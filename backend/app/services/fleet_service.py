from sqlalchemy.orm import Session
from typing import List
from app.repositories.fleet import VehicleRepository, CustomerRepository, DeliveryRepository
from app.schemas.fleet import (
    VehicleCreate, VehicleUpdate, VehicleResponse,
    CustomerCreate, CustomerUpdate, CustomerResponse,
    DeliveryCreate, DeliveryUpdate, DeliveryResponse
)
from app.core.exceptions import ResourceNotFoundException, ValidationException

class FleetService:
    def __init__(self, db: Session):
        self.vehicle_repo = VehicleRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.delivery_repo = DeliveryRepository(db)

    # Vehicles
    def create_vehicle(self, data: VehicleCreate) -> VehicleResponse:
        existing = self.vehicle_repo.get_by_plate(data.plate_number)
        if existing:
            raise ValidationException(f"Vehicle with plate number '{data.plate_number}' already exists.")
        return VehicleResponse.model_validate(self.vehicle_repo.create(data))

    def get_vehicle(self, vehicle_id: str) -> VehicleResponse:
        veh = self.vehicle_repo.get_by_id(vehicle_id)
        if not veh:
            raise ResourceNotFoundException("Vehicle", vehicle_id)
        return VehicleResponse.model_validate(veh)

    def list_vehicles(self) -> List[VehicleResponse]:
        return [VehicleResponse.model_validate(v) for v in self.vehicle_repo.list_all()]

    def update_vehicle(self, vehicle_id: str, data: VehicleUpdate) -> VehicleResponse:
        veh = self.vehicle_repo.get_by_id(vehicle_id)
        if not veh:
            raise ResourceNotFoundException("Vehicle", vehicle_id)
        return VehicleResponse.model_validate(self.vehicle_repo.update(veh, data))

    def delete_vehicle(self, vehicle_id: str):
        if not self.vehicle_repo.delete(vehicle_id):
            raise ResourceNotFoundException("Vehicle", vehicle_id)

    # Customers
    def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        return CustomerResponse.model_validate(self.customer_repo.create(data))

    def get_customer(self, customer_id: str) -> CustomerResponse:
        cust = self.customer_repo.get_by_id(customer_id)
        if not cust:
            raise ResourceNotFoundException("Customer", customer_id)
        return CustomerResponse.model_validate(cust)

    def list_customers(self) -> List[CustomerResponse]:
        return [CustomerResponse.model_validate(c) for c in self.customer_repo.list_all()]

    def update_customer(self, customer_id: str, data: CustomerUpdate) -> CustomerResponse:
        cust = self.customer_repo.get_by_id(customer_id)
        if not cust:
            raise ResourceNotFoundException("Customer", customer_id)
        return CustomerResponse.model_validate(self.customer_repo.update(cust, data))

    def delete_customer(self, customer_id: str):
        if not self.customer_repo.delete(customer_id):
            raise ResourceNotFoundException("Customer", customer_id)

    # Deliveries
    def create_delivery(self, data: DeliveryCreate) -> DeliveryResponse:
        customer = self.customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise ResourceNotFoundException("Customer", data.customer_id)
        return DeliveryResponse.model_validate(self.delivery_repo.create(data))

    def get_delivery(self, delivery_id: str) -> DeliveryResponse:
        deliv = self.delivery_repo.get_by_id(delivery_id)
        if not deliv:
            raise ResourceNotFoundException("Delivery", delivery_id)
        return DeliveryResponse.model_validate(deliv)

    def list_deliveries(self) -> List[DeliveryResponse]:
        return [DeliveryResponse.model_validate(d) for d in self.delivery_repo.list_all()]

    def update_delivery(self, delivery_id: str, data: DeliveryUpdate) -> DeliveryResponse:
        deliv = self.delivery_repo.get_by_id(delivery_id)
        if not deliv:
            raise ResourceNotFoundException("Delivery", delivery_id)
        return DeliveryResponse.model_validate(self.delivery_repo.update(deliv, data))

    def delete_delivery(self, delivery_id: str):
        if not self.delivery_repo.delete(delivery_id):
            raise ResourceNotFoundException("Delivery", delivery_id)
