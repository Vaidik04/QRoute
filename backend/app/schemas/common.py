from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Unique error code identifier", json_schema_extra={"example": "RESOURCE_NOT_FOUND"})
    message: str = Field(..., description="Human-readable error explanation", json_schema_extra={"example": "Vehicle not found"})

class ErrorResponse(BaseModel):
    error: ErrorDetail
