BODY = "Write a {{platform}} post about {{product}}. Facts: {{facts}}."


def make_template(api, headers, name="Announcement", body=BODY, client_id=None):
    payload = {"name": name, "body": body}
    if client_id:
        payload["client_id"] = client_id
    return api.post("/templates", json=payload, headers=headers)


def test_create_returns_variables_and_rejects_duplicate_names(api, agency):
    r = make_template(api, agency)
    assert r.status_code == 201
    assert r.json()["variables"] == ["platform", "product", "facts"]
    assert make_template(api, agency).status_code == 409


def test_template_cannot_be_attached_to_another_agencys_client(api, agency, other_agency, make_client):
    cid = make_client(agency)
    assert make_template(api, other_agency, client_id=cid).status_code == 404


def test_list_filters_by_client(api, agency, make_client):
    a = make_client(agency, "FinBank")
    b = make_client(agency, "ZestWear", "d2c")
    make_template(api, agency, name="Agency wide")
    make_template(api, agency, name="Only A", client_id=a)
    make_template(api, agency, name="Only B", client_id=b)
    for_a = {t["name"] for t in api.get(f"/templates?client_id={a}", headers=agency).json()}
    assert for_a == {"Agency wide", "Only A"}
    everything = {t["name"] for t in api.get("/templates", headers=agency).json()}
    assert everything == {"Agency wide", "Only A", "Only B"}


def test_delete_and_cross_agency_isolation(api, agency, other_agency):
    tid = make_template(api, agency).json()["id"]
    assert api.get("/templates", headers=other_agency).json() == []
    assert api.delete(f"/templates/{tid}", headers=other_agency).status_code == 404
    assert api.delete(f"/templates/{tid}", headers=agency).status_code == 204
    assert api.get("/templates", headers=agency).json() == []
