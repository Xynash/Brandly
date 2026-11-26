import logging


def test_every_response_has_a_request_id(api):
    assert len(api.get("/health").headers["X-Request-ID"]) >= 8


def test_a_valid_incoming_request_id_is_echoed(api):
    r = api.get("/health", headers={"X-Request-ID": "abc-123_XYZ"})
    assert r.headers["X-Request-ID"] == "abc-123_XYZ"


def test_a_malformed_request_id_is_replaced(api):
    r = api.get("/health", headers={"X-Request-ID": "bad id with spaces!"})
    assert r.headers["X-Request-ID"] != "bad id with spaces!"


def test_cors_preflight_allows_the_frontend_origin(api):
    r = api.options(
        "/clients",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-agency-id,content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "x-agency-id" in r.headers["access-control-allow-headers"].lower()


def test_cors_does_not_allow_unknown_origins(api):
    r = api.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_exposes_request_id_and_retry_after_to_the_browser(api):
    r = api.get("/health", headers={"Origin": "http://localhost:3000"})
    exposed = r.headers["access-control-expose-headers"].lower()
    assert "x-request-id" in exposed and "retry-after" in exposed


def test_unexpected_crash_returns_clean_json_with_a_request_id(api, agency, make_client, monkeypatch):
    cid = make_client(agency)

    def boom(*args, **kwargs):
        raise RuntimeError("secret internals")

    monkeypatch.setattr("app.routers.generate.build_context", boom)
    r = api.post(f"/clients/{cid}/generate", json={"task": "x"}, headers=agency)
    assert r.status_code == 500
    body = r.json()
    assert body["detail"] == "Internal server error"
    assert body["request_id"] == r.headers["X-Request-ID"]
    assert "secret internals" not in r.text


def test_requests_are_logged_without_secrets(api, caplog):
    with caplog.at_level(logging.INFO, logger="brandly"):
        api.get("/health", headers={"X-Agency-Id": "super-secret"})
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "GET /health -> 200" in logged and "request_id=" in logged
    assert "super-secret" not in logged
