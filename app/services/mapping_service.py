from __future__ import annotations
import uuid
from sqlalchemy.orm import Session
from app.core.settings import load_yaml_config
from app.db.repositories.ingestion_repo import IngestionRepository
from app.ingestion.file_reader import read_csv
from app.ingestion.profiler import profile_dataframe

REQUIRED_FIELDS={"votes"}
TABLE_LEVEL_FIELDS={"department","municipality","polling_station","table_number","votes"}
STATION_LEVEL_FIELDS={"department","municipality","polling_station","votes"}
MUNICIPALITY_LEVEL_FIELDS={"department","municipality","votes"}

class MappingService:
    def __init__(self, db: Session): self.db=db; self.repo=IngestionRepository(db)
    def propose_mapping(self, ingestion_run_id: uuid.UUID, manual_mappings: list[dict] | None = None) -> dict:
        run=self.repo.get_run(ingestion_run_id); source=self.repo.get_source_file_by_run(ingestion_run_id)
        if not run or not source: raise ValueError('Ingestion run or source file not found')
        cfg=load_yaml_config('config/column_aliases.yaml')
        aliases={field: c.get('aliases',[]) for field,c in cfg.get('canonical_fields',{}).items()}
        df=read_csv(source.source_url, source.detected_encoding, source.detected_separator)
        profiles=profile_dataframe(df, aliases)
        manual={i['source_field_name']: i['canonical_field_name'] for i in (manual_mappings or [])}
        mappings=[]
        for p in profiles:
            canonical=manual.get(p.source_field_name) or p.candidate_for
            if canonical:
                method='MANUAL' if p.source_field_name in manual else 'DICTIONARY'
                item={"source_field_name": p.source_field_name, "canonical_field_name": canonical, "mapping_method": method, "confidence": 1.0, "status": "AUTO_ACCEPTED"}
                mappings.append(item)
                self.repo.save_mapping(source.source_file_id, p.source_field_name, canonical, method, 1.0, 'AUTO_ACCEPTED')
        mapped={m['canonical_field_name'] for m in mappings}
        if TABLE_LEVEL_FIELDS.issubset(mapped): level='TABLE_LEVEL'
        elif STATION_LEVEL_FIELDS.issubset(mapped): level='STATION_LEVEL'
        elif MUNICIPALITY_LEVEL_FIELDS.issubset(mapped): level='MUNICIPALITY_LEVEL'
        elif REQUIRED_FIELDS.issubset(mapped): level='DEPARTMENT_LEVEL'
        else: level='UNUSABLE'
        run.status='MAPPED'; run.analysis_level=level; self.db.commit()
        return {"ingestion_run_id": str(run.ingestion_run_id), "source_file_id": str(source.source_file_id), "mappings": mappings, "missing_required_fields": sorted(REQUIRED_FIELDS-mapped), "analysis_level_candidate": level}
