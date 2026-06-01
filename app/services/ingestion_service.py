from __future__ import annotations
import shutil, uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.core.settings import get_settings, load_yaml_config
from app.db.repositories.ingestion_repo import IngestionRepository
from app.ingestion.file_reader import detect_file, read_csv
from app.ingestion.hashing import calculate_sha256
from app.ingestion.profiler import profile_dataframe

class IngestionService:
    def __init__(self, db: Session):
        self.db=db; self.repo=IngestionRepository(db); self.settings=get_settings()
    def create_ingestion(self, file: UploadFile, election_id: uuid.UUID | None, source_name: str, source_url: str | None, execution_mode: str) -> dict:
        upload_dir=Path(self.settings.upload_dir); upload_dir.mkdir(parents=True, exist_ok=True)
        target=upload_dir / file.filename
        with target.open('wb') as out: shutil.copyfileobj(file.file, out)
        digest=calculate_sha256(target)
        run=self.repo.create_ingestion_run(self.settings.pipeline_version, self.settings.rules_version, self.settings.scoring_version, execution_mode)
        source=self.repo.create_source_file(run.ingestion_run_id, election_id, source_name, str(target), file.filename, digest, target.stat().st_size)
        self.db.commit()
        return {"ingestion_run_id": str(run.ingestion_run_id), "source_file_id": str(source.source_file_id), "file_name": source.file_name, "file_hash": source.file_hash, "execution_mode": run.execution_mode}
    def profile_file(self, ingestion_run_id: uuid.UUID) -> dict:
        run=self.repo.get_run(ingestion_run_id); source=self.repo.get_source_file_by_run(ingestion_run_id)
        if not run or not source: raise ValueError('Ingestion run or source file not found')
        det=detect_file(source.source_url)
        source.detected_format=det.detected_format; source.detected_encoding=det.detected_encoding; source.detected_separator=det.detected_separator; source.status='PROFILED'; run.status='PROFILED'
        cfg=load_yaml_config('config/column_aliases.yaml')
        aliases={field: c.get('aliases',[]) for field,c in cfg.get('canonical_fields',{}).items()}
        df=read_csv(source.source_url, det.detected_encoding, det.detected_separator)
        profiles=profile_dataframe(df, aliases)
        self.db.commit()
        return {"ingestion_run_id": str(run.ingestion_run_id), "source_file_id": str(source.source_file_id), "detected_format": source.detected_format, "detected_encoding": source.detected_encoding, "detected_separator": source.detected_separator, "columns": [p.__dict__ for p in profiles]}
    def get_status(self, ingestion_run_id: uuid.UUID) -> dict:
        run=self.repo.get_run(ingestion_run_id)
        if not run: raise ValueError('Ingestion run not found')
        return {"ingestion_run_id": str(run.ingestion_run_id), "pipeline_status": run.status, "analysis_level": run.analysis_level, "summary": {}}
