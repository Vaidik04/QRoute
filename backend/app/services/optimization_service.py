import json
import time
from sqlalchemy.orm import Session
from typing import List, Optional
from app.repositories.optimization import OptimizationRepository
from app.repositories.fleet import VehicleRepository, DeliveryRepository, CustomerRepository
from app.repositories.network import NetworkRepository
from app.adapters.optimization_adapter import OptimizationAdapter
from app.schemas.optimization import OptimizationRunResponse, OptimizationDeliveryRequest
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import logger

class OptimizationService:
    def __init__(self, db: Session):
        self.db = db
        self.opt_repo = OptimizationRepository(db)
        self.veh_repo = VehicleRepository(db)
        self.deliv_repo = DeliveryRepository(db)
        self.cust_repo = CustomerRepository(db)
        self.net_repo = NetworkRepository(db)
        self.adapter = OptimizationAdapter()

    def create_run(self, req: OptimizationDeliveryRequest) -> OptimizationRunResponse:
        # Load vehicles and deliveries
        vehicles = [self.veh_repo.get_by_id(vid) for vid in req.vehicle_ids if self.veh_repo.get_by_id(vid)]
        deliveries = [self.deliv_repo.get_by_id(did) for did in req.delivery_ids if self.deliv_repo.get_by_id(did)]
        
        if not vehicles:
            raise ValidationException("At least one valid vehicle ID must be provided.")
        if not deliveries:
            raise ValidationException("At least one valid delivery ID must be provided.")

        customers = [d.customer for d in deliveries if d.customer]
        nodes = self.net_repo.list_nodes()
        edges = self.net_repo.list_edges()

        # Create QUEUED run
        run = self.opt_repo.create_run(algorithm_name=req.algorithm or "D-QPSO")
        
        # Execute optimization (in-memory execution)
        start_time = time.time()
        self.opt_repo.update_status(run.id, "RUNNING")
        
        problem = self.adapter.build_problem(run.id, vehicles, customers, edges)
        result, mapped_routes = self.adapter.solve_and_map_geometry(problem, nodes, edges)
        
        elapsed_ms = (time.time() - start_time) * 1000.0

        # Store convergence per iteration in optimization_iterations
        for it in result.iterations:
            self.opt_repo.add_iteration(
                run_id=run.id,
                iteration_number=it["iteration"],
                best_cost=it["best_cost"],
                average_cost=it.get("avg_cost")
            )

        # Store solutions and road geometry
        for vehicle_id, route_info in mapped_routes.items():
            self.opt_repo.add_solution(
                run_id=run.id,
                vehicle_id=vehicle_id,
                sequence_json=json.dumps(route_info["sequence"]),
                total_cost=result.total_cost,
                total_distance=result.total_distance
            )

        # Set metrics
        self.opt_repo.set_metrics(
            run_id=run.id,
            runtime_ms=elapsed_ms,
            total_distance=result.total_distance,
            fleet_utilization=round(len(vehicles) / max(1, len(vehicles)), 2)
        )

        self.opt_repo.update_status(run.id, "COMPLETED", finished=True)
        return OptimizationRunResponse.model_validate(self.opt_repo.get_run(run.id))

    def get_run(self, run_id: str) -> OptimizationRunResponse:
        run = self.opt_repo.get_run(run_id)
        if not run:
            raise ResourceNotFoundException("OptimizationRun", run_id)
        return OptimizationRunResponse.model_validate(run)
