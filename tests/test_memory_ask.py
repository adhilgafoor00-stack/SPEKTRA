from core import llm


def test_teach_and_facts(assistant):
    assert assistant.handle("teach python: readable language") == "learned: python"
    assert "python" in assistant.handle("facts")


def test_ask_uses_learned_facts_offline(assistant, monkeypatch):
    monkeypatch.setattr("core.tools.wiki_summary", lambda *a, **k: "wikipedia error: offline")
    assistant.handle("teach recursion: a function that calls itself")
    out = assistant.handle("ask what is recursion")
    assert "(learned)" in out and "calls itself" in out


def test_ask_prefers_llm_and_passes_facts(assistant, monkeypatch):
    seen = {}

    def fake_generate(q, facts=None, history=None):
        seen["facts"] = facts
        return "LLM says hi"

    monkeypatch.setattr(llm, "generate", fake_generate)
    assistant.handle("teach flask: a python web framework")
    assert assistant.handle("ask what is flask") == "LLM says hi"
    assert any("python web framework" in f for f in seen["facts"])


def test_ask_falls_back_when_llm_fails(assistant, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *a, **k: None)
    monkeypatch.setattr("core.tools.wiki_summary", lambda *a, **k: "wikipedia error: offline")
    assert "(base)" in assistant.handle("ask something unknown")


def test_log_is_capped(assistant):
    for i in range(assistant.memory.MAX_LOG + 20):
        assistant.memory.log_interaction(f"u{i}", "a")
    assert len(assistant.memory.data["log"]) == assistant.memory.MAX_LOG


def test_llm_backend_selection(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "auto")
    monkeypatch.setattr(llm, "_ollama_up", lambda: False)
    assert llm.pick_backend() == "none"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.pick_backend() == "anthropic"
