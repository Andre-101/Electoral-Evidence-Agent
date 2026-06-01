from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.services.agent_service import AgentService
from app.services.alert_service import AlertService
from app.services.core_load_service import CoreLoadService
from app.services.evidence_service import EvidenceService
from app.services.ingestion_service import IngestionService
from app.services.mapping_service import MappingService
from app.services.metrics_service import MetricsService
from app.services.report_service import ReportService
from app.services.scoring_service import ScoringService


class LocalUploadFile:
    def __init__(self, path: Path, filename: str):
        self.path = path
        self.filename = filename
        self.file = path.open("rb")

    def close(self):
        self.file.close()


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    def run_demo_pipeline(self, sample_name: str = "sample_territorial_outlier.csv") -> dict:
        sample_path = Path("data/samples") / sample_name
        if not sample_path.exists():
            raise ValueError(f"Sample file not found: {sample_path}")

        upload = LocalUploadFile(sample_path, f"demo_{uuid4()}_{sample_name}")
        try:
            ingestion = IngestionService(self.db).create_ingestion(
                file=upload,
                election_id=None,
                source_name="demo_pipeline",
                source_url=str(sample_path),
                execution_mode="EXPLORATORY",
            )
        finally:
            upload.close()

        ingestion_run_id = ingestion["ingestion_run_id"]

        IngestionService(self.db).profile_file(ingestion_run_id)
        MappingService(self.db).propose_mapping(ingestion_run_id, [])
        CoreLoadService(self.db).load_to_core(ingestion_run_id)
        MetricsService(self.db).calculate_all_basic_metrics(ingestion_run_id)
        MetricsService(self.db).calculate_territorial_metrics(ingestion_run_id)
        AlertService(self.db).generate_eda_alerts(ingestion_run_id)
        ScoringService(self.db).calculate_scores(ingestion_run_id)

        cases = ScoringService(self.db).get_review_cases(ingestion_run_id)
        if not cases["items"]:
            return {
                "ingestion_run_id": ingestion_run_id,
                "review_cases_created": 0,
                "message": "Pipeline finished, but no review cases were created.",
            }

        first_case_id = cases["items"][0]["review_case_id"]
        EvidenceService(self.db).generate_evidence_items(first_case_id)
        dossier = AgentService(self.db).generate_dossier(first_case_id)
        case_report = ReportService(self.db).generate_case_report(first_case_id)
        executive_report = ReportService(self.db).generate_executive_report(ingestion_run_id)

        return {
            "ingestion_run_id": ingestion_run_id,
            "review_cases_created": cases["total"],
            "first_review_case_id": first_case_id,
            "evidence_dossier_id": dossier["evidence_dossier_id"],
            "case_report_id": case_report["report_id"],
            "case_report_path": case_report["export"]["file_path"],
            "executive_report_id": executive_report["report_id"],
            "executive_report_path": executive_report["export"]["file_path"],
        }
