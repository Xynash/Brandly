import uuid

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import engine
from app.services.compliance import ScanResult
from app.services.generation import GenerationResult
from app.services.history import save_generation

BODY = "Write a {{platform}} post about {{product}}. Facts: {{facts}}."
VALUES = {"platform": "Instagram", "product": "the Monsoon Hoodie", "facts": "Rs 1499"}


def generate(api, headers, cid, **payload):
    payload = payload or {"task": "Write a post"}
    return api.post(f"/clients/{cid}/generate", json=payload, headers=headers)


def listing(api, headers, query=""):
    r = api.get(f"/generations{query}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_generation_is_saved_and_returned_with_its_id(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    r = generate(api, agency, cid, task="Write a post")
    assert r.status_code == 200
    gen_id = r.json()["id"]
    assert gen_id
    saved = api.get(f"/generations/{gen_id}", headers=agency).json()
    assert saved["task"] == "Write a post"
    assert saved["output"] == "A calm, clear draft."
    assert saved["client_id"] == cid
    assert saved["passed"] is True and saved["flagged"] is False
    assert saved["attempts"] == 1 and saved["score"] == 100 and saved["violations"] == []


def test_a_flagged_generation_keeps_its_violations_and_is_filterable(api, agency, make_client, put_hub, fake_llm):
    cid = make_client(agency)
    put_hub(cid, agency, [{"word": "slay"}])
    fake_llm.replies = ["slay one", "slay two"]
    flagged_id = generate(api, agency, cid).json()["id"]
    fake_llm.replies = ["A calm, clear draft."]
    clean_id = generate(api, agency, cid).json()["id"]

    assert [g["id"] for g in listing(api, agency, "?flagged=true")] == [flagged_id]
    assert [g["id"] for g in listing(api, agency, "?flagged=false")] == [clean_id]
    saved = api.get(f"/generations/{flagged_id}", headers=agency).json()
    assert saved["flagged"] is True and saved["passed"] is False and saved["attempts"] == 2
    assert [v["word"] for v in saved["violations"]] == ["slay"]


def test_template_generations_store_the_filled_in_task(api, agency, make_client, fake_llm):
    cid = make_client(agency)
    tid = api.post("/templates", json={"name": "Announcement", "body": BODY}, headers=agency).json()["id"]
    gen_id = generate(api, agency, cid, template_id=tid, values=VALUES).json()["id"]
    saved = api.get(f"/generations/{gen_id}", headers=agency).json()
    assert saved["task"] == "Write a Instagram post about the Monsoon Hoodie. Facts: Rs 1499."
    assert saved["template_id"] == tid


def test_history_is_private_to_each_agency(api, agency, other_agency, make_client, fake_llm):
    cid = make_client(agency)
    gen_id = generate(api, agency, cid).json()["id"]
    assert listing(api, other_agency) == []
    assert api.get(f"/generations/{gen_id}", headers=other_agency).status_code == 404
    assert api.get(f"/generations/{uuid.uuid4()}", headers=agency).status_code == 404


def test_list_is_newest_first_filterable_by_client_and_paginated(api, agency, make_client, fake_llm):
    a = make_client(agency, "FinBank")
    b = make_client(agency, "ZestWear", "d2c")
    first = generate(api, agency, a, task="first").json()["id"]
    second = generate(api, agency, a, task="second").json()["id"]
    third = generate(api, agency, b, task="third").json()["id"]

    assert [g["id"] for g in listing(api, agency)] == [third, second, first]
    assert [g["id"] for g in listing(api, agency, f"?client_id={a}")] == [second, first]
    assert [g["id"] for g in listing(api, agency, "?limit=2")] == [third, second]
    assert [g["id"] for g in listing(api, agency, "?limit=2&offset=2")] == [first]
    assert api.get("/generations?limit=0", headers=agency).status_code == 422
    assert api.get("/generations?limit=101", headers=agency).status_code == 422


def test_failed_model_calls_are_not_saved(api, agency, make_client, fake_llm):
    from app.services.llm import LLMError

    cid = make_client(agency)
    fake_llm.error = LLMError("boom")
    assert generate(api, agency, cid).status_code == 502
    assert listing(api, agency) == []


def test_deleting_a_client_removes_its_history_but_deleting_a_template_keeps_it(api, agency, make_client, fake_llm):
    a = make_client(agency, "FinBank")
    b = make_client(agency, "ZestWear", "d2c")
    tid = api.post("/templates", json={"name": "Announcement", "body": BODY}, headers=agency).json()["id"]
    keep = generate(api, agency, a, template_id=tid, values=VALUES).json()["id"]
    generate(api, agency, b, task="other client")

    assert api.delete(f"/templates/{tid}", headers=agency).status_code == 204
    assert api.get(f"/generations/{keep}", headers=agency).json()["template_id"] is None

    assert api.delete(f"/clients/{b}", headers=agency).status_code == 204
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from generations")).scalar() == 1


class FailingDB:
    def __init__(self):
        self.rolled_back = False

    def add(self, obj):
        pass

    def commit(self):
        raise SQLAlchemyError("boom")

    def rollback(self):
        self.rolled_back = True


def test_a_failed_save_never_raises_and_rolls_back():
    result = GenerationResult(text="A draft", scan=ScanResult(True, 100, []), attempts=1, flagged=False)
    db = FailingDB()
    saved = save_generation(
        db, agency_id=uuid.uuid4(), client_id=uuid.uuid4(), template_id=None, task="t", result=result
    )
    assert saved is None
    assert db.rolled_back is True
