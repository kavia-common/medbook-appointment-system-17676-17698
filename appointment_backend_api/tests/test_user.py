import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_own_user_info_requires_auth():
    resp = client.get("/user/me")
    assert resp.status_code == 401

def test_profile_edit_and_fetch():
    # Register and login, edit profile, fetch, check.
    pass
