import json
from backend.app.main import health_check


def test_healthz_endpoint():
    response = health_check()
    assert response.status_code == 200
    data = json.loads(response.body.decode("utf-8"))
    assert data["status"] == "ok"
    assert data["database"] == "connected"
