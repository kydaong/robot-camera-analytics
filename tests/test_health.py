"""Basic health and root endpoint tests."""


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Robot Camera Analytics" in r.json()["message"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
