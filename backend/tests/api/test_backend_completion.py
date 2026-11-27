import json
import uuid
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import User
from app.models.tenant import AuthSession, ProviderKey
from app.services.auth import hash_password, token_hash


def test_password_signup_login_and_logout(api, monkeypatch, fake_llm):
    monkeypatch.setattr(settings, "auth_mode", "password")
    password = "a long test passphrase"
    signup = dict(email="Admin@example.com", password=password, full_name="Admin", agency_name="Agency")
    rejected = api.post("/auth/signup", json={**signup, "password": "short-secret"})
    assert rejected.status_code == 422 and "short-secret" not in rejected.text
    created = api.post("/auth/signup", json=signup)
    assert created.status_code == 201, created.text
    assert created.headers["Cache-Control"] == "no-store"
    token = created.json()["access_token"]
    admin = {"Authorization": f"Bearer {token}"}
    agency = api.get("/agencies/current", headers=admin)
    assert agency.status_code == 200
    agency_id = uuid.UUID(agency.json()["id"])
    assert api.post("/auth/signup", json={**signup, "email": "ADMIN@example.com"}).status_code == 409
    assert api.get("/clients", headers={"X-Agency-Id": str(agency_id)}).status_code == 401
    assert api.get("/clients", headers={**admin, "X-Agency-Id": str(uuid.uuid4())}).status_code == 403

    with SessionLocal.begin() as db:
        session = db.get(AuthSession, token_hash(token))
        assert session.token_hash != token
        assert session.user.password_hash.startswith("scrypt-v1")
        assert password not in session.user.password_hash
        writer = User(
            agency_id=agency_id, email="writer@example.com", full_name="Writer",
            password_hash=hash_password(password),
        )
        db.add(writer)
        db.flush()
        writer_id = writer.id

    wrong = api.post("/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert wrong.status_code == 401
    logged_in = api.post("/auth/login", json={"email": "WRITER@example.com", "password": password})
    assert logged_in.status_code == 200, logged_in.text
    writer_headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
    assert api.post("/clients", headers=writer_headers, json={"name": "No"}).status_code == 403
    client = api.post("/clients", headers=admin, json={"name": "Yes"}).json()["id"]
    result = api.post(f"/clients/{client}/generate", headers=writer_headers, json={"task": "Draft"})
    assert result.status_code == 200, result.text
    history = api.get(f"/generations/{result.json()['id']}", headers=admin)
    assert history.json()["user_id"] == str(writer_id)
    assert api.post("/auth/logout", headers=admin).status_code == 204
    assert api.get("/clients", headers=admin).status_code == 401
    with SessionLocal.begin() as db:
        writer_token = logged_in.json()["access_token"]
        db.get(AuthSession, token_hash(writer_token)).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert api.get("/clients", headers=writer_headers).status_code == 401


def test_presets_and_checked_sse_share_the_same_rules(api, agency, make_client, put_hub, fake_llm):
    cid = make_client(agency)
    preset = "india-investment-advice-v1"
    assert any(item["id"] == preset for item in api.get("/presets", headers=agency).json())
    put_hub(cid, agency, preset_ids=[preset])
    put_hub(cid, agency, audience="Investors")
    result = api.post(f"/clients/{cid}/scan", headers=agency, json={"text": "We offer guaranteed returns."})
    assert result.json()["passed"] is False
    fake_llm.replies = ["We offer guaranteed returns."]
    blocked = api.post(f"/clients/{cid}/generate/stream", headers=agency, json={"task": "Draft"})
    assert blocked.status_code == 200
    assert blocked.headers["content-type"].startswith("text/event-stream")
    assert "event: review_required" in blocked.text
    assert "guaranteed returns" not in blocked.text
    assert len(fake_llm.calls) == 2
    fake_llm.replies = ["Review the investment terms."]
    clean = api.post(f"/clients/{cid}/generate/stream", headers=agency, json={"task": "Draft"})
    assert "event: completed" in clean.text
    assert "Review the investment terms." in clean.text


def test_import_hub_returns_an_unpersisted_draft(api, agency, make_client, fake_llm, monkeypatch):
    async def read_page(url):
        assert url == "https://example.com/"
        return "A website with enough real-sounding text for the importer."

    fake_llm.replies = [json.dumps({"tone_description": "Bright and clear"})]
    monkeypatch.setattr("app.routers.hub_import.read_page", read_page)
    monkeypatch.setattr("app.routers.hub_import.get_provider", lambda: fake_llm)
    cid = make_client(agency)
    response = api.post(f"/clients/{cid}/hub/import", headers=agency, json={"url": "https://example.com/"})
    assert response.status_code == 200, response.text
    assert response.json()["tone_description"] == "Bright and clear"
    assert api.get(f"/clients/{cid}/hub", headers=agency).json()["tone_description"] == ""


def test_provider_keys_are_encrypted_and_used_only_for_the_owner(
    api, agency, other_agency, make_client, fake_llm, monkeypatch,
):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    encryption_key = Fernet.generate_key()
    monkeypatch.setattr(settings, "provider_key_encryption_key", encryption_key.decode())
    route = "/agencies/current/provider-keys/gemini"
    key = "sample-provider-secret"
    invalid = api.put(route, headers=agency, json={"api_key": [key]})
    assert invalid.status_code == 422 and key not in invalid.text
    assert api.put(route, headers=agency, json={"api_key": key}).status_code == 204
    agency_id = uuid.UUID(agency["X-Agency-Id"])
    with SessionLocal() as db:
        stored = db.get(ProviderKey, (agency_id, "gemini"))
        assert key not in stored.encrypted_key
        assert Fernet(encryption_key).decrypt(stored.encrypted_key.encode()).decode() == key

    keys = []
    def provider(api_key=None):
        keys.append(api_key)
        return fake_llm
    monkeypatch.setattr("app.routers.generate.get_provider", provider)
    for headers in (agency, other_agency):
        client = make_client(headers)
        assert api.post(f"/clients/{client}/generate", headers=headers, json={"task": "Draft"}).status_code == 200
    assert keys == [key, None]
    assert api.delete(route, headers=agency).status_code == 204
