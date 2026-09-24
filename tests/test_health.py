def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["service"] == "q-transit-backend"
    assert data["version"] == "1.0.0"
    assert "components" in data
