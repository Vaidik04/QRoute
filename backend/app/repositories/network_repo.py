from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.network import RoadNode, RoadEdge
from backend.app.repositories.base import BaseRepository

class NetworkRepository:
    def get_node_by_external_id(self, db: Session, external_id: str) -> Optional[RoadNode]:
        return db.query(RoadNode).filter(RoadNode.external_node_id == external_id).first()

    def get_edge_by_sumo_id(self, db: Session, sumo_id: str) -> Optional[RoadEdge]:
        return db.query(RoadEdge).filter(RoadEdge.sumo_edge_id == sumo_id).first()

    def get_all_edges(self, db: Session) -> List[RoadEdge]:
        return db.query(RoadEdge).all()

    def get_all_nodes(self, db: Session) -> List[RoadNode]:
        return db.query(RoadNode).all()
