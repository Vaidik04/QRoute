from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.repositories.routing import TripRepository
from app.repositories.fleet import VehicleRepository
from app.schemas.routing import TripCreate, TripUpdate, TripResponse
from app.core.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/trips", tags=["Trips & Routing"])

@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    veh = VehicleRepository(db).get_by_id(data.vehicle_id)
    if not veh:
        raise ResourceNotFoundException("Vehicle", data.vehicle_id)
    repo = TripRepository(db)
    return TripResponse.model_validate(repo.create(data))

@router.get("", response_model=List[TripResponse])
def list_trips(db: Session = Depends(get_db)):
    repo = TripRepository(db)
    return [TripResponse.model_validate(t) for t in repo.list_all()]

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    repo = TripRepository(db)
    trip = repo.get_by_id(trip_id)
    if not trip:
        raise ResourceNotFoundException("Trip", trip_id)
    return TripResponse.model_validate(trip)

@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(trip_id: str, data: TripUpdate, db: Session = Depends(get_db)):
    repo = TripRepository(db)
    trip = repo.get_by_id(trip_id)
    if not trip:
        raise ResourceNotFoundException("Trip", trip_id)
    return TripResponse.model_validate(repo.update(trip, data))

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: str, db: Session = Depends(get_db)):
    repo = TripRepository(db)
    if not repo.delete(trip_id):
        raise ResourceNotFoundException("Trip", trip_id)
