import os
from pathlib import Path

# Must happen BEFORE anything imports the app, so it never touches your dev database.
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://brandly:brandly@127.0.0.1:5433/brandly_test"
)
os.environ["DATABASE_URL"] = TEST_URL
os.environ["LLM_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def _postgres_reachable():
    """Stop the whole run once, with a clear message, if the test server cannot be reached."""
    url = make_url(TEST_URL)
    try:
        with psycopg.connect(
            host=url.host, port=url.port, user=url.username, password=url.password,
            dbname="postgres", connect_timeout=5,
        ):
            pass
    except psycopg.Error as exc:
        pytest.exit(
            f"Cannot reach Postgres at {url.host}:{url.port} ({type(exc).__name__}). "
            "Is Docker running? Try: docker compose up -d   then   docker restart brandly-db",
            returncode=2,
        )


@pytest.fixture(scope="session", autouse=True)
def _database(_postgres_reachable):
    """Create the test database if needed and bring it to the latest migration."""
    from app.core.config import settings

    url = make_url(settings.database_url)
    assert url.database and url.database.endswith("_test"), (
        f"Refusing to run: '{url.database}' is not a test database"
    )
    with psycopg.connect(
        host=url.host, port=url.port, user=url.username, password=url.password,
        dbname="postgres", autocommit=True,
    ) as conn:
        exists = conn.execute("select 1 from pg_database where datname = %s", (url.database,)).fetchone()
        if not exists:
            conn.execute(f'create database "{url.database}"')

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")  # also proves the migrations work from scratch
    yield


@pytest.fixture(autouse=True)
def _clean(_database):
    """Every test starts from empty tables."""
    from app.core.db import engine

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE agencies CASCADE"))


@pytest.fixture
def api():
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def make_agency(api):
    def _make(name="Agency A"):
        r = api.post("/agencies", json={"name": name})
        assert r.status_code == 201, r.text
        return {"X-Agency-Id": r.json()["id"]}

    return _make


@pytest.fixture
def agency(make_agency):
    return make_agency("Agency A")


@pytest.fixture
def other_agency(make_agency):
    return make_agency("Agency B")


@pytest.fixture
def make_client(api):
    def _make(headers, name="FinBank", industry="fintech"):
        r = api.post("/clients", json={"name": name, "industry": industry}, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _make


@pytest.fixture
def put_hub(api):
    def _put(cid, headers, words=(), **fields):
        body = {"tone_description": "Formal", "banned_words": list(words), **fields}
        r = api.put(f"/clients/{cid}/hub", json=body, headers=headers)
        assert r.status_code == 200, r.text
        return r.json()

    return _put


class FakeProvider:
    """Stands in for Gemini. Returns scripted replies; the last reply repeats."""

    name = "fake"

    def __init__(self):
        self.replies = ["A calm, clear draft."]
        self.calls = []
        self.error = None

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


@pytest.fixture
def fake_llm(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.routers.generate.get_provider", lambda: provider)
    return provider
