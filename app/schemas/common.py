from typing import Any

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ApiWarning(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    success: bool
    status: str
    data: Any = Field(default_factory=dict)
    errors: list[ApiError] = Field(default_factory=list)
    warnings: list[ApiWarning] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
