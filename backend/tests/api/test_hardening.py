from app.core.config import settings
from app.core.db import engine


def generate(api, headers, cid):
    return api.post(f"/clients/{cid}/generate", json={"task": "Write a post"}, headers=headers)


def test_database_connection_is_released_before_the_model_call(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    seen = []
    fake_llm.on_call = lambda: seen.append(engine.pool.checkedout())
    assert generate(api, agency, cid).status_code == 200
    assert seen == [0]  # zero connections held while waiting for the model


def test_generate_is_rate_limited_per_agency(api, agency, other_agency, make_client, fake_llm, monkeypatch):
    monkeypatch.setattr(settings, "generate_rate_limit_per_minute", 2)
    a = make_client(agency)
    b = make_client(other_agency)
    assert generate(api, agency, a).status_code == 200
    assert generate(api, agency, a).status_code == 200
    blocked = generate(api, agency, a)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert len(fake_llm.calls) == 2  # the blocked request never reached the model
    assert generate(api, other_agency, b).status_code == 200  # other agencies are unaffected
