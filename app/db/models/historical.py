import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntityCrosswalk(Base):
    __tablename__ = "entity_crosswalks"
    entity_crosswalk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    match_method: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class HistoricalComparison(Base):
    __tablename__ = "historical_comparisons"
    historical_comparison_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    target_election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    absolute_change: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    relative_change: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    comparison_confidence: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
