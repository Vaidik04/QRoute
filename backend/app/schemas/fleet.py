from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class VehicleBase(BaseModel):
    plate_number: str = Field(..., description="Unique license plate number", json_schema_extra={"example": "MP04-AB-1234"})
    vehicle_type: str = Field("truck", json_schema_extra={"example": "truck"})
    capacity_weight: float = Field(1000.0, gt=0, json_schema_extra={"example": 1000.0})
    capacity_volume: float = Field(10.0, gt=0, json_schema_extra={"example": 10.0})
    current_lat: Optional[float] = Field(None, ge=-90, le=90)
    current_lng: Optional[float] = Field(None, ge=-180, le=180)
    status: str = Field("IDLE", json_schema_extra={"example": "IDLE"})

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    capacity_weight: Optional[float] = Field(None, gt=0)
    capacity_volume: Optional[float] = Field(None, gt=0)
    current_lat: Optional[float] = Field(None, ge=-90, le=90)
    current_lng: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CustomerBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Bhopal Central Depot"})
    address: Optional[str] = Field(None, json_schema_extra={"example": "Arera Colony, Bhopal"})
    lat: float = Field(..., ge=-90, le=90, json_schema_extra={"example": 23.2332})
    lng: float = Field(..., ge=-180, le=180, json_schema_extra={"example": 77.4343})
    time_window_start: Optional[str] = Field(None, json_schema_extra={"example": "09:00"})
    time_window_end: Optional[str] = Field(None, json_schema_extra={"example": "17:00"})

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeliveryBase(BaseModel):
    customer_id: str = Field(..., description="ID of the customer receiving delivery")
    package_weight: float = Field(10.0, gt=0, json_schema_extra={"example": 15.5})
    package_volume: float = Field(0.1, gt=0, json_schema_extra={"example": 0.2})
    priority: int = Field(1, ge=1, le=5, json_schema_extra={"example": 1})
    status: str = Field("PENDING", json_schema_extra={"example": "PENDING"})

class DeliveryCreate(DeliveryBase):
    pass

class DeliveryUpdate(BaseModel):
    customer_id: Optional[str] = None
    package_weight: Optional[float] = Field(None, gt=0)
    package_volume: Optional[float] = Field(None, gt=0)
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None

class DeliveryResponse(DeliveryBase):
    id: str
    created_at: datetime
    customer: Optional[CustomerResponse] = None
    model_config = ConfigDict(from_attributes=True)
