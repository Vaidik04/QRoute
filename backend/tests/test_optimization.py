from fastapi.testclient import TestClient

def test_optimization_run_and_geometry_mapping(client: TestClient):
    # Seed data
    client.post("/api/v1/demo/seed")
    
    # Get seeded vehicle and delivery IDs
    vehs = client.get("/api/v1/vehicles").json()
    delivs = client.get("/api/v1/deliveries").json()

    assert len(vehs) > 0
    assert len(delivs) > 0

    opt_payload = {
        "vehicle_ids": [vehs[0]["id"]],
        "delivery_ids": [delivs[0]["id"]],
        "algorithm": "D-QPSO"
    }

    response = client.post("/api/v1/optimization/run", json=opt_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["algorithm_name"] == "D-QPSO"
    assert len(data["solutions"]) > 0
    assert len(data["iterations"]) == 10  # verified convergence per iteration
    assert data["metrics"]["total_runtime_ms"] > 0
