from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.alerts_scoring import QualityAlert
from app.db.models.control import IngestionRun
from app.db.models.electoral_core import PollingTable
from app.db.models.results import VoteResult


@dataclass(frozen=True)
class QualitySummary:
    quality_alerts_created: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int


class QualityValidationService:
    def __init__(self, db: Session):
        self.db = db

    def _create_alert(
        self,
        ingestion_run_id: uuid.UUID,
        election_id: uuid.UUID | None,
        entity_level: str,
        entity_id: str | None,
        alert_code: str,
        severity: str,
        message: str,
        source_file_id: uuid.UUID | None = None,
    ) -> QualityAlert:
        alert = QualityAlert(
            ingestion_run_id=ingestion_run_id,
            election_id=election_id,
            entity_level=entity_level,
            entity_id=entity_id,
            alert_code=alert_code,
            severity=severity,
            message=message,
            source_file_id=source_file_id,
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def validate_quality(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self.db.get(IngestionRun, ingestion_run_id)
        if run is None:
            raise ValueError(f"Ingestion run not found: {ingestion_run_id}")

        # Idempotent for this sprint: remove previous quality alerts for same run before recalculating.
        self.db.query(QualityAlert).filter(
            QualityAlert.ingestion_run_id == ingestion_run_id
        ).delete(synchronize_session=False)

        vote_results = (
            self.db.query(VoteResult)
            .filter(VoteResult.ingestion_run_id == ingestion_run_id)
            .all()
        )

        created = 0
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for result in vote_results:
            if result.votes < 0:
                self._create_alert(
                    ingestion_run_id=ingestion_run_id,
                    election_id=result.election_id,
                    entity_level="VOTE_RESULT",
                    entity_id=str(result.vote_result_id),
                    alert_code="NEGATIVE_VOTES",
                    severity="CRITICAL",
                    message="El resultado contiene votos negativos.",
                    source_file_id=result.source_file_id,
                )
                created += 1
                severity_counts["CRITICAL"] += 1

        # Table-level consistency: total votes must not exceed registered voters if census exists.
        table_ids = {vr.polling_table_id for vr in vote_results}
        for table_id in table_ids:
            table = self.db.get(PollingTable, table_id)
            if not table or table.registered_voters is None:
                continue
            total_votes = sum(vr.votes for vr in vote_results if vr.polling_table_id == table_id)
            if total_votes > table.registered_voters:
                self._create_alert(
                    ingestion_run_id=ingestion_run_id,
                    election_id=table.election_id,
                    entity_level="POLLING_TABLE",
                    entity_id=str(table.polling_table_id),
                    alert_code="VOTES_GREATER_THAN_CENSUS",
                    severity="CRITICAL",
                    message="La mesa tiene más votos totales que votantes registrados.",
                    source_file_id=None,
                )
                created += 1
                severity_counts["CRITICAL"] += 1

        run.status = "VALIDATED"
        self.db.commit()

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "quality_alerts_created": created,
            "critical_alerts": severity_counts["CRITICAL"],
            "high_alerts": severity_counts["HIGH"],
            "medium_alerts": severity_counts["MEDIUM"],
            "low_alerts": severity_counts["LOW"],
        }

    def get_quality_summary(self, ingestion_run_id: uuid.UUID) -> dict:
        alerts = (
            self.db.query(QualityAlert)
            .filter(QualityAlert.ingestion_run_id == ingestion_run_id)
            .all()
        )
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        return {
            "ingestion_run_id": str(ingestion_run_id),
            "quality_alerts_count": len(alerts),
            "by_severity": severity_counts,
            "by_alert_code": {
                code: sum(1 for alert in alerts if alert.alert_code == code)
                for code in sorted({alert.alert_code for alert in alerts})
            },
        }
