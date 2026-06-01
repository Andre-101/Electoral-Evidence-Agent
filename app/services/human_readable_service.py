from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.electoral_core import (
    CandidateElection,
    CandidateMaster,
    ElectoralOption,
    PartyElection,
    PartyMaster,
    PollingStation,
    PollingStationElection,
    PollingTable,
)
from app.db.models.catalogs import Department, Municipality, OptionType


def _first_attr(obj, names: list[str], default=None):
    if obj is None:
        return default
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value not in (None, ""):
                return value
    return default


class HumanReadableService:
    def __init__(self, db: Session):
        self.db = db

    def describe_review_case(self, case_detail: dict) -> dict:
        entity_level = case_detail.get("entity_level")
        entity_id = case_detail.get("entity_id")
        option_id = case_detail.get("electoral_option_id")

        entity = self.describe_entity(entity_level, entity_id)
        option = self.describe_electoral_option(option_id) if option_id else None

        return {
            "entity": entity,
            "electoral_option": option,
            "display_title": self._display_title(entity, option),
        }

    def describe_entity(self, entity_level: str | None, entity_id: str | None) -> dict:
        if not entity_level or not entity_id:
            return {"label": "Entidad no disponible", "technical_id": entity_id}

        if entity_level == "POLLING_TABLE":
            return self.describe_polling_table(entity_id)

        if entity_level == "VOTE_RESULT":
            return {
                "label": "Resultado de votación",
                "technical_id": entity_id,
                "details": "Registro individual de resultado electoral.",
            }

        return {
            "label": entity_level.replace("_", " ").title(),
            "technical_id": entity_id,
        }

    def describe_polling_table(self, polling_table_id: str) -> dict:
        table = self.db.get(PollingTable, uuid.UUID(polling_table_id))
        if table is None:
            return {"label": "Mesa no encontrada", "technical_id": polling_table_id}

        station_election = self.db.get(PollingStationElection, table.polling_station_election_id)
        station = self.db.get(PollingStation, station_election.polling_station_id) if station_election else None
        municipality = self.db.get(Municipality, station.municipality_id) if station else None
        department = self.db.get(Department, municipality.department_id) if municipality else None

        station_name = _first_attr(
            station,
            ["name", "station_name", "polling_station_name", "display_name", "code", "station_code"],
            "Puesto no disponible",
        )
        table_number = _first_attr(
            table,
            ["table_number", "number", "table_code", "code"],
            "Mesa no disponible",
        )
        municipality_name = _first_attr(
            municipality,
            ["name", "municipality_name", "display_name", "code"],
            "Municipio no disponible",
        )
        department_name = _first_attr(
            department,
            ["name", "department_name", "display_name", "code"],
            "Departamento no disponible",
        )
        registered_voters = _first_attr(
            table,
            ["registered_voters", "census", "voter_count"],
            None,
        )

        label = f"Mesa {table_number} — {station_name}"
        location = f"{municipality_name}, {department_name}"

        return {
            "label": label,
            "technical_id": polling_table_id,
            "table_number": table_number,
            "polling_station": station_name,
            "municipality": municipality_name,
            "department": department_name,
            "location": location,
            "registered_voters": registered_voters,
        }

    def describe_electoral_option(self, electoral_option_id: str | None) -> dict | None:
        if not electoral_option_id:
            return None

        option = self.db.get(ElectoralOption, uuid.UUID(electoral_option_id))
        if option is None:
            return {"label": "Opción electoral no encontrada", "technical_id": electoral_option_id}

        option_type = self.db.get(OptionType, option.option_type_id)
        option_type_code = _first_attr(option_type, ["code", "name"], None)

        candidate_name = None
        party_name = None

        candidate_election_id = _first_attr(option, ["candidate_election_id"], None)
        if candidate_election_id:
            candidate_election = self.db.get(CandidateElection, candidate_election_id)
            candidate = self.db.get(CandidateMaster, candidate_election.candidate_id) if candidate_election else None
            candidate_name = _first_attr(candidate, ["full_name", "name", "candidate_name"], None)

        party_election_id = _first_attr(option, ["party_election_id"], None)
        if party_election_id:
            party_election = self.db.get(PartyElection, party_election_id)
            party = self.db.get(PartyMaster, party_election.party_id) if party_election else None
            party_name = _first_attr(party, ["name", "party_name", "display_name"], None)

        if candidate_name and party_name:
            label = f"{candidate_name} — {party_name}"
        elif candidate_name:
            label = candidate_name
        elif party_name:
            label = party_name
        elif option_type_code == "BLANK":
            label = "Voto en blanco"
        elif option_type_code == "NULL":
            label = "Voto nulo"
        elif option_type_code == "UNMARKED":
            label = "Voto no marcado"
        else:
            label = "Opción electoral"

        return {
            "label": label,
            "technical_id": electoral_option_id,
            "candidate": candidate_name,
            "party": party_name,
            "option_type": option_type_code,
        }

    def _display_title(self, entity: dict, option: dict | None) -> str:
        if option:
            return f"{entity.get('label', 'Entidad')} / {option.get('label', 'Opción')}"
        return entity.get("label", "Caso de revisión")

    def replace_known_ids_in_text(self, text: str | None, case_detail: dict) -> str:
        if not text:
            return ""

        readable = self.describe_review_case(case_detail)
        entity = readable["entity"]
        option = readable.get("electoral_option")

        replacements = {}

        entity_id = case_detail.get("entity_id")
        if entity_id:
            replacements[entity_id] = entity.get("label", entity_id)

        option_id = case_detail.get("electoral_option_id")
        if option_id and option:
            replacements[option_id] = option.get("label", option_id)

        election_id = case_detail.get("election_id")
        if election_id:
            replacements[election_id] = "la elección analizada"

        result = text
        for raw, human in replacements.items():
            result = result.replace(f"**{raw}**", f"**{human}**")
            result = result.replace(raw, human)

        return result
