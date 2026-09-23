from sqlalchemy import String, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.db.base import Base

class TrafficState(Base):
    __tablename__ = "traffic_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_edge_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_edges.internal_edge_id"), nullable=False, index=True)
    current_speed_kph: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_factor: Mapped[float] = mapped_column(Float, default=1.0) # 1.0 = free flow, >1.0 = congested
    jam_length_meters: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    edge = relationship("RoadEdge", lazy="joined")

class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    internal_edge_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_edges.internal_edge_id"), nullable=False, index=True)
    predicted_speed_kph: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85)
    prediction_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(50), default="ACCIDENT") # ACCIDENT, ROADWORK, WEATHER, BLOCKAGE
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")       # LOW, MEDIUM, HIGH, CRITICAL
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")          # ACTIVE, RESOLVED, DISSIPATED
    reported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    affected_edges = relationship("IncidentEdge", back_populates="incident", cascade="all, delete-orphan")

class IncidentEdge(Base):
    __tablename__ = "incident_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    internal_edge_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_edges.internal_edge_id"), nullable=False)
    impact_factor: Mapped[float] = mapped_column(Float, default=0.1) # multiplier for speed reduction

    incident = relationship("Incident", back_populates="affected_edges")
