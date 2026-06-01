import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TableMetric(Base):
    __tablename__ = "table_metrics"
    table_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_tables.polling_table_id"), nullable=False)
    turnout: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    valid_vote_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    blank_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    null_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    unmarked_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    winner_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    winner_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_share: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    runner_up_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)


class OptionTableMetric(Base):
    __tablename__ = "option_table_metrics"
    option_table_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_tables.polling_table_id"), nullable=False)
    electoral_option_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    vote_share: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    diff_vs_station: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    diff_vs_municipality: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    robust_z_vs_station: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    robust_z_vs_municipality: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)


class StationMetric(Base):
    __tablename__ = "station_metrics"
    station_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_station_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_station_elections.polling_station_election_id"), nullable=False)
    total_tables: Mapped[int] = mapped_column(Integer, nullable=False)
    total_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    average_turnout: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    median_turnout: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    turnout_mad: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    dominant_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    dominant_option_share: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)


class MunicipalityMetric(Base):
    __tablename__ = "municipality_metrics"
    municipality_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    municipality_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("municipalities.municipality_id"), nullable=False)
    total_stations: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tables: Mapped[int] = mapped_column(Integer, nullable=False)
    total_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    average_turnout: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    median_turnout: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    dominant_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    dominant_option_share: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)


class DigitTest(Base):
    __tablename__ = "digit_tests"
    digit_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    electoral_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    test_type: Mapped[str] = mapped_column(String(80), nullable=False)
    observations_count: Mapped[int] = mapped_column(Integer, nullable=False)
    statistic_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    p_value: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    result_flag: Mapped[str] = mapped_column(String(80), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
