from fastapi.testclient import TestClient

from app.main import app


def test_cors_preflight_allows_frontend_origin():
    """浏览器从 localhost:3000 POST 到 localhost:8000 会先发 OPTIONS 预检。"""
    client = TestClient(app)
    r = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "POST" in r.headers.get("access-control-allow-methods", "")


def test_cors_actual_request_carries_allow_origin():
    client = TestClient(app)
    r = client.get("/healthz", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
