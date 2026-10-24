import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test gets its own workspace, data folder and simulated hardware."""
    monkeypatch.setenv("SPEKTRA_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("SPEKTRA_LLM", "none")
    monkeypatch.setenv("SPEKTRA_HW", "sim")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from core import hardware
    hardware.reset_device()
    yield
    hardware.reset_device()


@pytest.fixture
def assistant(tmp_path):
    from core.assistant import Assistant
    from core.memory import Memory
    a = Assistant()
    a.memory = Memory(str(tmp_path / "memory.json"), str(tmp_path / "facts.json"))
    return a


@pytest.fixture
def client(assistant):
    import app as app_module
    app_module.jarvis = assistant
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()
