from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
from backend.app.db.base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True, index=True)
    vehicle_code = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, default="van") # van, truck, ev, emergency
    capacity = Column(Float, default=100.0)
    battery_capacity = Column(Float, nullable=True) # for EV mode
    current_battery = Column(Float, nullable=True) # for EV mode
    home_depot_id = Column(String, nullable=True)
    status = Column(String, default="IDLE") # IDLE, ACTIVE, CHARGING, MAINTENANCE
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
