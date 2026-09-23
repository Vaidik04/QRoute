from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.fleet_service import FleetService
from app.schemas.fleet import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    return FleetService(db).create_customer(data)

@router.get("", response_model=List[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return FleetService(db).list_customers()

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    return FleetService(db).get_customer(customer_id)

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: str, data: CustomerUpdate, db: Session = Depends(get_db)):
    return FleetService(db).update_customer(customer_id, data)

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    FleetService(db).delete_customer(customer_id)
