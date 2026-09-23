from sqlalchemy import String, Float, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.db.base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plate_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="truck")
    capacity_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    capacity_volume: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    current_lat: Mapped[float] = mapped_column(Float, nullable=True)
    current_lng: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="IDLE") # IDLE, IN_TRANSIT, MAINTENANCE
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    time_window_start: Mapped[str] = mapped_column(String(10), nullable=True) # e.g. "09:00"
    time_window_end: Mapped[str] = mapped_column(String(10), nullable=True)   # e.g. "17:00"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    package_weight: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    package_volume: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="PENDING") # PENDING, ASSIGNED, IN_TRANSIT, DELIVERED, FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    customer = relationship("Customer", lazy="joined")
