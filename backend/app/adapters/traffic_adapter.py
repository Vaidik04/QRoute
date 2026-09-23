from typing import Dict, Any, Optional
from app.core.exceptions import ValidationException
from app.schemas.traffic import TrafficStateCreate
from app.core.logging import logger

class TrafficAdapter:
    """
    Adapter that normalizes external/Member 2 traffic provider state payloads
    into canonical internal TrafficState models. Rejects invalid inputs (negative speed,
    nulls without fallback) before they reach the optimizer.
    """
    @staticmethod
    def normalize_traffic_payload(raw_data: Dict[str, Any]) -> TrafficStateCreate:
        internal_edge_id = raw_data.get("internal_edge_id") or raw_data.get("edge_id") or raw_data.get("sumo_edge_id")
        if not internal_edge_id:
            raise ValidationException("Traffic update payload missing required 'edge_id' or 'internal_edge_id'")

        raw_speed = raw_data.get("current_speed_kph")
        if raw_speed is None:
            raw_speed = raw_data.get("speed")
        
        if raw_speed is None:
            raise ValidationException(f"Traffic update for edge '{internal_edge_id}' contains null speed without fallback.")
        
        try:
            speed_kph = float(raw_speed)
        except (ValueError, TypeError):
            raise ValidationException(f"Invalid non-numeric speed value '{raw_speed}' for edge '{internal_edge_id}'.")

        if speed_kph < 0:
            logger.warning(f"Rejected invalid negative traffic speed {speed_kph} kph on edge {internal_edge_id}")
            raise ValidationException(f"Traffic speed must be non-negative. Got {speed_kph} kph.")

        congestion_factor = float(raw_data.get("congestion_factor", 1.0))
        if congestion_factor < 0:
            congestion_factor = 1.0

        jam_length = float(raw_data.get("jam_length_meters", 0.0))
        if jam_length < 0:
            jam_length = 0.0

        return TrafficStateCreate(
            internal_edge_id=str(internal_edge_id),
            current_speed_kph=speed_kph,
            congestion_factor=congestion_factor,
            jam_length_meters=jam_length
        )
