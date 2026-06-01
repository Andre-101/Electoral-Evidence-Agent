import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QualityAlert(Base):
    __tablename__ = "quality_alerts"
    quality_alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
    election_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=True)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    alert_code: Mapped[str] = mapped_column(String(120), ForeignKey("alert_catalog.alert_code"), nullable=False)
    severity: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("source_files.source_file_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EdaAlert(Base):
    __tablename__ = "eda_alerts"
    eda_alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    electoral_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    alert_code: Mapped[str] = mapped_column(String(120), ForeignKey("alert_catalog.alert_code"), nullable=False)
    severity: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    comparison_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"
    anomaly_score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    electoral_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    review_priority_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    priority: Mapped[str] = mapped_column(String(80), nullable=False)
    statistical_confidence: Mapped[str] = mapped_column(String(80), nullable=False)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    main_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ScoreComponent(Base):
    __tablename__ = "score_components"
    score_component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anomaly_score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("anomaly_scores.anomaly_score_id"), nullable=False)
    source_alert_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_alert_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    component_type: Mapped[str] = mapped_column(String(80), nullable=False)
    component_name: Mapped[str] = mapped_column(String(120), nullable=False)
    points: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReviewCase(Base):
    __tablename__ = "review_cases"
    review_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("elections.election_id"), nullable=False)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False)
    anomaly_score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("anomaly_scores.anomaly_score_id"), nullable=False)
    entity_level: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    electoral_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("electoral_options.electoral_option_id"), nullable=True)
    review_priority_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    priority: Mapped[str] = mapped_column(String(80), nullable=False)
    statistical_confidence: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="OPEN")
    case_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
