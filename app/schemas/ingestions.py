from typing import Any
from pydantic import BaseModel, Field

class ColumnProfileDTO(BaseModel):
    source_field_name: str
    inferred_type: str
    null_rate: float
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    candidate_for: str | None = None

class SourceMappingDTO(BaseModel):
    source_field_name: str
    canonical_field_name: str
    mapping_method: str
    confidence: float
    status: str
