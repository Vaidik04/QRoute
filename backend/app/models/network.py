from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey
from backend.app.db.base import Base

class RoadNode(Base):
    __tablename__ = "road_nodes"

    id = Column(String, primary_key=True, index=True) # Canonical internal node ID (e.g. NODE_01)
    external_node_id = Column(String, index=True, nullable=True) # OSM or SUMO node ID
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    node_type = Column(String, default="junction") # junction, depot, customer_stop, transit_hub
    metadata_json = Column(Text, nullable=True)

class RoadEdge(Base):
    __tablename__ = "road_edges"

    id = Column(String, primary_key=True, index=True) # Canonical internal edge ID (e.g. R17)
    external_edge_id = Column(String, index=True, nullable=True) # External provider edge ID
    sumo_edge_id = Column(String, index=True, nullable=True) # SUMO edge ID
    osm_edge_id = Column(String, index=True, nullable=True) # OSM way ID
    
    from_node_id = Column(String, ForeignKey("road_nodes.id"), nullable=False)
    to_node_id = Column(String, ForeignKey("road_nodes.id"), nullable=False)
    
    geometry_json = Column(Text, nullable=True) # GeoJSON LineString coordinates [[lon, lat], ...]
    length_m = Column(Float, nullable=False, default=100.0)
    lanes = Column(Integer, default=2)
    speed_limit_kmh = Column(Float, default=50.0)
    one_way = Column(Boolean, default=False)
    road_type = Column(String, default="secondary") # primary, secondary, highway, residential
    metadata_json = Column(Text, nullable=True)
