def post(client, text, **kw):
    return client.post("/api/handle", json={"text": text}, **kw)


def test_help_works(client):
    r = post(client, "help")
    assert r.status_code == 200 and r.get_json()["ok"]


def test_rejects_non_json(client):
    r = client.post("/api/handle", data='{"text":"help"}', content_type="text/plain")
    assert r.status_code == 415


def test_rejects_cross_site_origin(client):
    r = post(client, "help", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_rejects_foreign_host(client):
    r = post(client, "help", base_url="http://evil.example")
    assert r.status_code == 403


def test_allows_local_origin(client):
    r = post(client, "help", headers={"Origin": "http://127.0.0.1:5000"})
    assert r.status_code == 200


def test_empty_and_oversized_input(client):
    assert client.post("/api/handle", json={"text": "  "}).get_json()["ok"] is False
    assert post(client, "x" * 5000).status_code == 413


def test_widgets_include_hardware(client, monkeypatch):
    monkeypatch.setattr("core.widgets.net_status", lambda: {"online": False, "latency_ms": None, "ip": "x"})
    j = client.get("/api/widgets").get_json()
    assert j["ok"] and j["data"]["hardware"]["mode"] == "sim"
