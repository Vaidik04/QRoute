import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.traffic import TrafficState
from backend.app.models.incident import Incident, IncidentEdge
from backend.app.models.simulation import SimulationRun
from backend.app.models.optimization import OptimizationRun

logger = logging.getLogger("qtransit")

class DemoService:
    def reset_demo(self, db: Session) -> Dict[str, Any]:
        """Reset temporary presentation simulation state, incidents, and restore clean Bhopal state."""
        logger.info("DemoService: Initiating Demo State Reset for presentation...")

        # Clear temporary simulation runs & incidents
        db.query(SimulationRun).delete()
        db.query(IncidentEdge).delete()
        db.query(Incident).delete()
        db.commit()

        return {
            "status": "SUCCESS",
            "message": "Demo environment reset cleanly to initial Bhopal state.",
            "available_scenarios": [
                "DEMO_01_BASIC_TRIP",
                "DEMO_02_DELIVERY",
                "DEMO_03_ROAD_CLOSURE",
                "DEMO_04_DYNAMIC_REROUTE"
            ]
        }

    def get_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "DEMO_01_BASIC_TRIP",
                "name": "Single Point-to-Point Trip",
                "description": "Hamidia Hospital to New Market via Board Office Square."
            },
            {
                "id": "DEMO_02_DELIVERY",
                "name": "Quantum Multi-Vehicle Delivery VRP",
                "description": "Adaptive D-QPSO optimization across 5 Bhopal customer nodes with 2 delivery vans."
            },
            {
                "id": "DEMO_03_ROAD_CLOSURE",
                "name": "Arterial Road Closure Incident",
                "description": "Simulate peak hour accident on MP Nagar Zone 1 arterial road."
            },
            {
                "id": "DEMO_04_DYNAMIC_REROUTE",
                "name": "Live Dynamic Feedback Rerouting",
                "description": "End-to-end feedback loop: Traffic incident -> QPSO re-optimization -> SUMO reroute -> WebSocket broadcast."
            }
        ]

demo_service = DemoService()
