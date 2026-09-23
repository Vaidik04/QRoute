def test_benchmarks_endpoints(client):
    res_create = client.post("/api/v1/benchmarks/run", json={})
    assert res_create.status_code == 201
    data = res_create.json()
    assert "id" in data
    assert len(data["results"]) == 2

    bm_id = data["id"]
    res_get = client.get(f"/api/v1/benchmarks/{bm_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == bm_id

    res_list = client.get("/api/v1/benchmarks")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

def test_transit_endpoints(client):
    res_stops = client.get("/api/v1/transit/stops")
    assert res_stops.status_code == 200
    assert len(res_stops.json()) > 0

    res_routes = client.get("/api/v1/transit/routes")
    assert res_routes.status_code == 200
    assert len(res_routes.json()) > 0

def test_ev_endpoints(client):
    res_chargers = client.get("/api/v1/ev/charging-stations")
    assert res_chargers.status_code == 200
    assert len(res_chargers.json()) > 0

    res_route = client.post("/api/v1/ev/route", json={"origin": "A", "destination": "B"})
    assert res_route.status_code == 200
    assert res_route.json()["mode"] == "ev"

    res_veh = client.get("/api/v1/ev/vehicle/V_EV_1")
    assert res_veh.status_code == 200
    assert res_veh.json()["vehicle_id"] == "V_EV_1"
