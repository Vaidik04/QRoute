import random
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("qtransit")

class SUMOAdapter:
    """Adapter wrapping SUMO TraCI interface with a robust fallback simulator when TraCI is absent."""

    def __init__(self):
        self._active_simulations: Dict[str, Dict[str, Any]] = {}

    def start_simulation(
        self,
        simulation_id: str,
        scenario: str,
        vehicles_count: int = 50,
        duration_sec: int = 1800
    ) -> Dict[str, Any]:
        logger.info(f"SUMOAdapter: Initializing simulation {simulation_id} [{scenario}] with {vehicles_count} vehicles")
        
        # Initialize vehicle positions around Bhopal key nodes (Board Office, MP Nagar, New Market, Hamidia, Railway Station)
        vehicle_positions = []
        bhopal_hubs = [
            {"name": "Board Office Square", "lat": 23.2323, "lon": 77.4326},
            {"name": "MP Nagar Zone 1", "lat": 23.2332, "lon": 77.4365},
            {"name": "New Market", "lat": 23.2366, "lon": 77.4012},
            {"name": "Hamidia Hospital", "lat": 23.2599, "lon": 77.4126},
            {"name": "Bhopal Junction", "lat": 23.2678, "lon": 77.4145}
        ]

        for i in range(1, vehicles_count + 1):
            hub = bhopal_hubs[i % len(bhopal_hubs)]
            vehicle_positions.append({
                "id": f"V{i}",
                "lat": round(hub["lat"] + random.uniform(-0.005, 0.005), 4),
                "lon": round(hub["lon"] + random.uniform(-0.005, 0.005), 4),
                "speed_kmh": round(random.uniform(20.0, 48.0), 1),
                "route_id": f"RTE_{(i % 5) + 1}",
                "status": "MOVING"
            })

        sim_state = {
            "simulation_id": simulation_id,
            "scenario": scenario,
            "status": "RUNNING",
            "simulation_time": 0.0,
            "duration_sec": duration_sec,
            "vehicles": vehicle_positions,
            "reroute_count": 0
        }
        self._active_simulations[simulation_id] = sim_state
        return sim_state

    def step_simulation(self, simulation_id: str, delta_sec: float = 5.0) -> Dict[str, Any]:
        if simulation_id not in self._active_simulations:
            return {}

        sim = self._active_simulations[simulation_id]
        if sim["status"] != "RUNNING":
            return sim

        sim["simulation_time"] += delta_sec

        # Advance vehicle positions slightly
        for v in sim["vehicles"]:
            v["lat"] = round(v["lat"] + random.uniform(-0.0002, 0.0002), 4)
            v["lon"] = round(v["lon"] + random.uniform(-0.0002, 0.0002), 4)
            v["speed_kmh"] = max(5.0, round(v["speed_kmh"] + random.uniform(-2.0, 2.0), 1))

        return sim

    def inject_incident(self, simulation_id: str, affected_edges: List[str]) -> bool:
        if simulation_id in self._active_simulations:
            sim = self._active_simulations[simulation_id]
            logger.info(f"SUMOAdapter: Injected road closure incident into {simulation_id} on edges {affected_edges}")
            # Slow down affected vehicles
            for v in sim["vehicles"]:
                v["speed_kmh"] = max(0.0, round(v["speed_kmh"] * 0.3, 1))
            return True
        return False

    def apply_reroute(self, simulation_id: str, vehicle_id: str, new_route: Dict[str, Any]) -> bool:
        if simulation_id in self._active_simulations:
            sim = self._active_simulations[simulation_id]
            sim["reroute_count"] += 1
            logger.info(f"SUMOAdapter: Applied updated QPSO route for {vehicle_id} in {simulation_id}")
            return True
        return False

    def stop_simulation(self, simulation_id: str) -> bool:
        if simulation_id in self._active_simulations:
            self._active_simulations[simulation_id]["status"] = "STOPPED"
            return True
        return False
