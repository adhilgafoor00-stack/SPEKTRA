"""Pluggable LLM backend for `ask`.

Backends (chosen with SPEKTRA_LLM, default "auto"):
  anthropic  - Claude via the Messages API   (needs ANTHROPIC_API_KEY)
  ollama     - local model via Ollama        (needs `ollama serve`, offline-friendly)
  none       - disabled, SPEKTRA falls back to facts + Wikipedia

"auto" picks anthropic if a key is set, else ollama if it is reachable, else none.

Env vars:
  SPEKTRA_LLM            auto | anthropic | ollama | none
  SPEKTRA_LLM_MODEL      model name override
  ANTHROPIC_API_KEY      key for the anthropic backend
  OLLAMA_HOST            default http://127.0.0.1:11434
"""
import os
from typing import List, Optional

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"
DEFAULT_OLLAMA_MODEL = "llama3.2"
TIMEOUT = 30

SYSTEM_PROMPT = (
    "You are SPEKTRA, a concise, practical assistant running locally for a student. "
    "Answer in at most 4 short sentences unless asked for more. "
    "If 'Known facts' are provided, treat them as the user's own taught knowledge "
    "and prefer them over your general knowledge when they conflict. "
    "If you are not sure, say so."
)


class LLMError(RuntimeError):
    pass


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _ollama_up() -> bool:
    try:
        return requests.get(_ollama_host() + "/api/tags", timeout=0.6).ok
    except Exception:
        return False


def pick_backend() -> str:
    choice = os.environ.get("SPEKTRA_LLM", "auto").lower()
    if choice in ("anthropic", "ollama", "none"):
        return choice
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if _ollama_up():
        return "ollama"
    return "none"


def build_user_prompt(question: str, facts: List[str], history: List[str]) -> str:
    parts = []
    if facts:
        parts.append("Known facts:\n" + "\n".join(f"- {f}" for f in facts))
    if history:
        parts.append("Recent conversation:\n" + "\n".join(history))
    parts.append("Question: " + question)
    return "\n\n".join(parts)


def _anthropic(prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY is not set")
    r = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.environ.get("SPEKTRA_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL),
            "max_tokens": 400,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise LLMError(f"anthropic HTTP {r.status_code}")
    blocks = r.json().get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise LLMError("empty response")
    return text


def _ollama(prompt: str) -> str:
    r = requests.post(
        _ollama_host() + "/api/chat",
        json={
            "model": os.environ.get("SPEKTRA_LLM_MODEL", DEFAULT_OLLAMA_MODEL),
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=TIMEOUT * 4,  # local models can be slow on first load
    )
    if not r.ok:
        raise LLMError(f"ollama HTTP {r.status_code}")
    text = (r.json().get("message") or {}).get("content", "").strip()
    if not text:
        raise LLMError("empty response")
    return text


def generate(question: str, facts: Optional[List[str]] = None,
             history: Optional[List[str]] = None) -> Optional[str]:
    """Return an LLM answer, or None if no backend is available / the call fails."""
    backend = pick_backend()
    if backend == "none":
        return None
    prompt = build_user_prompt(question, facts or [], history or [])
    try:
        return _anthropic(prompt) if backend == "anthropic" else _ollama(prompt)
    except Exception:
        return None


def status() -> str:
    backend = pick_backend()
    if backend == "none":
        return "llm: off (set ANTHROPIC_API_KEY or run Ollama to enable)"
    default = DEFAULT_ANTHROPIC_MODEL if backend == "anthropic" else DEFAULT_OLLAMA_MODEL
    return f"llm: {backend} ({os.environ.get('SPEKTRA_LLM_MODEL', default)})"
