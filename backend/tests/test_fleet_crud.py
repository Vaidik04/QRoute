from fastapi.testclient import TestClient

def test_vehicles_crud(client: TestClient):
    # 1. Create Vehicle
    payload = {
        "plate_number": "MP04-TEST-9999",
        "vehicle_type": "electric_van",
        "capacity_weight": 1500.0,
        "capacity_volume": 15.0,
        "current_lat": 23.25,
        "current_lng": 77.41,
        "status": "IDLE"
    }
    response = client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == 201
    veh_data = response.json()
    veh_id = veh_data["id"]
    assert veh_data["plate_number"] == "MP04-TEST-9999"

    # 2. List Vehicles
    list_resp = client.get("/api/v1/vehicles")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Get Vehicle by ID
    get_resp = client.get(f"/api/v1/vehicles/{veh_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == veh_id

    # 4. Update Vehicle
    up_resp = client.put(f"/api/v1/vehicles/{veh_id}", json={"status": "IN_TRANSIT"})
    assert up_resp.status_code == 200
    assert up_resp.json()["status"] == "IN_TRANSIT"

    # 5. Delete Vehicle
    del_resp = client.delete(f"/api/v1/vehicles/{veh_id}")
    assert del_resp.status_code == 204

    # 6. Verify 404 Coded Error Format
    get_404 = client.get(f"/api/v1/vehicles/{veh_id}")
    assert get_404.status_code == 404
    err_json = get_404.json()
    assert "error" in err_json
    assert err_json["error"]["code"] == "RESOURCE_NOT_FOUND"

def test_customers_and_deliveries_crud(client: TestClient):
    # Create Customer
    c_resp = client.post("/api/v1/customers", json={
        "name": "Bhopal Test Depot",
        "address": "Arera Colony",
        "lat": 23.21,
        "lng": 77.44,
        "time_window_start": "09:00",
        "time_window_end": "17:00"
    })
    assert c_resp.status_code == 201
    cust_id = c_resp.json()["id"]

    # Create Delivery
    d_resp = client.post("/api/v1/deliveries", json={
        "customer_id": cust_id,
        "package_weight": 25.0,
        "package_volume": 0.3,
        "priority": 1,
        "status": "PENDING"
    })
    assert d_resp.status_code == 201
    deliv_id = d_resp.json()["id"]
    assert d_resp.json()["customer_id"] == cust_id
