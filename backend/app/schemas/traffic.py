from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class TrafficStateSchema(BaseModel):
    edge_id: str = Field(..., example="R17")
    timestamp: datetime
    speed_kmh: float = Field(..., example=24.5)
    travel_time_sec: float = Field(..., example=184.0)
    density: Optional[float] = 0.0
    flow: Optional[float] = 0.0
    congestion: float = Field(..., example=0.72)
    queue_length: Optional[float] = 0.0
    status: str = Field("OPEN", example="OPEN")
    source: str = Field("SIMULATED", example="SIMULATED")

class TrafficPredictionSchema(BaseModel):
    edge_id: str = Field(..., example="R17")
    generated_at: datetime
    target_time: datetime
    horizon_min: int = Field(10, example=10)
    predicted_speed: float = Field(..., example=22.0)
    predicted_travel_time: float = Field(..., example=200.0)
    model_name: str = Field("ST-GNN-TrafficNet", example="ST-GNN-TrafficNet")
    confidence: float = Field(0.92, example=0.92)
