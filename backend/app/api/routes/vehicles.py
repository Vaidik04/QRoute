from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.fleet_service import FleetService
from app.schemas.fleet import VehicleCreate, VehicleUpdate, VehicleResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles (Fleet)"])

@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: VehicleCreate, db: Session = Depends(get_db)):
    return FleetService(db).create_vehicle(data)

@router.get("", response_model=List[VehicleResponse])
def list_vehicles(db: Session = Depends(get_db)):
    return FleetService(db).list_vehicles()

@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    return FleetService(db).get_vehicle(vehicle_id)

@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(vehicle_id: str, data: VehicleUpdate, db: Session = Depends(get_db)):
    return FleetService(db).update_vehicle(vehicle_id, data)

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    FleetService(db).delete_vehicle(vehicle_id)
