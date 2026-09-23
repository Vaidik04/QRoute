from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.network import RoadNode, RoadEdge

class NetworkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_node(self, internal_node_id: str) -> Optional[RoadNode]:
        return self.db.query(RoadNode).filter(RoadNode.internal_node_id == internal_node_id).first()

    def get_edge(self, internal_edge_id: str) -> Optional[RoadEdge]:
        return self.db.query(RoadEdge).filter(RoadEdge.internal_edge_id == internal_edge_id).first()

    def list_nodes(self) -> List[RoadNode]:
        return self.db.query(RoadNode).all()

    def list_edges(self) -> List[RoadEdge]:
        return self.db.query(RoadEdge).all()

    def create_node(self, internal_id: str, lat: float, lng: float, osm_id: Optional[str] = None, sumo_id: Optional[str] = None) -> RoadNode:
        node = RoadNode(
            internal_node_id=internal_id,
            osm_node_id=osm_id,
            sumo_node_id=sumo_id,
            lat=lat,
            lng=lng
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def create_edge(self, internal_id: str, source_node_id: str, target_node_id: str, length_meters: float = 100.0, speed_limit_kph: float = 50.0, osm_way_id: Optional[str] = None, sumo_edge_id: Optional[str] = None) -> RoadEdge:
        edge = RoadEdge(
            internal_edge_id=internal_id,
            osm_way_id=osm_way_id,
            sumo_edge_id=sumo_edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            length_meters=length_meters,
            speed_limit_kph=speed_limit_kph
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge
