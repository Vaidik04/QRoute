from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
import uuid
from app.db.base import Base

class RoadNode(Base):
    __tablename__ = "road_nodes"

    internal_node_id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"node_{uuid.uuid4().hex[:12]}")
    osm_node_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    sumo_node_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)

class RoadEdge(Base):
    __tablename__ = "road_edges"

    internal_edge_id: Mapped[str] = mapped_column(String(100), primary_key=True, default=lambda: f"edge_{uuid.uuid4().hex[:12]}")
    osm_way_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    sumo_edge_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    source_node_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_nodes.internal_node_id"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(100), ForeignKey("road_nodes.internal_node_id"), nullable=False)
    length_meters: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    speed_limit_kph: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    geom = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=True)

    source_node = relationship("RoadNode", foreign_keys=[source_node_id], lazy="joined")
    target_node = relationship("RoadNode", foreign_keys=[target_node_id], lazy="joined")
