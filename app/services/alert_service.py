from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.robust_stats import mad_decimal, median_decimal, robust_z
from app.core.settings import load_yaml_config
from app.db.models.alerts_scoring import EdaAlert
from app.db.models.analytics import OptionTableMetric, StationMetric, TableMetric
from app.db.models.control import IngestionRun
from app.db.models.electoral_core import PollingTable
from app.services.metrics_service import MetricsService


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _rule_by_code(rules: list[dict], code: str) -> dict:
    for rule in rules:
        if rule.get("rule_code") == code:
            return rule
    raise KeyError(f"EDA rule not found in rules.yaml: {code}")


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def _load_eda_rules(self) -> list[dict]:
        data = load_yaml_config("config/rules.yaml")
        return [rule for rule in data.get("eda_rules", []) if rule.get("enabled", True)]

    def _create_eda_alert(
        self,
        ingestion_run_id: uuid.UUID,
        election_id: uuid.UUID,
        entity_level: str,
        entity_id: str,
        alert_code: str,
        severity: str,
        metric_name: str,
        metric_value,
        threshold_value,
        message: str,
        electoral_option_id: uuid.UUID | None = None,
        comparison_group: str | None = None,
    ) -> EdaAlert:
        alert = EdaAlert(
            ingestion_run_id=ingestion_run_id,
            election_id=election_id,
            entity_level=entity_level,
            entity_id=entity_id,
            electoral_option_id=electoral_option_id,
            alert_code=alert_code,
            severity=severity,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold_value=threshold_value,
            comparison_group=comparison_group,
            message=message,
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def _ensure_table_metrics(self, ingestion_run_id: uuid.UUID) -> None:
        count = (
            self.db.query(TableMetric)
            .filter(TableMetric.ingestion_run_id == ingestion_run_id)
            .count()
        )
        if count == 0:
            MetricsService(self.db).calculate_all_basic_metrics(ingestion_run_id)

    def _emit(self, rules, metric_or_entity, ingestion_run_id, code, metric_name, metric_value, threshold_value, election_id, entity_id, option_id=None):
        rule = _rule_by_code(rules, code)
        self._create_eda_alert(
            ingestion_run_id=ingestion_run_id,
            election_id=election_id,
            entity_level=rule.get("entity_level", "POLLING_TABLE"),
            entity_id=str(entity_id),
            electoral_option_id=option_id,
            alert_code=code,
            severity=rule["severity"],
            metric_name=metric_name,
            metric_value=metric_value,
            threshold_value=threshold_value,
            comparison_group=rule.get("comparison_group"),
            message=rule["message"],
        )

    def generate_eda_alerts(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self.db.get(IngestionRun, ingestion_run_id)
        if run is None:
            raise ValueError(f"Ingestion run not found: {ingestion_run_id}")

        self._ensure_table_metrics(ingestion_run_id)

        self.db.query(EdaAlert).filter(
            EdaAlert.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        rules = self._load_eda_rules()
        created = 0
        by_code: dict[str, int] = {}

        def count(code: str):
            nonlocal created
            created += 1
            by_code[code] = by_code.get(code, 0) + 1

        # Simple table alerts.
        table_metrics = (
            self.db.query(TableMetric)
            .filter(TableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )

        for metric in table_metrics:
            turnout = _to_decimal(metric.turnout)
            winner_share = _to_decimal(metric.winner_share)
            margin_rate = _to_decimal(metric.margin_rate)

            if turnout is not None:
                if turnout > Decimal("1.0"):
                    self._emit(rules, metric, ingestion_run_id, "TURNOUT_GT_100", "turnout", turnout, Decimal("1.0"), metric.election_id, metric.polling_table_id)
                    count("TURNOUT_GT_100")
                elif turnout >= Decimal("0.95"):
                    self._emit(rules, metric, ingestion_run_id, "TURNOUT_GE_95", "turnout", turnout, Decimal("0.95"), metric.election_id, metric.polling_table_id)
                    count("TURNOUT_GE_95")
                elif turnout <= Decimal("0.20"):
                    self._emit(rules, metric, ingestion_run_id, "TURNOUT_LE_20", "turnout", turnout, Decimal("0.20"), metric.election_id, metric.polling_table_id)
                    count("TURNOUT_LE_20")

            if winner_share is not None:
                if winner_share >= Decimal("0.95"):
                    self._emit(rules, metric, ingestion_run_id, "WINNER_SHARE_GE_95", "winner_share", winner_share, Decimal("0.95"), metric.election_id, metric.polling_table_id, metric.winner_option_id)
                    count("WINNER_SHARE_GE_95")
                elif winner_share >= Decimal("0.90"):
                    self._emit(rules, metric, ingestion_run_id, "WINNER_SHARE_GE_90", "winner_share", winner_share, Decimal("0.90"), metric.election_id, metric.polling_table_id, metric.winner_option_id)
                    count("WINNER_SHARE_GE_90")

            if margin_rate is not None and margin_rate >= Decimal("0.80"):
                self._emit(rules, metric, ingestion_run_id, "MARGIN_GE_80", "margin_rate", margin_rate, Decimal("0.80"), metric.election_id, metric.polling_table_id, metric.winner_option_id)
                count("MARGIN_GE_80")

        # Territorial turnout outliers.
        table_by_id = {table.polling_table_id: table for table in self.db.query(PollingTable).all()}
        station_by_table = {table_id: table.polling_station_election_id for table_id, table in table_by_id.items()}
        metrics_by_station: dict[uuid.UUID, list[TableMetric]] = {}
        for metric in table_metrics:
            station_id = station_by_table.get(metric.polling_table_id)
            if station_id:
                metrics_by_station.setdefault(station_id, []).append(metric)

        for station_id, metrics in metrics_by_station.items():
            values = [m.turnout for m in metrics if m.turnout is not None]
            if len(values) < 5:
                continue
            center = median_decimal(values)
            mad = mad_decimal(values, center)
            for metric in metrics:
                rz = robust_z(metric.turnout, center, mad)
                if rz is not None and abs(rz) >= Decimal("3.5"):
                    self._emit(
                        rules,
                        metric,
                        ingestion_run_id,
                        "TABLE_TURNOUT_OUTLIER_STATION",
                        "robust_z_turnout_station",
                        rz,
                        Decimal("3.5"),
                        metric.election_id,
                        metric.polling_table_id,
                    )
                    count("TABLE_TURNOUT_OUTLIER_STATION")

        # Territorial option outliers.
        option_metrics = (
            self.db.query(OptionTableMetric)
            .filter(OptionTableMetric.ingestion_run_id == ingestion_run_id)
            .all()
        )
        for metric in option_metrics:
            rz_station = _to_decimal(metric.robust_z_vs_station)
            diff_station = _to_decimal(metric.diff_vs_station)

            if rz_station is not None and abs(rz_station) >= Decimal("3.5"):
                self._emit(
                    rules,
                    metric,
                    ingestion_run_id,
                    "TABLE_PARTY_SHARE_OUTLIER_STATION",
                    "robust_z_party_share_station",
                    rz_station,
                    Decimal("3.5"),
                    metric.election_id,
                    metric.polling_table_id,
                    metric.electoral_option_id,
                )
                count("TABLE_PARTY_SHARE_OUTLIER_STATION")

            if diff_station is not None:
                if diff_station >= Decimal("0.30"):
                    self._emit(
                        rules,
                        metric,
                        ingestion_run_id,
                        "TABLE_DIFF_STATION_GE_30PP",
                        "diff_vs_station",
                        diff_station,
                        Decimal("0.30"),
                        metric.election_id,
                        metric.polling_table_id,
                        metric.electoral_option_id,
                    )
                    count("TABLE_DIFF_STATION_GE_30PP")
                elif diff_station >= Decimal("0.20"):
                    self._emit(
                        rules,
                        metric,
                        ingestion_run_id,
                        "TABLE_DIFF_STATION_GE_20PP",
                        "diff_vs_station",
                        diff_station,
                        Decimal("0.20"),
                        metric.election_id,
                        metric.polling_table_id,
                        metric.electoral_option_id,
                    )
                    count("TABLE_DIFF_STATION_GE_20PP")

        run.status = "ALERTS_GENERATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "eda_alerts_created": created,
            "by_alert_code": by_code,
        }

    def get_eda_alerts(self, ingestion_run_id: uuid.UUID) -> dict:
        alerts = (
            self.db.query(EdaAlert)
            .filter(EdaAlert.ingestion_run_id == ingestion_run_id)
            .order_by(EdaAlert.created_at.asc())
            .all()
        )
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "items": [
                {
                    "eda_alert_id": str(alert.eda_alert_id),
                    "election_id": str(alert.election_id),
                    "entity_level": alert.entity_level,
                    "entity_id": alert.entity_id,
                    "electoral_option_id": str(alert.electoral_option_id) if alert.electoral_option_id else None,
                    "alert_code": alert.alert_code,
                    "severity": alert.severity,
                    "metric_name": alert.metric_name,
                    "metric_value": float(alert.metric_value) if alert.metric_value is not None else None,
                    "threshold_value": float(alert.threshold_value) if alert.threshold_value is not None else None,
                    "comparison_group": alert.comparison_group,
                    "message": alert.message,
                }
                for alert in alerts
            ],
            "total": len(alerts),
        }

    def get_eda_summary(self, ingestion_run_id: uuid.UUID) -> dict:
        alerts = (
            self.db.query(EdaAlert)
            .filter(EdaAlert.ingestion_run_id == ingestion_run_id)
            .all()
        )
        by_severity: dict[str, int] = {}
        by_alert_code: dict[str, int] = {}
        for alert in alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            by_alert_code[alert.alert_code] = by_alert_code.get(alert.alert_code, 0) + 1
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "eda_alerts_count": len(alerts),
            "by_severity": by_severity,
            "by_alert_code": by_alert_code,
        }
