from sqlalchemy import String, Float, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.db.base import Base

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sumo_config_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="STOPPED") # STOPPED, RUNNING, PAUSED, COMPLETED, FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    metrics = relationship("SimulationMetric", back_populates="simulation", cascade="all, delete-orphan")

class SimulationMetric(Base):
    __tablename__ = "simulation_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_runs.id"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    active_vehicles: Mapped[int] = mapped_column(Integer, default=0)
    average_speed_kph: Mapped[float] = mapped_column(Float, default=0.0)
    total_emissions: Mapped[float] = mapped_column(Float, default=0.0)

    simulation = relationship("SimulationRun", back_populates="metrics")
