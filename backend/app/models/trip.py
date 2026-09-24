from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey, DateTime
from backend.app.db.base import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)
    mode = Column(String, default="car") # car, delivery, public_transport, ev, emergency
    objective = Column(String, default="balanced") # time, distance, congestion, balanced
    status = Column(String, default="ACTIVE") # ACTIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

class Route(Base):
    __tablename__ = "routes"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
    optimization_run_id = Column(String, ForeignKey("optimization_runs.id"), nullable=True)
    algorithm = Column(String, default="adaptive_d_qpso")
    distance_m = Column(Float, default=0.0)
    travel_time_sec = Column(Float, default=0.0)
    fitness = Column(Float, default=0.0)
    status = Column(String, default="FEASIBLE") # FEASIBLE, INFEASIBLE
    route_geometry_json = Column(Text, nullable=True) # GeoJSON LineString
    created_at = Column(DateTime, default=datetime.utcnow)

class RouteSegment(Base):
    __tablename__ = "route_segments"

    id = Column(String, primary_key=True, index=True)
    route_id = Column(String, ForeignKey("routes.id"), index=True, nullable=False)
    sequence = Column(Integer, nullable=False)
    edge_id = Column(String, ForeignKey("road_edges.id"), nullable=False)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    travel_time_sec = Column(Float, default=0.0)
