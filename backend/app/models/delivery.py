from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from backend.app.db.base import Base

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(String, primary_key=True, index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    status = Column(String, default="PENDING") # PENDING, IN_TRANSIT, COMPLETED, FAILED
    priority = Column(Integer, default=1)
    time_window_start = Column(String, nullable=True)
    time_window_end = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
