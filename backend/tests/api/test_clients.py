from sqlalchemy import text

from app.core.db import engine


def test_missing_or_unknown_agency_header(api):
    assert api.get("/clients").status_code == 422
    r = api.get("/clients", headers={"X-Agency-Id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


def test_create_list_and_duplicate_name(api, agency, make_client):
    cid = make_client(agency)
    assert [c["id"] for c in api.get("/clients", headers=agency).json()] == [cid]
    dup = api.post("/clients", json={"name": "FinBank"}, headers=agency)
    assert dup.status_code == 409


def test_new_client_starts_with_an_empty_hub(api, agency, make_client):
    cid = make_client(agency)
    hub = api.get(f"/clients/{cid}/hub", headers=agency).json()
    assert hub["tone_description"] == ""
    assert hub["banned_words"] == []


def test_same_client_name_is_allowed_in_different_agencies(agency, other_agency, make_client):
    make_client(agency)
    make_client(other_agency)


def test_agency_cannot_see_or_touch_another_agencys_client(api, agency, other_agency, make_client):
    cid = make_client(agency)
    assert api.get("/clients", headers=other_agency).json() == []
    assert api.get(f"/clients/{cid}/hub", headers=other_agency).status_code == 404
    r = api.put(f"/clients/{cid}/hub", json={"tone_description": "hacked"}, headers=other_agency)
    assert r.status_code == 404
    assert api.delete(f"/clients/{cid}", headers=other_agency).status_code == 404
    assert api.get(f"/clients/{cid}/hub", headers=agency).json()["tone_description"] == ""


def test_banned_words_are_synced_lowercased_and_deduped(agency, make_client, put_hub):
    cid = make_client(agency)
    hub = put_hub(cid, agency, [
        {"word": "Slay"}, {"word": "slay"}, {"word": "Guaranteed Returns", "severity": "warn"},
    ])
    assert {w["word"]: w["severity"] for w in hub["banned_words"]} == {
        "slay": "block", "guaranteed returns": "warn",
    }
    hub = put_hub(cid, agency, [{"word": "slay", "severity": "warn"}])
    assert {w["word"]: w["severity"] for w in hub["banned_words"]} == {"slay": "warn"}


def test_hub_limits_and_severity_are_validated(api, agency, make_client):
    cid = make_client(agency)
    url = f"/clients/{cid}/hub"
    assert api.put(url, json={"tone_description": "x" * 2001}, headers=agency).status_code == 422
    bad = {"banned_words": [{"word": "a", "severity": "nope"}]}
    assert api.put(url, json=bad, headers=agency).status_code == 422


def test_deleting_a_client_removes_its_hub_and_words(api, agency, make_client, put_hub):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}])
    assert api.delete(f"/clients/{cid}", headers=agency).status_code == 204
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from brand_hubs")).scalar() == 0
        assert conn.execute(text("select count(*) from banned_words")).scalar() == 0
