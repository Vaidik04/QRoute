from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.routing import Trip, Route, RouteSegment
from app.schemas.routing import TripCreate, TripUpdate

class TripRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, trip_id: str) -> Optional[Trip]:
        return self.db.query(Trip).filter(Trip.id == trip_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Trip]:
        return self.db.query(Trip).offset(skip).limit(limit).all()

    def get_by_vehicle_id(self, vehicle_id: str) -> List[Trip]:
        return self.db.query(Trip).filter(Trip.vehicle_id == vehicle_id, Trip.status == "ACTIVE").all()

    def create(self, obj_in: TripCreate) -> Trip:
        db_obj = Trip(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, trip: Trip, obj_in: TripUpdate) -> Trip:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(trip, field, value)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def delete(self, trip_id: str) -> bool:
        trip = self.get_by_id(trip_id)
        if trip:
            self.db.delete(trip)
            self.db.commit()
            return True
        return False

    def create_route_for_trip(self, trip_id: str, total_distance: float, total_duration: float, geojson_str: str, segments: List[dict]) -> Route:
        route = Route(
            trip_id=trip_id,
            total_distance_meters=total_distance,
            total_duration_seconds=total_duration,
            route_geometry_geojson=geojson_str
        )
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)

        for seg in segments:
            r_seg = RouteSegment(
                route_id=route.id,
                internal_edge_id=seg['internal_edge_id'],
                sequence_order=seg['sequence_order'],
                expected_travel_time_seconds=seg.get('expected_travel_time_seconds', 0.0)
            )
            self.db.add(r_seg)

        self.db.commit()
        self.db.refresh(route)
        return route
