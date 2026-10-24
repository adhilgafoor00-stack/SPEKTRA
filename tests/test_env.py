import os

from core import llm
from core.envfile import load_env


def test_keys_are_cleaned(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", '  "gsk_abc123"  \n')
    assert llm._env("GROQ_API_KEY") == "gsk_abc123"
    monkeypatch.setenv("GROQ_API_KEY", "Bearer gsk_abc123")
    assert llm._env("GROQ_API_KEY") == "gsk_abc123"
    monkeypatch.setenv("GROQ_API_KEY", "'gsk_abc123'")
    assert llm._env("GROQ_API_KEY") == "gsk_abc123"


def test_quoted_key_is_sent_clean(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "groq")
    monkeypatch.setenv("GROQ_API_KEY", '"gsk_abc123" ')
    seen = {}

    class R:
        status_code = 200
        ok = True

        def json(self):
            return {"choices": [{"message": {"content": "hey"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["auth"] = headers["Authorization"]
        return R()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    assert llm.chat([{"role": "user", "content": "hi"}]) == "hey"
    assert seen["auth"] == "Bearer gsk_abc123"


def test_dotenv_loader(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("# comment\nGROQ_API_KEY=gsk_from_file\nexport SPEKTRA_LLM=\"groq\"\nEMPTY\n")
    monkeypatch.delenv("SPEKTRA_LLM", raising=False)
    assert load_env(str(f)) == 2
    assert os.environ["GROQ_API_KEY"] == "gsk_from_file"
    assert os.environ["SPEKTRA_LLM"] == "groq"
    monkeypatch.setenv("GROQ_API_KEY", "already-set")
    load_env(str(f))
    assert os.environ["GROQ_API_KEY"] == "already-set"  # real env wins
    for k in ("GROQ_API_KEY", "SPEKTRA_LLM"):
        os.environ.pop(k, None)
