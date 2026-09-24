def test_start_simulation(client):
    payload = {
        "scenario": "evening_peak_closure",
        "duration_sec": 1800,
        "vehicles": 50,
        "routing_algorithm": "adaptive_d_qpso"
    }
    response = client.post("/api/v1/simulation/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert data["status"] == "STARTED"

    sim_id = data["simulation_id"]
    state_resp = client.get(f"/api/v1/simulation/{sim_id}")
    assert state_resp.status_code == 200
    st = state_resp.json()
    assert st["simulation_id"] == sim_id
    assert len(st["vehicles"]) > 0
