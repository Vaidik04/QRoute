from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class IncidentCreateSchema(BaseModel):
    type: str = Field("ROAD_CLOSURE", example="ROAD_CLOSURE")
    affected_edges: List[str] = Field(..., example=["R17", "R18"])
    severity: str = Field("HIGH", example="HIGH")
    description: Optional[str] = Field(None, example="Main road blockage due to accident")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class IncidentResponseSchema(BaseModel):
    id: str
    type: str
    affected_edges: List[str]
    severity: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    created_at: datetime
