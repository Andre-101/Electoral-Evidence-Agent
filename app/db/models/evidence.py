import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_cases.review_case_id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    comparison_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_table: Mapped[str] = mapped_column(String(120), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(120), nullable=False)
    strength: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EvidenceDossier(Base):
    __tablename__ = "evidence_dossiers"
    evidence_dossier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_cases.review_case_id"), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    dossier_status: Mapped[str] = mapped_column(String(80), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    technical_summary: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_policy_status: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
