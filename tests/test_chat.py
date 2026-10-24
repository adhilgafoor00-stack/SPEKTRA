from core import llm


def fake_backend(monkeypatch, replies):
    """Pretend an LLM is configured and record what chat() receives."""
    calls = []

    def fake_chat(messages, facts=None):
        calls.append({"messages": [dict(m) for m in messages], "facts": facts})
        return replies[len(calls) - 1]

    monkeypatch.setattr(llm, "pick_backend", lambda: "anthropic")
    monkeypatch.setattr(llm, "chat", fake_chat)
    return calls


def test_plain_text_goes_to_chat(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["hey! what are you building?"])
    assert assistant.handle("hi there, I'm bored") == "hey! what are you building?"
    assert calls[0]["messages"] == [{"role": "user", "content": "hi there, I'm bored"}]


def test_history_carries_across_turns(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["first", "second"])
    assistant.handle("remember the number 7")
    assistant.handle("what number?")
    roles = [m["role"] for m in calls[1]["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert calls[1]["messages"][0]["content"] == "remember the number 7"


def test_reset_clears_history(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["a", "b"])
    assistant.handle("one")
    assert assistant.handle("reset") == "conversation cleared."
    assistant.handle("two")
    assert len(calls[1]["messages"]) == 1


def test_history_is_capped_and_starts_with_user(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["r"] * 40)
    for i in range(30):
        assistant.handle(f"msg {i}")
    assert len(assistant.history) <= assistant.MAX_HISTORY
    sent = calls[-1]["messages"]
    assert sent[0]["role"] == "user" and sent[-1]["role"] == "user"


def test_failed_call_does_not_corrupt_history(assistant, monkeypatch):
    monkeypatch.setattr(llm, "pick_backend", lambda: "anthropic")

    def boom(messages, facts=None):
        raise llm.LLMError("rate limited (429). Try again in a moment.")

    monkeypatch.setattr(llm, "chat", boom)
    assert "(chat error)" in assistant.handle("hello")
    assert assistant.history == []


def test_no_backend_gives_setup_help(assistant):
    out = assistant.handle("how are you?")
    assert "GROQ_API_KEY" in out and "GEMINI_API_KEY" in out and "Ollama" in out


def test_taught_facts_are_passed_as_context(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["ok"])
    assistant.handle("teach esp32: my favourite board")
    assistant.handle("what should I do with my esp32?")
    assert any("favourite board" in f for f in calls[0]["facts"])


def test_commands_still_win_and_help_me_is_chat(assistant, monkeypatch):
    calls = fake_backend(monkeypatch, ["sure"])
    assert assistant.handle("calc 2+2") == "4"
    assert assistant.handle("help").startswith("Commands:")
    assert assistant.handle("help me plan my week") == "sure"
    assert calls[0]["messages"][0]["content"] == "help me plan my week"


def test_http_errors_become_friendly_messages(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-bad")

    class R:
        status_code = 401
        ok = False

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: R())
    try:
        llm.chat([{"role": "user", "content": "hi"}])
    except llm.LLMError as e:
        assert "401" in str(e)
    else:
        raise AssertionError("expected LLMError")


def test_anthropic_request_shape(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    seen = {}

    class R:
        status_code = 200
        ok = True

        def json(self):
            return {"content": [{"type": "text", "text": "hello from the model"}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, body=json)
        return R()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    out = llm.chat([{"role": "user", "content": "hi"}], facts=["esp32: my board"])
    assert out == "hello from the model"
    assert seen["url"].endswith("/v1/messages")
    assert seen["headers"]["x-api-key"] == "sk-test"
    assert seen["body"]["model"] == "claude-sonnet-5-5"
    assert "SPEKTRA" in seen["body"]["system"] and "esp32: my board" in seen["body"]["system"]
    assert seen["body"]["messages"] == [{"role": "user", "content": "hi"}]


def test_auto_picks_free_provider_from_key(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "auto")
    monkeypatch.setattr(llm, "_ollama_up", lambda: False)
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    assert llm.pick_backend() == "gemini"
    monkeypatch.setenv("GROQ_API_KEY", "gq-key")
    assert llm.pick_backend() == "groq"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    assert llm.pick_backend() == "anthropic"


def test_custom_needs_base_url_and_key(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "auto")
    monkeypatch.setattr(llm, "_ollama_up", lambda: False)
    monkeypatch.setenv("SPEKTRA_OPENAI_API_KEY", "k")
    assert llm.pick_backend() == "none"
    monkeypatch.setenv("SPEKTRA_OPENAI_BASE_URL", "http://localhost:1234/v1")
    assert llm.pick_backend() == "custom"


def _fake_post(monkeypatch, status=200, body=None):
    seen = {}

    class R:
        status_code = status
        ok = status < 400

        def json(self):
            return body or {"choices": [{"message": {"content": "hi from groq"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, body=json)
        return R()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return seen


def test_groq_request_shape(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gq-key")
    seen = _fake_post(monkeypatch)
    out = llm.chat([{"role": "user", "content": "yo"}], facts=["a: b"])
    assert out == "hi from groq"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer gq-key"
    msgs = seen["body"]["messages"]
    assert msgs[0]["role"] == "system" and "a: b" in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "yo"}
    assert seen["body"]["model"] == "llama-3.3-70b-versatile"


def test_model_override_and_gemini_url(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("SPEKTRA_LLM_MODEL", "my-model")
    seen = _fake_post(monkeypatch)
    llm.chat([{"role": "user", "content": "yo"}])
    assert seen["url"].startswith("https://generativelanguage.googleapis.com/v1beta/openai/")
    assert seen["body"]["model"] == "my-model"


def test_free_tier_errors_are_friendly(monkeypatch):
    monkeypatch.setenv("SPEKTRA_LLM", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gq-key")
    for status, word in ((429, "rate limit"), (401, "rejected"), (404, "model not found")):
        _fake_post(monkeypatch, status=status)
        try:
            llm.chat([{"role": "user", "content": "yo"}])
        except llm.LLMError as e:
            assert word in str(e)
        else:
            raise AssertionError("expected LLMError")
