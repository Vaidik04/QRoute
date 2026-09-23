from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field("ok", json_schema_extra={"example": "ok"})
    service: str = Field("q-transit-nexus-backend", json_schema_extra={"example": "q-transit-nexus-backend"})
    version: str = Field("1.0.0", json_schema_extra={"example": "1.0.0"})
