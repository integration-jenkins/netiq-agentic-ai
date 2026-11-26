"""Export request and response schemas for verified NETIQ results."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExportRequest(BaseModel):
    """Request payload for POST /v1/export."""
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    result_id: str = Field(..., alias="resultId", min_length=1, description="Verified result identifier")
    format: Literal["XLSX"] = Field(default="XLSX", description="Target export file format")

    @model_validator(mode="before")
    @classmethod
    def _accept_snake_or_camel(cls, data: object) -> object:
        if isinstance(data, dict) and "result_id" in data and "resultId" not in data:
            copied = dict(data)
            copied["resultId"] = copied["result_id"]
            return copied
        return data


class ExportResponse(BaseModel):
    """Response payload returned after generating an Excel export."""
    model_config = ConfigDict(frozen=True)

    status: str = Field(default="COMPLETED", description="Job status ('COMPLETED', 'FAILED')")
    fileId: str = Field(..., description="Unique generated file identifier")
    fileName: str = Field(..., description="Sanitized download filename")
    downloadUrl: str = Field(..., description="Relative API download URL (/v1/export/{file_id})")
    rowCount: int = Field(default=0, description="Total rows exported")
