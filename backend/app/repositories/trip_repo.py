from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.trip import Trip, Route, RouteSegment
from backend.app.repositories.base import BaseRepository

class TripRepository(BaseRepository[Trip]):
    def __init__(self):
        super().__init__(Trip)

    def create_route(self, db: Session, route: Route) -> Route:
        db.add(route)
        db.commit()
        db.refresh(route)
        return route

    def get_route_by_trip(self, db: Session, trip_id: str) -> Optional[Route]:
        return db.query(Route).filter(Route.trip_id == trip_id).first()

    def save_route_segments(self, db: Session, segments: List[RouteSegment]):
        db.bulk_save_objects(segments)
        db.commit()
