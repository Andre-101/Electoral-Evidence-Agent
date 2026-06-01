import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Period(Base):
    __tablename__ = "periods"
    period_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.country_id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Election(Base):
    __tablename__ = "elections"
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("periods.period_id"), nullable=False)
    election_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("election_types.election_type_id"), nullable=False)
    result_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("result_types.result_type_id"), nullable=False)
    election_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    election_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    expected_analysis_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PollingStation(Base):
    __tablename__ = "polling_stations"
    polling_station_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipality_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("municipalities.municipality_id"), nullable=False)
    station_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PollingStationElection(Base):
    __tablename__ = "polling_station_elections"
    polling_station_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_station_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_stations.polling_station_id"), nullable=False)
    station_name_as_reported: Mapped[str] = mapped_column(String(255), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_station_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PollingTable(Base):
    __tablename__ = "polling_tables"
    polling_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_station_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_station_elections.polling_station_election_id"), nullable=False)
    table_number: Mapped[str] = mapped_column(String(80), nullable=False)
    registered_voters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PartyMaster(Base):
    __tablename__ = "party_master"
    party_master_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="UNKNOWN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PartyElection(Base):
    __tablename__ = "party_elections"
    party_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    party_master_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("party_master.party_master_id"), nullable=True)
    party_name_as_reported: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CandidateMaster(Base):
    __tablename__ = "candidate_master"
    candidate_master_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CandidateElection(Base):
    __tablename__ = "candidate_elections"
    candidate_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    candidate_master_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_master.candidate_master_id"), nullable=True)
    candidate_name_as_reported: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    party_election_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("party_elections.party_election_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ElectoralOption(Base):
    __tablename__ = "electoral_options"
    electoral_option_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    option_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("option_types.option_type_id"), nullable=False)
    party_election_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("party_elections.party_election_id"), nullable=True)
    candidate_election_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_elections.candidate_election_id"), nullable=True)
    option_label: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
