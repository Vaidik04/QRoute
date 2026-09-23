from sqlalchemy import String, Float, DateTime, ForeignKey, func, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.db.base import Base

class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PLANNED") # PLANNED, ACTIVE, COMPLETED, CANCELLED
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    vehicle = relationship("Vehicle", lazy="joined")
    routes = relationship("Route", back_populates="trip", order_by="Route.created_at.desc()")

class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), nullable=False)
    total_distance_meters: Mapped[float] = mapped_column(Float, default=0.0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    route_geometry_geojson: Mapped[str] = mapped_column(Text, nullable=True) # GeoJSON FeatureCollection/LineString
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip = relationship("Trip", back_populates="routes")
    segments = relationship("RouteSegment", back_populates="route", order_by="RouteSegment.sequence_order", cascade="all, delete-orphan")

class RouteSegment(Base):
    __tablename__ = "route_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id: Mapped[str] = mapped_column(String(36), ForeignKey("routes.id"), nullable=False)
    internal_edge_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_edges.internal_edge_id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_travel_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    route = relationship("Route", back_populates="segments")
    edge = relationship("RoadEdge", lazy="joined")
