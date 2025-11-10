from fastapi.testclient import TestClient
from autoappbuilder.api.app import app

client = TestClient(app)

def test_catalog():
    r = client.get("/catalog")
    assert r.status_code == 200
    assert "items" in r.json()
