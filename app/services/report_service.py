from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.db.models.alerts_scoring import EdaAlert, QualityAlert, ReviewCase, ScoreComponent
from app.db.models.evidence import EvidenceDossier, EvidenceItem
from app.db.models.reports import Report, ReportExport, TraceabilityEvent
from app.services.agent_service import AgentService
from app.services.evidence_service import EvidenceService
from app.services.scoring_service import ScoringService
from app.services.human_readable_service import HumanReadableService


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.templates_dir = Path("app/reports/templates")
        self.exports_dir = Path("data/exports")
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _write_export(self, file_name: str, content: str) -> tuple[str, str]:
        path = self.exports_dir / file_name
        path.write_text(content, encoding="utf-8")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        return str(path), file_hash

    def generate_case_report(self, review_case_id: uuid.UUID, export_format: str = "HTML") -> dict:
        if export_format.upper() != "HTML":
            raise ValueError("Sprint 11 only supports HTML exports.")

        scoring = ScoringService(self.db)
        evidence = EvidenceService(self.db)
        agent = AgentService(self.db)

        case_detail = scoring.get_review_case_detail(review_case_id)
        human = HumanReadableService(self.db)
        readable_case = human.describe_review_case(case_detail)

        try:
            dossier = agent.get_dossier(review_case_id)
        except Exception:
            dossier = agent.generate_dossier(review_case_id)

        dossier = dict(dossier)
        dossier["executive_summary"] = human.replace_known_ids_in_text(dossier.get("executive_summary"), case_detail)
        dossier["technical_summary"] = human.replace_known_ids_in_text(dossier.get("technical_summary"), case_detail)
        dossier["limitations"] = human.replace_known_ids_in_text(dossier.get("limitations"), case_detail)
        dossier["recommended_next_steps"] = human.replace_known_ids_in_text(dossier.get("recommended_next_steps"), case_detail)

        evidence_items = evidence.get_evidence_items(review_case_id)["items"]
        for item in evidence_items:
            item["description"] = human.replace_known_ids_in_text(item.get("description"), case_detail)
        agent_context = evidence.build_agent_context(review_case_id)
        score_components = agent_context["score_components"]
        traceability = agent_context["traceability"]

        title = f"Reporte de caso de revisión — {readable_case['display_title']}"
        template = self.env.get_template("case_report.html.j2")
        html = template.render(
            title=title,
            generated_by="ReportService v0.1",
            generated_at=dossier["generated_at"],
            review_case=case_detail,
            readable_case=readable_case,
            dossier=dossier,
            evidence_items=evidence_items,
            score_components=score_components,
            traceability=traceability,
        )

        report = Report(
            ingestion_run_id=uuid.UUID(case_detail["ingestion_run_id"]),
            election_id=uuid.UUID(case_detail["election_id"]),
            review_case_id=review_case_id,
            report_type="CASE",
            title=title,
            status="GENERATED",
        )
        self.db.add(report)
        self.db.flush()

        file_name = f"case_report_{review_case_id}.html"
        file_path, file_hash = self._write_export(file_name, html)

        export = ReportExport(
            report_id=report.report_id,
            export_format="HTML",
            file_path=file_path,
            file_hash=file_hash,
        )
        self.db.add(export)

        trace_event = TraceabilityEvent(
            ingestion_run_id=report.ingestion_run_id,
            entity_type="REVIEW_CASE",
            entity_id=str(review_case_id),
            event_type="REPORT_GENERATED",
            event_description=f"Reporte de caso exportado como HTML: {file_path}.",
        )
        self.db.add(trace_event)
        self.db.commit()

        return self._report_response(report, export)

    def generate_executive_report(self, ingestion_run_id: uuid.UUID, export_format: str = "HTML") -> dict:
        if export_format.upper() != "HTML":
            raise ValueError("Sprint 11 only supports HTML exports.")

        review_cases = ScoringService(self.db).get_review_cases(ingestion_run_id)["items"]
        eda_alerts_count = (
            self.db.query(EdaAlert)
            .filter(EdaAlert.ingestion_run_id == ingestion_run_id)
            .count()
        )
        quality_alerts_count = (
            self.db.query(QualityAlert)
            .filter(QualityAlert.ingestion_run_id == ingestion_run_id)
            .count()
        )

        if not review_cases:
            raise ValueError("No review cases found. Run scoring before generating executive report.")

        first_case = self.db.get(ReviewCase, uuid.UUID(review_cases[0]["review_case_id"]))
        election_id = first_case.election_id

        title = f"Reporte ejecutivo — Ingesta {ingestion_run_id}"
        template = self.env.get_template("executive_report.html.j2")
        html = template.render(
            title=title,
            counts={
                "review_cases": len(review_cases),
                "eda_alerts": eda_alerts_count,
                "quality_alerts": quality_alerts_count,
            },
            review_cases=review_cases,
        )

        report = Report(
            ingestion_run_id=ingestion_run_id,
            election_id=election_id,
            review_case_id=None,
            report_type="EXECUTIVE",
            title=title,
            status="GENERATED",
        )
        self.db.add(report)
        self.db.flush()

        file_name = f"executive_report_{ingestion_run_id}.html"
        file_path, file_hash = self._write_export(file_name, html)

        export = ReportExport(
            report_id=report.report_id,
            export_format="HTML",
            file_path=file_path,
            file_hash=file_hash,
        )
        self.db.add(export)

        trace_event = TraceabilityEvent(
            ingestion_run_id=ingestion_run_id,
            entity_type="INGESTION_RUN",
            entity_id=str(ingestion_run_id),
            event_type="REPORT_GENERATED",
            event_description=f"Reporte ejecutivo exportado como HTML: {file_path}.",
        )
        self.db.add(trace_event)
        self.db.commit()

        return self._report_response(report, export)

    def get_report(self, report_id: uuid.UUID) -> dict:
        report = self.db.get(Report, report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")
        export = (
            self.db.query(ReportExport)
            .filter(ReportExport.report_id == report_id)
            .order_by(ReportExport.created_at.desc())
            .first()
        )
        return self._report_response(report, export)

    def read_report_html(self, report_id: uuid.UUID) -> str:
        report = self.get_report(report_id)
        file_path = report["export"]["file_path"]
        return Path(file_path).read_text(encoding="utf-8")

    def _report_response(self, report: Report, export: ReportExport | None) -> dict:
        return {
            "report_id": str(report.report_id),
            "ingestion_run_id": str(report.ingestion_run_id),
            "election_id": str(report.election_id),
            "review_case_id": str(report.review_case_id) if report.review_case_id else None,
            "report_type": report.report_type,
            "title": report.title,
            "status": report.status,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "export": None if export is None else {
                "report_export_id": str(export.report_export_id),
                "export_format": export.export_format,
                "file_path": export.file_path,
                "file_hash": export.file_hash,
            },
        }
