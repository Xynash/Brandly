def test_health_reports_database_connected(api):
    r = api.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "connected"}
