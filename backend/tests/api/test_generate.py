from app.services.llm import LLMError

BODY = "Write a {{platform}} post about {{product}}. Facts: {{facts}}."
VALUES = {"platform": "Instagram", "product": "the Monsoon Hoodie", "facts": "Rs 1499"}


def generate(api, headers, cid, **payload):
    return api.post(f"/clients/{cid}/generate", json=payload, headers=headers)


def make_template_id(api, headers, client_id=None):
    payload = {"name": "Announcement", "body": BODY}
    if client_id:
        payload["client_id"] = client_id
    r = api.post("/templates", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_generate_from_a_task(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    r = generate(api, agency, cid, task="Write a post")
    body = r.json()
    assert r.status_code == 200
    assert body["text"] == "A calm, clear draft."
    assert body["passed"] and not body["flagged"] and body["attempts"] == 1
    assert fake_llm.calls[0][1] == "Write a post"


def test_banned_word_triggers_one_stricter_retry(api, agency, make_client, put_hub, fake_llm):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}])
    fake_llm.replies = ["This will slay!", "A calm, clear draft."]
    body = generate(api, agency, cid, task="Write a post").json()
    assert body["attempts"] == 2 and not body["flagged"]
    assert body["text"] == "A calm, clear draft."
    assert '"slay"' in fake_llm.calls[1][0]


def test_still_failing_after_retry_is_flagged_not_an_error(api, agency, make_client, put_hub, fake_llm):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}])
    fake_llm.replies = ["slay one", "slay two"]
    r = generate(api, agency, cid, task="Write a post")
    assert r.status_code == 200
    assert r.json()["flagged"] is True and r.json()["passed"] is False
    assert r.json()["attempts"] == 2
    assert len(fake_llm.calls) == 2


def test_provider_failure_becomes_a_502(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    fake_llm.error = LLMError("boom")
    r = generate(api, agency, cid, task="Write a post")
    assert r.status_code == 502
    assert "boom" in r.json()["detail"]


def test_other_agency_cannot_generate_and_the_model_is_never_called(api, agency, other_agency, make_client, fake_llm):
    cid = make_client(agency)
    assert generate(api, other_agency, cid, task="Write a post").status_code == 404
    assert fake_llm.calls == []


def test_requires_exactly_one_of_task_or_template(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    assert generate(api, agency, cid).status_code == 422
    tid = make_template_id(api, agency)
    both = generate(api, agency, cid, task="x", template_id=tid, values=VALUES)
    assert both.status_code == 422
    assert fake_llm.calls == []


def test_generate_from_a_template_renders_the_values(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    tid = make_template_id(api, agency)
    r = generate(api, agency, cid, template_id=tid, values=VALUES)
    assert r.status_code == 200
    assert fake_llm.calls[0][1] == "Write a Instagram post about the Monsoon Hoodie. Facts: Rs 1499."


def test_missing_template_values_are_a_422_and_the_model_is_not_called(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    tid = make_template_id(api, agency)
    r = generate(api, agency, cid, template_id=tid, values={"platform": "Instagram"})
    assert r.status_code == 422
    assert "product" in r.json()["detail"] and "facts" in r.json()["detail"]
    assert fake_llm.calls == []


def test_template_scoped_to_another_client_is_not_found(api, agency, make_client, fake_llm):
    a = make_client(agency, "FinBank")
    b = make_client(agency, "ZestWear", "d2c")
    tid = make_template_id(api, agency, client_id=a)
    assert generate(api, agency, b, template_id=tid, values=VALUES).status_code == 404
    assert generate(api, agency, a, template_id=tid, values=VALUES).status_code == 200


def test_another_agencys_template_is_not_found(api, agency, other_agency, make_client, fake_llm):
    cid = make_client(agency)
    foreign = make_template_id(api, other_agency)
    assert generate(api, agency, cid, template_id=foreign, values=VALUES).status_code == 404
    assert fake_llm.calls == []
