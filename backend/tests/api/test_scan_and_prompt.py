def test_scan_flags_banned_words(api, agency, make_client, put_hub):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}, {"word": "synergy", "severity": "warn"}])
    r = api.post(f"/clients/{cid}/scan", json={"text": "Real synergy, and we slay."}, headers=agency)
    body = r.json()
    assert r.status_code == 200
    assert body["passed"] is False
    assert body["score"] == 50
    assert {v["word"] for v in body["violations"]} == {"slay", "synergy"}


def test_scan_passes_clean_text(api, agency, make_client, put_hub):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}])
    r = api.post(f"/clients/{cid}/scan", json={"text": "Clear terms and no hidden fees."}, headers=agency)
    assert r.json()["passed"] is True
    assert r.json()["score"] == 100


def test_scan_is_blocked_across_agencies(api, agency, other_agency, make_client):
    cid = make_client(agency)
    r = api.post(f"/clients/{cid}/scan", json={"text": "hello"}, headers=other_agency)
    assert r.status_code == 404


def test_prompt_preview_contains_the_hub_rules(api, agency, make_client, put_hub):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}], tone_description="Formal and calm", audience="Salaried professionals")
    r = api.post(f"/clients/{cid}/prompt-preview", json={"task": "Write a post"}, headers=agency)
    assert r.status_code == 200
    assert "Formal and calm" in r.json()["system"]
    assert "- slay" in r.json()["system"]
    assert r.json()["user"] == "Write a post"


def test_prompts_never_mix_clients(api, agency, make_client, put_hub):
    a = make_client(agency, "FinBank", "fintech")
    b = make_client(agency, "ZestWear", "d2c apparel")
    put_hub(a, agency, [{"word": "guaranteed returns"}], tone_description="Formal")
    put_hub(b, agency, [{"word": "cheap"}], tone_description="Witty")

    def system(cid):
        r = api.post(f"/clients/{cid}/prompt-preview", json={"task": "Hi"}, headers=agency)
        return r.json()["system"]

    sa, sb = system(a), system(b)
    assert "Formal" in sa and "guaranteed returns" in sa
    assert "Witty" not in sa and "cheap" not in sa
    assert "Witty" in sb and "cheap" in sb
    assert "Formal" not in sb and "guaranteed returns" not in sb


def test_prompt_preview_is_blocked_across_agencies(api, agency, other_agency, make_client):
    cid = make_client(agency)
    r = api.post(f"/clients/{cid}/prompt-preview", json={"task": "Hi"}, headers=other_agency)
    assert r.status_code == 404
