from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime
from backend.app.db.base import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, default="ROAD_CLOSURE") # ROAD_CLOSURE, ACCIDENT, CONSTRUCTION, SEVERE_CONGESTION
    severity = Column(String, default="HIGH") # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    status = Column(String, default="ACTIVE") # ACTIVE, RESOLVED, CANCELLED
    source = Column(String, default="SIMULATION_INJECTED")
    created_at = Column(DateTime, default=datetime.utcnow)

class IncidentEdge(Base):
    __tablename__ = "incident_edges"

    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), index=True, nullable=False)
    edge_id = Column(String, ForeignKey("road_edges.id"), index=True, nullable=False)
