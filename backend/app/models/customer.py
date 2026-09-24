from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime
from backend.app.db.base import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    customer_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    demand = Column(Float, default=10.0)
    priority = Column(Integer, default=1)
    service_time_sec = Column(Integer, default=300) # 5 minutes
    time_window_start = Column(String, nullable=True) # ISO or HH:MM
    time_window_end = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
