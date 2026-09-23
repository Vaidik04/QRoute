from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.fleet_service import FleetService
from app.schemas.fleet import DeliveryCreate, DeliveryUpdate, DeliveryResponse

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

@router.post("", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
def create_delivery(data: DeliveryCreate, db: Session = Depends(get_db)):
    return FleetService(db).create_delivery(data)

@router.get("", response_model=List[DeliveryResponse])
def list_deliveries(db: Session = Depends(get_db)):
    return FleetService(db).list_deliveries()

@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    return FleetService(db).get_delivery(delivery_id)

@router.put("/{delivery_id}", response_model=DeliveryResponse)
def update_delivery(delivery_id: str, data: DeliveryUpdate, db: Session = Depends(get_db)):
    return FleetService(db).update_delivery(delivery_id, data)

@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery(delivery_id: str, db: Session = Depends(get_db)):
    FleetService(db).delete_delivery(delivery_id)
