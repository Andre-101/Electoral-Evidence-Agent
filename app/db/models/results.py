import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoteResult(Base):
    __tablename__ = "vote_results"
    vote_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_tables.polling_table_id"), nullable=False)
    electoral_option_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
    source_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_files.source_file_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TableTotal(Base):
    __tablename__ = "table_totals"
    table_total_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    polling_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polling_tables.polling_table_id"), nullable=False)
    registered_voters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_votes: Mapped[int] = mapped_column(Integer, nullable=False)
    blank_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    null_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmarked_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    option_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
