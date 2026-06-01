from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import load_yaml_config
from app.db.models.alerts_scoring import (
    AnomalyScore,
    EdaAlert,
    QualityAlert,
    ReviewCase,
    ScoreComponent,
)
from app.db.models.catalogs import AlertCatalog
from app.db.models.control import IngestionRun
from app.services.alert_service import AlertService


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _as_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


class ScoringService:
    def __init__(self, db: Session):
        self.db = db

    def _load_scoring_config(self) -> dict:
        return load_yaml_config("config/scoring.yaml")

    def _priority_for_score(self, score: float, config: dict) -> str:
        for priority, bounds in config["priority_ranges"].items():
            if bounds["min"] <= score <= bounds["max"]:
                return priority
        return "CRITICAL_REVIEW" if score > 100 else "LOW"

    def _confidence_for_entity(self, alert_count: int, high_alert_count: int, critical_alert_count: int) -> str:
        if critical_alert_count >= 1 or high_alert_count >= 3:
            return "HIGH"
        if high_alert_count >= 1 or alert_count >= 3:
            return "MEDIUM"
        if alert_count >= 1:
            return "LOW"
        return "INSUFFICIENT"

    def _alert_catalog_by_code(self) -> dict[str, AlertCatalog]:
        return {
            item.alert_code: item
            for item in self.db.query(AlertCatalog).all()
        }

    def _ensure_alerts(self, ingestion_run_id: uuid.UUID) -> None:
        count = (
            self.db.query(EdaAlert)
            .filter(EdaAlert.ingestion_run_id == ingestion_run_id)
            .count()
        )
        if count == 0:
            AlertService(self.db).generate_eda_alerts(ingestion_run_id)

    def _entity_key_from_alert(self, alert) -> tuple[str, str, uuid.UUID | None]:
        return (alert.entity_level, alert.entity_id, getattr(alert, "electoral_option_id", None))

    def _score_alerts_for_entity(
        self,
        alerts: list,
        config: dict,
        alert_catalog: dict[str, AlertCatalog],
    ) -> tuple[float, list[dict]]:
        severity_points = config["severity_points"]
        category_weights = config["category_weights"]

        total = 0.0
        components: list[dict] = []
        categories = set()
        high_or_more = 0
        critical = 0

        for alert in alerts:
            catalog = alert_catalog.get(alert.alert_code)
            category = catalog.category if catalog else "UNKNOWN"
            categories.add(category)

            base_points = severity_points.get(alert.severity, 0)
            weight = category_weights.get(category, 1.0)
            points = float(base_points) * float(weight)
            total += points

            if SEVERITY_ORDER.get(alert.severity, 0) >= SEVERITY_ORDER["HIGH"]:
                high_or_more += 1
            if alert.severity == "CRITICAL":
                critical += 1

            components.append(
                {
                    "source_alert_type": "EDA_ALERT" if isinstance(alert, EdaAlert) else "QUALITY_ALERT",
                    "source_alert_id": str(alert.eda_alert_id if isinstance(alert, EdaAlert) else alert.quality_alert_id),
                    "component_type": "ALERT_POINTS",
                    "component_name": alert.alert_code,
                    "points": points,
                    "explanation": f"Alerta {alert.alert_code} con severidad {alert.severity}, categoría {category} y peso {weight}.",
                }
            )

        # Simplified bonuses from scoring.yaml, enough for MVP.
        if "TURNOUT" in categories and "CONCENTRATION" in categories:
            total += 20
            components.append(
                {
                    "source_alert_type": "NONE",
                    "source_alert_id": None,
                    "component_type": "BONUS",
                    "component_name": "HIGH_TURNOUT_AND_HIGH_CONCENTRATION",
                    "points": 20,
                    "explanation": "El caso combina alertas de participación y concentración.",
                }
            )

        if "TURNOUT" in categories and "TERRITORIAL" in categories:
            total += 20
            components.append(
                {
                    "source_alert_type": "NONE",
                    "source_alert_id": None,
                    "component_type": "BONUS",
                    "component_name": "HIGH_TURNOUT_AND_STATION_OUTLIER",
                    "points": 20,
                    "explanation": "El caso combina participación atípica y señal territorial.",
                }
            )

        if "CONCENTRATION" in categories and "TERRITORIAL" in categories:
            total += 15
            components.append(
                {
                    "source_alert_type": "NONE",
                    "source_alert_id": None,
                    "component_type": "BONUS",
                    "component_name": "HIGH_CONCENTRATION_AND_STATION_OUTLIER",
                    "points": 15,
                    "explanation": "El caso combina concentración alta y desviación territorial.",
                }
            )

        if critical >= 1:
            total += 25
            components.append(
                {
                    "source_alert_type": "NONE",
                    "source_alert_id": None,
                    "component_type": "BONUS",
                    "component_name": "CRITICAL_ALERT_PRESENT",
                    "points": 25,
                    "explanation": "El caso contiene al menos una alerta crítica.",
                }
            )

        if high_or_more >= 3:
            total += 20
            components.append(
                {
                    "source_alert_type": "NONE",
                    "source_alert_id": None,
                    "component_type": "BONUS",
                    "component_name": "THREE_OR_MORE_HIGH_ALERTS",
                    "points": 20,
                    "explanation": "El caso acumula tres o más alertas de severidad alta o crítica.",
                }
            )

        return min(max(total, 0.0), 100.0), components

    def calculate_scores(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self.db.get(IngestionRun, ingestion_run_id)
        if run is None:
            raise ValueError(f"Ingestion run not found: {ingestion_run_id}")

        self._ensure_alerts(ingestion_run_id)

        # Idempotent for this sprint.
        old_scores = (
            self.db.query(AnomalyScore)
            .filter(AnomalyScore.ingestion_run_id == ingestion_run_id)
            .all()
        )
        old_score_ids = [score.anomaly_score_id for score in old_scores]
        if old_score_ids:
            self.db.query(ReviewCase).filter(ReviewCase.anomaly_score_id.in_(old_score_ids)).delete(synchronize_session=False)
            self.db.query(ScoreComponent).filter(ScoreComponent.anomaly_score_id.in_(old_score_ids)).delete(synchronize_session=False)
        self.db.query(AnomalyScore).filter(
            AnomalyScore.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        config = self._load_scoring_config()
        alert_catalog = self._alert_catalog_by_code()

        eda_alerts = (
            self.db.query(EdaAlert)
            .filter(EdaAlert.ingestion_run_id == ingestion_run_id)
            .all()
        )
        quality_alerts = (
            self.db.query(QualityAlert)
            .filter(QualityAlert.ingestion_run_id == ingestion_run_id)
            .all()
        )

        grouped: dict[tuple[str, str, uuid.UUID | None], list] = defaultdict(list)
        for alert in eda_alerts:
            grouped[self._entity_key_from_alert(alert)].append(alert)
        for alert in quality_alerts:
            if alert.entity_id:
                grouped[(alert.entity_level, alert.entity_id, None)].append(alert)

        scores_created = 0
        components_created = 0
        review_cases_created = 0
        minimum_score = config.get("case_generation", {}).get("minimum_score_to_create_case", 25)

        for (entity_level, entity_id, option_id), alerts in grouped.items():
            score_value, component_payloads = self._score_alerts_for_entity(alerts, config, alert_catalog)
            priority = self._priority_for_score(score_value, config)
            alert_count = len(alerts)
            high_count = sum(1 for alert in alerts if SEVERITY_ORDER.get(alert.severity, 0) >= SEVERITY_ORDER["HIGH"])
            critical_count = sum(1 for alert in alerts if alert.severity == "CRITICAL")
            confidence = self._confidence_for_entity(alert_count, high_count, critical_count)

            election_id = alerts[0].election_id
            main_reasons = ", ".join(sorted({alert.alert_code for alert in alerts}))

            anomaly_score = AnomalyScore(
                ingestion_run_id=ingestion_run_id,
                election_id=election_id,
                entity_level=entity_level,
                entity_id=entity_id,
                electoral_option_id=option_id,
                review_priority_score=score_value,
                priority=priority,
                statistical_confidence=confidence,
                alert_count=alert_count,
                high_alert_count=high_count,
                critical_alert_count=critical_count,
                main_reasons=main_reasons,
            )
            self.db.add(anomaly_score)
            self.db.flush()
            scores_created += 1

            for payload in component_payloads:
                component = ScoreComponent(
                    anomaly_score_id=anomaly_score.anomaly_score_id,
                    source_alert_type=payload["source_alert_type"],
                    source_alert_id=payload["source_alert_id"],
                    component_type=payload["component_type"],
                    component_name=payload["component_name"],
                    points=payload["points"],
                    explanation=payload["explanation"],
                )
                self.db.add(component)
                components_created += 1

            if score_value >= minimum_score:
                case_summary = (
                    f"Caso priorizado por {main_reasons}. "
                    f"Score de revisión: {score_value:.2f}. "
                    "No representa conclusión de fraude."
                )
                review_case = ReviewCase(
                    election_id=election_id,
                    ingestion_run_id=ingestion_run_id,
                    anomaly_score_id=anomaly_score.anomaly_score_id,
                    entity_level=entity_level,
                    entity_id=entity_id,
                    electoral_option_id=option_id,
                    review_priority_score=score_value,
                    priority=priority,
                    statistical_confidence=confidence,
                    status=config.get("case_generation", {}).get("default_status", "OPEN"),
                    case_summary=case_summary,
                )
                self.db.add(review_case)
                review_cases_created += 1

        run.status = "SCORED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "anomaly_scores_created": scores_created,
            "score_components_created": components_created,
            "review_cases_created": review_cases_created,
        }

    def get_review_cases(self, ingestion_run_id: uuid.UUID) -> dict:
        cases = (
            self.db.query(ReviewCase)
            .filter(ReviewCase.ingestion_run_id == ingestion_run_id)
            .order_by(ReviewCase.review_priority_score.desc())
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [self._case_to_dict(case, include_components=False) for case in cases],
            "total": len(cases),
        }

    def get_review_case_detail(self, review_case_id: uuid.UUID) -> dict:
        case = self.db.get(ReviewCase, review_case_id)
        if case is None:
            raise ValueError(f"Review case not found: {review_case_id}")

        components = (
            self.db.query(ScoreComponent)
            .filter(ScoreComponent.anomaly_score_id == case.anomaly_score_id)
            .all()
        )
        data = self._case_to_dict(case, include_components=False)
        data["score_components"] = [
            {
                "score_component_id": str(component.score_component_id),
                "source_alert_type": component.source_alert_type,
                "source_alert_id": component.source_alert_id,
                "component_type": component.component_type,
                "component_name": component.component_name,
                "points": float(component.points),
                "explanation": component.explanation,
            }
            for component in components
        ]
        return data

    def _case_to_dict(self, case: ReviewCase, include_components: bool = False) -> dict:
        return {
            "review_case_id": str(case.review_case_id),
            "election_id": str(case.election_id),
            "ingestion_run_id": str(case.ingestion_run_id),
            "anomaly_score_id": str(case.anomaly_score_id),
            "entity_level": case.entity_level,
            "entity_id": case.entity_id,
            "electoral_option_id": str(case.electoral_option_id) if case.electoral_option_id else None,
            "review_priority_score": float(case.review_priority_score),
            "priority": case.priority,
            "statistical_confidence": case.statistical_confidence,
            "status": case.status,
            "case_summary": case.case_summary,
        }
