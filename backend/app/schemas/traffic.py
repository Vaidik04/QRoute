from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime

class TrafficStateBase(BaseModel):
    internal_edge_id: str = Field(..., description="Internal road edge identifier")
    current_speed_kph: float = Field(..., ge=0, description="Current edge speed in kph, strictly non-negative")
    congestion_factor: float = Field(1.0, ge=0, description="Congestion multiplier (>= 0)")
    jam_length_meters: float = Field(0.0, ge=0, description="Jam queue length in meters (>= 0)")

    @field_validator('current_speed_kph', 'congestion_factor', 'jam_length_meters')
    @classmethod
    def validate_non_negative(cls, v: float, info) -> float:
        if v is None or v < 0:
            raise ValueError(f"{info.field_name} must be a non-negative number")
        return v

class TrafficStateCreate(TrafficStateBase):
    pass

class TrafficStateResponse(TrafficStateBase):
    id: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class TrafficPredictionResponse(BaseModel):
    id: str
    internal_edge_id: str
    predicted_speed_kph: float = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1.0)
    prediction_time: datetime
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class IncidentEdgeBase(BaseModel):
    internal_edge_id: str
    impact_factor: float = Field(0.1, ge=0, le=1.0)

class IncidentBase(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Accident near VIP Road"})
    incident_type: str = Field("ACCIDENT", json_schema_extra={"example": "ACCIDENT"})
    severity: str = Field("MEDIUM", json_schema_extra={"example": "HIGH"})
    description: Optional[str] = None
    status: str = Field("ACTIVE", json_schema_extra={"example": "ACTIVE"})

class IncidentCreate(IncidentBase):
    affected_edge_ids: List[str] = Field([], description="List of internal edge IDs impacted by incident")
    impact_factor: float = Field(0.1, ge=0, le=1.0)

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None

class IncidentResponse(IncidentBase):
    id: str
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
