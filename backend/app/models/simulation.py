from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime
from backend.app.db.base import Base

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True, index=True) # SIM_1001
    scenario = Column(String, default="evening_peak_closure")
    seed = Column(Integer, default=42)
    duration_sec = Column(Integer, default=1800)
    active_vehicles = Column(Integer, default=50)
    status = Column(String, default="STARTED", index=True) # STARTED, RUNNING, PAUSED, STOPPED, COMPLETED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class SimulationMetrics(Base):
    __tablename__ = "simulation_metrics"

    id = Column(String, primary_key=True, index=True)
    simulation_id = Column(String, ForeignKey("simulation_runs.id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    average_speed = Column(Float, default=0.0)
    average_delay = Column(Float, default=0.0)
    queue_length = Column(Float, default=0.0)
    throughput = Column(Float, default=0.0)
    waiting_time = Column(Float, default=0.0)
    reroutes = Column(Integer, default=0)
