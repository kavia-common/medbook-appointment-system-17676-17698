from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_patient_registration_and_login():
    payload = {
        "email": "testpat@example.com",
        "full_name": "Test Patient",
        "password": "strongpass",
        "user_type": "patient",
        "is_active": True
    }
    resp = client.post("/auth/register/patient", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == payload["email"]

    # login
    resp = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data

def test_doctor_registration_and_login():
    payload = {
        "email": "testdoc@example.com",
        "full_name": "Test Doctor",
        "password": "strongpass",
        "user_type": "doctor",
        "is_active": True
    }
    resp = client.post("/auth/register/doctor", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == payload["email"]

    # login
    resp = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data

def test_login_invalid():
    resp = client.post("/auth/login", json={"email": "wrong@example.com", "password": "abc"})
    assert resp.status_code == 401

def test_register_existing_user():
    payload = {
        "email": "exists@example.com",
        "full_name": "Exists User",
        "password": "strongpass",
        "user_type": "patient",
        "is_active": True
    }
    # First register succeeds
    resp = client.post("/auth/register/patient", json=payload)
    assert resp.status_code == 200
    # Register again should fail
    resp = client.post("/auth/register/patient", json=payload)
    assert resp.status_code == 400
