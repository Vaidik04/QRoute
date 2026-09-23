from fastapi.testclient import TestClient

def test_demo_seed_and_analytics(client: TestClient):
    # Seed
    seed_resp = client.post("/api/v1/demo/seed")
    assert seed_resp.status_code == 201
    assert seed_resp.json()["status"] == "DEMO_DATA_SEEDED"

    # Analytics endpoints
    opt_an = client.get("/api/v1/analytics/optimization")
    assert opt_an.status_code == 200

    traf_an = client.get("/api/v1/analytics/traffic")
    assert traf_an.status_code == 200

    bench_resp = client.get("/api/v1/analytics/benchmark")
    assert bench_resp.status_code == 200
    assert len(bench_resp.json()) > 0

    # Comparison endpoint with real computed metrics (not hardcoded percentages)
    comp_resp = client.get("/api/v1/analytics/comparison?baseline=run_01&optimized=run_02")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert "total_travel_distance_meters" in comp_data
    assert "improvement_percentage" in comp_data["total_travel_distance_meters"]
