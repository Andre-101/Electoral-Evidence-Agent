from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.alerts_scoring import EdaAlert, QualityAlert, ReviewCase, ScoreComponent
from app.db.models.control import IngestionRun, SourceFile
from app.db.models.evidence import EvidenceItem
from app.db.models.reports import TraceabilityEvent


def _strength_from_severity(severity: str) -> str:
    if severity == "CRITICAL":
        return "CRITICAL"
    if severity == "HIGH":
        return "HIGH"
    if severity == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def _evidence_type_from_alert_code(alert_code: str) -> str:
    if alert_code.startswith("TURNOUT"):
        return "TURNOUT_ANOMALY"
    if alert_code.startswith("WINNER_SHARE") or alert_code.startswith("MARGIN"):
        return "CONCENTRATION_ANOMALY"
    if "STATION" in alert_code or "TERRITORIAL" in alert_code or "DIFF" in alert_code:
        return "TERRITORIAL_OUTLIER"
    if "DIGIT" in alert_code:
        return "DIGIT_ANOMALY"
    return "QUALITY_ISSUE"


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def _get_case(self, review_case_id: uuid.UUID) -> ReviewCase:
        case = self.db.get(ReviewCase, review_case_id)
        if case is None:
            raise ValueError(f"Review case not found: {review_case_id}")
        return case

    def generate_evidence_items(self, review_case_id: uuid.UUID) -> dict:
        case = self._get_case(review_case_id)

        # Idempotent for this sprint.
        self.db.query(EvidenceItem).filter(
            EvidenceItem.review_case_id == review_case_id
        ).delete(synchronize_session=False)

        created = 0

        eda_alerts = (
            self.db.query(EdaAlert)
            .filter(
                EdaAlert.ingestion_run_id == case.ingestion_run_id,
                EdaAlert.entity_level == case.entity_level,
                EdaAlert.entity_id == case.entity_id,
            )
            .all()
        )

        # If the review_case is option-specific, keep option-specific alerts aligned.
        if case.electoral_option_id:
            eda_alerts = [
                alert for alert in eda_alerts
                if alert.electoral_option_id is None or alert.electoral_option_id == case.electoral_option_id
            ]

        for alert in eda_alerts:
            evidence = EvidenceItem(
                review_case_id=case.review_case_id,
                evidence_type=_evidence_type_from_alert_code(alert.alert_code),
                entity_level=alert.entity_level,
                entity_id=alert.entity_id,
                metric_name=alert.metric_name,
                metric_value=alert.metric_value,
                comparison_context=alert.comparison_group,
                source_table="eda_alerts",
                source_record_id=str(alert.eda_alert_id),
                strength=_strength_from_severity(alert.severity),
                description=(
                    f"{alert.message} "
                    f"Métrica {alert.metric_name}={alert.metric_value}; "
                    f"umbral={alert.threshold_value}."
                ),
            )
            self.db.add(evidence)
            created += 1

        quality_alerts = (
            self.db.query(QualityAlert)
            .filter(
                QualityAlert.ingestion_run_id == case.ingestion_run_id,
                QualityAlert.entity_level == case.entity_level,
                QualityAlert.entity_id == case.entity_id,
            )
            .all()
        )

        for alert in quality_alerts:
            evidence = EvidenceItem(
                review_case_id=case.review_case_id,
                evidence_type="QUALITY_ISSUE",
                entity_level=alert.entity_level,
                entity_id=alert.entity_id or case.entity_id,
                metric_name=None,
                metric_value=None,
                comparison_context=None,
                source_table="quality_alerts",
                source_record_id=str(alert.quality_alert_id),
                strength=_strength_from_severity(alert.severity),
                description=alert.message,
            )
            self.db.add(evidence)
            created += 1

        components = (
            self.db.query(ScoreComponent)
            .filter(ScoreComponent.anomaly_score_id == case.anomaly_score_id)
            .all()
        )

        for component in components:
            evidence = EvidenceItem(
                review_case_id=case.review_case_id,
                evidence_type="SCORE_COMPONENT",
                entity_level=case.entity_level,
                entity_id=case.entity_id,
                metric_name=component.component_name,
                metric_value=component.points,
                comparison_context=component.component_type,
                source_table="score_components",
                source_record_id=str(component.score_component_id),
                strength="MEDIUM" if component.component_type != "BONUS" else "LOW",
                description=component.explanation,
            )
            self.db.add(evidence)
            created += 1

        trace_event = TraceabilityEvent(
            ingestion_run_id=case.ingestion_run_id,
            entity_type="REVIEW_CASE",
            entity_id=str(case.review_case_id),
            event_type="EVIDENCE_CREATED",
            event_description=f"Se generaron {created} evidence_items para el caso de revisión.",
        )
        self.db.add(trace_event)

        self.db.commit()

        return {
            "review_case_id": str(review_case_id),
            "evidence_items_created": created,
        }

    def get_evidence_items(self, review_case_id: uuid.UUID) -> dict:
        case = self._get_case(review_case_id)
        items = (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.review_case_id == review_case_id)
            .order_by(EvidenceItem.created_at.asc())
            .all()
        )

        return {
            "review_case_id": str(review_case_id),
            "items": [self._evidence_item_to_dict(item) for item in items],
            "total": len(items),
        }

    def build_agent_context(self, review_case_id: uuid.UUID) -> dict:
        case = self._get_case(review_case_id)

        items = (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.review_case_id == review_case_id)
            .order_by(EvidenceItem.created_at.asc())
            .all()
        )

        if not items:
            self.generate_evidence_items(review_case_id)
            items = (
                self.db.query(EvidenceItem)
                .filter(EvidenceItem.review_case_id == review_case_id)
                .order_by(EvidenceItem.created_at.asc())
                .all()
            )

        run = self.db.get(IngestionRun, case.ingestion_run_id)
        source_files = (
            self.db.query(SourceFile)
            .filter(SourceFile.ingestion_run_id == case.ingestion_run_id)
            .all()
        )

        components = (
            self.db.query(ScoreComponent)
            .filter(ScoreComponent.anomaly_score_id == case.anomaly_score_id)
            .all()
        )

        return {
            "review_case": {
                "review_case_id": str(case.review_case_id),
                "election_id": str(case.election_id),
                "ingestion_run_id": str(case.ingestion_run_id),
                "entity_level": case.entity_level,
                "entity_id": case.entity_id,
                "electoral_option_id": str(case.electoral_option_id) if case.electoral_option_id else None,
                "review_priority_score": float(case.review_priority_score),
                "priority": case.priority,
                "statistical_confidence": case.statistical_confidence,
                "status": case.status,
                "case_summary": case.case_summary,
            },
            "evidence_items": [self._evidence_item_to_dict(item) for item in items],
            "score_components": [
                {
                    "score_component_id": str(component.score_component_id),
                    "component_type": component.component_type,
                    "component_name": component.component_name,
                    "points": float(component.points),
                    "explanation": component.explanation,
                    "source_alert_type": component.source_alert_type,
                    "source_alert_id": component.source_alert_id,
                }
                for component in components
            ],
            "traceability": {
                "pipeline_version": run.pipeline_version if run else None,
                "rules_version": run.rules_version if run else None,
                "scoring_version": run.scoring_version if run else None,
                "source_files": [
                    {
                        "source_file_id": str(source.source_file_id),
                        "file_name": source.file_name,
                        "file_hash": source.file_hash,
                        "source_name": source.source_name,
                        "detected_format": source.detected_format,
                        "detected_encoding": source.detected_encoding,
                        "detected_separator": source.detected_separator,
                    }
                    for source in source_files
                ],
            },
            "methodological_limits": [
                "El sistema identifica señales atípicas y posibles irregularidades; no concluye fraude electoral.",
                "La revisión humana o documental sigue siendo necesaria.",
                "El MVP no procesa imágenes, actas escaneadas ni OCR.",
            ],
        }

    def _evidence_item_to_dict(self, item: EvidenceItem) -> dict:
        return {
            "evidence_item_id": str(item.evidence_item_id),
            "review_case_id": str(item.review_case_id),
            "evidence_type": item.evidence_type,
            "entity_level": item.entity_level,
            "entity_id": item.entity_id,
            "metric_name": item.metric_name,
            "metric_value": float(item.metric_value) if item.metric_value is not None else None,
            "comparison_context": item.comparison_context,
            "source_table": item.source_table,
            "source_record_id": item.source_record_id,
            "strength": item.strength,
            "description": item.description,
        }
