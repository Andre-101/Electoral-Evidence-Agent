from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.catalogs import Country, Department, ElectionType, Municipality, OptionType, ResultType
from app.db.models.control import SourceMapping
from app.db.models.electoral_core import (
    CandidateElection,
    CandidateMaster,
    Election,
    ElectoralOption,
    PartyElection,
    PartyMaster,
    Period,
    PollingStation,
    PollingStationElection,
    PollingTable,
)
from app.db.models.results import VoteResult
from app.db.repositories.ingestion_repo import IngestionRepository
from app.ingestion.file_reader import read_csv
from app.services.normalization_service import (
    infer_option_type,
    normalize_key,
    normalize_label,
    parse_int,
)


@dataclass
class CoreLoadSummary:
    election_id: str
    ingestion_run_id: str
    records_read: int
    vote_results_upserted: int
    departments_touched: int
    municipalities_touched: int
    polling_stations_touched: int
    polling_tables_touched: int
    electoral_options_touched: int
    skipped_records: int


class CoreLoadService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = IngestionRepository(db)

    def _get_or_create(self, model, defaults: dict | None = None, **kwargs):
        instance = self.db.query(model).filter_by(**kwargs).one_or_none()
        if instance:
            return instance
        data = {**kwargs, **(defaults or {})}
        instance = model(**data)
        self.db.add(instance)
        self.db.flush()
        return instance

    def _get_pilot_election(self) -> Election:
        election = self.db.query(Election).order_by(Election.created_at.asc()).first()
        if not election:
            raise ValueError("No election exists. Run seed_pilot_election.py first.")
        return election

    def _field_map(self, source_file_id: uuid.UUID) -> dict[str, str]:
        mappings = self.db.query(SourceMapping).filter_by(source_file_id=source_file_id).all()
        return {m.canonical_field_name: m.source_field_name for m in mappings}

    def _value(self, row: dict, field_map: dict[str, str], canonical: str):
        source_field = field_map.get(canonical)
        if not source_field:
            return None
        return row.get(source_field)

    def load_to_core(self, ingestion_run_id: uuid.UUID) -> dict:
        run = self.repo.get_run(ingestion_run_id)
        if run is None:
            raise ValueError(f"Ingestion run not found: {ingestion_run_id}")

        source = self.repo.get_source_file_by_run(ingestion_run_id)
        if source is None:
            raise ValueError(f"Source file not found for ingestion run: {ingestion_run_id}")

        election = self.db.get(Election, source.election_id) if source.election_id else self._get_pilot_election()
        if source.election_id is None:
            source.election_id = election.election_id

        country = self.db.query(Country).filter_by(iso_code="COL").one()
        field_map = self._field_map(source.source_file_id)
        required = {"department", "municipality", "polling_station", "table_number", "votes"}
        missing = sorted(required - set(field_map))
        if missing:
            raise ValueError(f"Missing mapped fields for TABLE_LEVEL load: {missing}")

        df = read_csv(source.source_url, encoding=source.detected_encoding, separator=source.detected_separator)
        rows = df.to_dicts()

        touched_departments = set()
        touched_municipalities = set()
        touched_stations = set()
        touched_tables = set()
        touched_options = set()
        vote_results_upserted = 0
        skipped_records = 0

        for row in rows:
            try:
                department_raw = normalize_label(self._value(row, field_map, "department"))
                municipality_raw = normalize_label(self._value(row, field_map, "municipality"))
                station_raw = normalize_label(self._value(row, field_map, "polling_station"))
                table_number = normalize_label(self._value(row, field_map, "table_number"))
                candidate_raw = normalize_label(self._value(row, field_map, "candidate"))
                party_raw = normalize_label(self._value(row, field_map, "party"))
                votes = parse_int(self._value(row, field_map, "votes"))
                registered_voters = parse_int(self._value(row, field_map, "registered_voters"))

                if not department_raw or not municipality_raw or not station_raw or not table_number or votes is None:
                    skipped_records += 1
                    continue

                department = self._get_or_create(
                    Department,
                    country_id=country.country_id,
                    normalized_name=normalize_key(department_raw),
                    defaults={"department_name": department_raw},
                )
                municipality = self._get_or_create(
                    Municipality,
                    department_id=department.department_id,
                    normalized_name=normalize_key(municipality_raw),
                    defaults={"municipality_name": municipality_raw},
                )
                station = self._get_or_create(
                    PollingStation,
                    municipality_id=municipality.municipality_id,
                    normalized_name=normalize_key(station_raw),
                    defaults={"canonical_name": station_raw},
                )
                station_election = self._get_or_create(
                    PollingStationElection,
                    election_id=election.election_id,
                    polling_station_id=station.polling_station_id,
                    station_name_as_reported=station_raw,
                    defaults={},
                )
                polling_table = self._get_or_create(
                    PollingTable,
                    election_id=election.election_id,
                    polling_station_election_id=station_election.polling_station_election_id,
                    table_number=table_number,
                    defaults={"registered_voters": registered_voters},
                )
                if registered_voters is not None and polling_table.registered_voters is None:
                    polling_table.registered_voters = registered_voters

                option_type_code = infer_option_type(candidate_raw, party_raw)
                option_type = self.db.query(OptionType).filter_by(code=option_type_code).one()

                party_election = None
                if party_raw and option_type_code in {"CANDIDATE", "PARTY"}:
                    party_master = self._get_or_create(
                        PartyMaster,
                        normalized_name=normalize_key(party_raw),
                        defaults={"canonical_name": party_raw, "status": "UNKNOWN"},
                    )
                    party_election = self._get_or_create(
                        PartyElection,
                        election_id=election.election_id,
                        normalized_name=normalize_key(party_raw),
                        defaults={
                            "party_master_id": party_master.party_master_id,
                            "party_name_as_reported": party_raw,
                        },
                    )

                candidate_election = None
                if candidate_raw and option_type_code == "CANDIDATE":
                    candidate_master = self._get_or_create(
                        CandidateMaster,
                        normalized_name=normalize_key(candidate_raw),
                        defaults={"canonical_name": candidate_raw},
                    )
                    candidate_election = self._get_or_create(
                        CandidateElection,
                        election_id=election.election_id,
                        normalized_name=normalize_key(candidate_raw),
                        party_election_id=party_election.party_election_id if party_election else None,
                        defaults={
                            "candidate_master_id": candidate_master.candidate_master_id,
                            "candidate_name_as_reported": candidate_raw,
                        },
                    )

                option_label = candidate_raw or party_raw or option_type_code
                electoral_option = self._get_or_create(
                    ElectoralOption,
                    election_id=election.election_id,
                    option_type_id=option_type.option_type_id,
                    normalized_label=normalize_key(option_label),
                    defaults={
                        "option_label": option_label,
                        "party_election_id": party_election.party_election_id if party_election else None,
                        "candidate_election_id": candidate_election.candidate_election_id if candidate_election else None,
                    },
                )

                existing_vote = (
                    self.db.query(VoteResult)
                    .filter_by(
                        election_id=election.election_id,
                        polling_table_id=polling_table.polling_table_id,
                        electoral_option_id=electoral_option.electoral_option_id,
                    )
                    .one_or_none()
                )
                if existing_vote:
                    existing_vote.votes = votes
                    existing_vote.ingestion_run_id = ingestion_run_id
                    existing_vote.source_file_id = source.source_file_id
                else:
                    vote_result = VoteResult(
                        election_id=election.election_id,
                        polling_table_id=polling_table.polling_table_id,
                        electoral_option_id=electoral_option.electoral_option_id,
                        votes=votes,
                        ingestion_run_id=ingestion_run_id,
                        source_file_id=source.source_file_id,
                    )
                    self.db.add(vote_result)
                vote_results_upserted += 1

                touched_departments.add(str(department.department_id))
                touched_municipalities.add(str(municipality.municipality_id))
                touched_stations.add(str(station.polling_station_id))
                touched_tables.add(str(polling_table.polling_table_id))
                touched_options.add(str(electoral_option.electoral_option_id))
            except Exception:
                skipped_records += 1
                continue

        run.status = "LOADED_TO_CORE"
        source.status = "PROCESSED"
        self.db.commit()

        summary = CoreLoadSummary(
            election_id=str(election.election_id),
            ingestion_run_id=str(ingestion_run_id),
            records_read=len(rows),
            vote_results_upserted=vote_results_upserted,
            departments_touched=len(touched_departments),
            municipalities_touched=len(touched_municipalities),
            polling_stations_touched=len(touched_stations),
            polling_tables_touched=len(touched_tables),
            electoral_options_touched=len(touched_options),
            skipped_records=skipped_records,
        )
        return summary.__dict__

    def get_core_summary(self, ingestion_run_id: uuid.UUID) -> dict:
        source = self.repo.get_source_file_by_run(ingestion_run_id)
        run = self.repo.get_run(ingestion_run_id)
        election_id = source.election_id if source and source.election_id else None
        return {
            "ingestion_run_id": str(ingestion_run_id),
            "pipeline_status": run.status if run else None,
            "election_id": str(election_id) if election_id else None,
            "vote_results": self.db.query(VoteResult).filter_by(ingestion_run_id=ingestion_run_id).count(),
            "polling_tables": self.db.query(PollingTable).count(),
            "polling_stations": self.db.query(PollingStation).count(),
            "electoral_options": self.db.query(ElectoralOption).count(),
        }
