from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime
from backend.app.db.base import Base

class TrafficState(Base):
    __tablename__ = "traffic_states"

    id = Column(String, primary_key=True, index=True)
    edge_id = Column(String, ForeignKey("road_edges.id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    speed_kmh = Column(Float, nullable=False)
    density = Column(Float, default=0.0) # vehicles per km
    flow = Column(Float, default=0.0) # vehicles per hr
    travel_time_sec = Column(Float, nullable=False)
    congestion = Column(Float, default=0.0) # 0.0 (free flow) to 1.0 (jammed)
    queue_length = Column(Float, default=0.0)
    status = Column(String, default="OPEN") # OPEN, CONGESTED, CLOSED
    source = Column(String, default="SIMULATED") # SIMULATED, OBSERVED, HISTORICAL
    confidence = Column(Float, default=1.0)

class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"

    id = Column(String, primary_key=True, index=True)
    edge_id = Column(String, ForeignKey("road_edges.id"), index=True, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    target_time = Column(DateTime, index=True, nullable=False)
    horizon_min = Column(Integer, default=10) # horizon in minutes (e.g. T+10)
    predicted_speed = Column(Float, nullable=False)
    predicted_travel_time = Column(Float, nullable=False)
    model_name = Column(String, default="ST-GNN-TrafficNet")
    model_version = Column(String, default="v1.2")
    confidence = Column(Float, default=0.92)
