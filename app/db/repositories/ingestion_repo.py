from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models.control import IngestionRun, SourceFile, SourceMapping

class IngestionRepository:
    def __init__(self, db: Session): self.db = db
    def create_ingestion_run(self, pipeline_version: str, rules_version: str, scoring_version: str, execution_mode: str) -> IngestionRun:
        run = IngestionRun(status="PENDING", pipeline_version=pipeline_version, rules_version=rules_version, scoring_version=scoring_version, execution_mode=execution_mode)
        self.db.add(run); self.db.flush(); return run
    def create_source_file(self, ingestion_run_id: uuid.UUID, election_id: uuid.UUID | None, source_name: str, source_url: str | None, file_name: str, file_hash: str, file_size_bytes: int | None) -> SourceFile:
        source = SourceFile(ingestion_run_id=ingestion_run_id, election_id=election_id, source_name=source_name, source_url=source_url, file_name=file_name, file_hash=file_hash, file_size_bytes=file_size_bytes, uploaded_at=datetime.utcnow(), status="REGISTERED")
        self.db.add(source); self.db.flush(); return source
    def get_run(self, ingestion_run_id: uuid.UUID) -> IngestionRun | None:
        return self.db.get(IngestionRun, ingestion_run_id)
    def get_source_file_by_run(self, ingestion_run_id: uuid.UUID) -> SourceFile | None:
        return self.db.query(SourceFile).filter(SourceFile.ingestion_run_id == ingestion_run_id).order_by(SourceFile.created_at.desc()).first()
    def save_mapping(self, source_file_id: uuid.UUID, source_field_name: str, canonical_field_name: str, mapping_method: str, confidence: float, status: str) -> SourceMapping:
        existing = self.db.query(SourceMapping).filter(SourceMapping.source_file_id == source_file_id, SourceMapping.source_field_name == source_field_name).one_or_none()
        if existing:
            existing.canonical_field_name=canonical_field_name; existing.mapping_method=mapping_method; existing.confidence=confidence; existing.status=status; return existing
        mapping = SourceMapping(source_file_id=source_file_id, source_field_name=source_field_name, canonical_field_name=canonical_field_name, mapping_method=mapping_method, confidence=confidence, status=status)
        self.db.add(mapping); self.db.flush(); return mapping
