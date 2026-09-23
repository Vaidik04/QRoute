from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.fleet import Vehicle, Customer, Delivery
from app.schemas.fleet import VehicleCreate, VehicleUpdate, CustomerCreate, CustomerUpdate, DeliveryCreate, DeliveryUpdate

class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, vehicle_id: str) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    def get_by_plate(self, plate: str) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.plate_number == plate).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Vehicle]:
        return self.db.query(Vehicle).offset(skip).limit(limit).all()

    def create(self, obj_in: VehicleCreate) -> Vehicle:
        db_obj = Vehicle(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, vehicle: Vehicle, obj_in: VehicleUpdate) -> Vehicle:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vehicle, field, value)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def delete(self, vehicle_id: str) -> bool:
        vehicle = self.get_by_id(vehicle_id)
        if vehicle:
            self.db.delete(vehicle)
            self.db.commit()
            return True
        return False

class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        return self.db.query(Customer).offset(skip).limit(limit).all()

    def create(self, obj_in: CustomerCreate) -> Customer:
        db_obj = Customer(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, customer: Customer, obj_in: CustomerUpdate) -> Customer:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def delete(self, customer_id: str) -> bool:
        customer = self.get_by_id(customer_id)
        if customer:
            self.db.delete(customer)
            self.db.commit()
            return True
        return False

class DeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, delivery_id: str) -> Optional[Delivery]:
        return self.db.query(Delivery).filter(Delivery.id == delivery_id).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Delivery]:
        return self.db.query(Delivery).offset(skip).limit(limit).all()

    def create(self, obj_in: DeliveryCreate) -> Delivery:
        db_obj = Delivery(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, delivery: Delivery, obj_in: DeliveryUpdate) -> Delivery:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(delivery, field, value)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def delete(self, delivery_id: str) -> bool:
        delivery = self.get_by_id(delivery_id)
        if delivery:
            self.db.delete(delivery)
            self.db.commit()
            return True
        return False
