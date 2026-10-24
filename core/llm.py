"""Pluggable LLM backend for chat and `ask`.

Backends (SPEKTRA_LLM, default "auto"):
  groq        - free tier, no card needed        GROQ_API_KEY
  gemini      - Google AI Studio free tier       GEMINI_API_KEY
  openrouter  - has ":free" models               OPENROUTER_API_KEY
  openai      - OpenAI (paid credits needed)     OPENAI_API_KEY
  custom      - any OpenAI-compatible server     SPEKTRA_OPENAI_BASE_URL + SPEKTRA_OPENAI_API_KEY
  anthropic   - Claude (paid)                    ANTHROPIC_API_KEY
  ollama      - local model, free and offline    needs `ollama serve`
  none        - disabled

"auto" uses the first one whose key is set (order above is the order tried:
anthropic, groq, gemini, openrouter, openai, custom), else Ollama if running, else none.

Other env vars:
  SPEKTRA_LLM_MODEL   model name override (every provider has a sensible default)
  OLLAMA_HOST         default http://127.0.0.1:11434
"""
import os
from typing import List, Optional

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"  # use claude-haiku-5-5 for cheaper/faster
DEFAULT_OLLAMA_MODEL = "llama3.2"

# OpenAI-compatible providers: name -> (base url, key env var, default model).
# Free-tier model names change often; override with SPEKTRA_LLM_MODEL if one is retired.
OPENAI_COMPAT = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
               "gemini-flash-latest"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
                   "meta-llama/llama-3.3-70b-instruct:free"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "custom": (None, "SPEKTRA_OPENAI_API_KEY", "gpt-4o-mini"),
}
AUTO_ORDER = ["groq", "gemini", "openrouter", "openai", "custom"]
TIMEOUT = 30

SYSTEM_PROMPT = (
    "You are SPEKTRA, a concise, practical assistant running locally for a student. "
    "Answer in at most 4 short sentences unless asked for more. "
    "If 'Known facts' are provided, treat them as the user's own taught knowledge "
    "and prefer them over your general knowledge when they conflict. "
    "If you are not sure, say so."
)


CHAT_SYSTEM_PROMPT = (
    "You are SPEKTRA, a personal assistant built by AG, a hardware-engineering student, "
    "and running locally on their machine. Talk like a thoughtful, warm, direct friend who "
    "knows the subject: natural conversational prose, no filler or flattery, honest when "
    "you are unsure or disagree. Match the length of the question: short answers for "
    "casual or simple questions, more depth only when asked or needed. Ask a brief "
    "clarifying question when a request is genuinely ambiguous. Use code blocks for code. "
    "Avoid heavy formatting such as headers and long bullet lists unless the user asks. "
    "The reply is shown in a plain-text console, so do not use markdown bold or tables. "
    "If 'Known facts' are provided they are things the user taught you: use them when "
    "relevant and prefer them over your general knowledge if they conflict. "
    "Never claim to have run commands, read files or touched hardware unless the user "
    "pasted the result; tell them the console commands (help) that do those things."
)


class LLMError(RuntimeError):
    pass


def _env(name: str) -> str:
    """Env var with the usual copy/paste damage removed: surrounding spaces, newlines,
    quotes (Windows `set KEY="..."` keeps them) and an accidental 'Bearer ' prefix."""
    v = (os.environ.get(name) or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    if v.lower().startswith("bearer "):
        v = v[7:].strip()
    return v


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _ollama_up() -> bool:
    try:
        return requests.get(_ollama_host() + "/api/tags", timeout=0.6).ok
    except Exception:
        return False


def _compat_config(name: str):
    base, key_env, model = OPENAI_COMPAT[name]
    if name == "custom":
        base = _env("SPEKTRA_OPENAI_BASE_URL")
    return base, _env(key_env), model


def _compat_ready(name: str) -> bool:
    base, key, _ = _compat_config(name)
    return bool(base and key)


def pick_backend() -> str:
    choice = os.environ.get("SPEKTRA_LLM", "auto").lower()
    if choice in ("anthropic", "ollama", "none") or choice in OPENAI_COMPAT:
        return choice
    if _env("ANTHROPIC_API_KEY"):
        return "anthropic"
    for name in AUTO_ORDER:
        if _compat_ready(name):
            return name
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


def _anthropic(messages: List[dict], system: str, max_tokens: int) -> str:
    key = _env("ANTHROPIC_API_KEY")
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
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        },
        timeout=TIMEOUT * 2,
    )
    if r.status_code == 401:
        raise LLMError("API key rejected (401). Check ANTHROPIC_API_KEY is copied in full and still active.")
    if r.status_code == 429:
        raise LLMError("rate limited (429). Try again in a moment.")
    if not r.ok:
        raise LLMError(f"anthropic HTTP {r.status_code}")
    blocks = r.json().get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise LLMError("empty response")
    return text


def _ollama(messages: List[dict], system: str, max_tokens: int) -> str:
    r = requests.post(
        _ollama_host() + "/api/chat",
        json={
            "model": os.environ.get("SPEKTRA_LLM_MODEL", DEFAULT_OLLAMA_MODEL),
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}] + messages,
        },
        timeout=TIMEOUT * 4,  # local models can be slow on first load
    )
    if not r.ok:
        raise LLMError(f"ollama HTTP {r.status_code}")
    text = (r.json().get("message") or {}).get("content", "").strip()
    if not text:
        raise LLMError("empty response")
    return text


def _openai_compat(name: str):
    def call(messages: List[dict], system: str, max_tokens: int) -> str:
        base, key, default_model = _compat_config(name)
        if not base or not key:
            raise LLMError(f"{name}: missing base URL or API key")
        r = requests.post(
            base.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("SPEKTRA_LLM_MODEL", default_model),
                "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}] + messages,
            },
            timeout=TIMEOUT * 2,
        )
        if r.status_code in (401, 403):
            raise LLMError(f"{name}: API key rejected ({r.status_code}). Check it is copied in full (no quotes or spaces) and still active in the provider's console; make a new key if unsure.")
        if r.status_code == 404:
            raise LLMError(f"{name}: model not found. Set SPEKTRA_LLM_MODEL to a current model name.")
        if r.status_code == 429:
            raise LLMError(f"{name}: free-tier rate limit hit (429). Wait a bit and try again.")
        if not r.ok:
            raise LLMError(f"{name} HTTP {r.status_code}")
        choices = r.json().get("choices") or []
        text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
        if not text:
            raise LLMError("empty response")
        return text
    return call


def _complete(messages: List[dict], system: str, max_tokens: int) -> str:
    backend = pick_backend()
    if backend == "none":
        raise LLMError("no LLM configured")
    if backend == "anthropic":
        fn = _anthropic
    elif backend == "ollama":
        fn = _ollama
    else:
        fn = _openai_compat(backend)
    return fn(messages, system, max_tokens)


def generate(question: str, facts: Optional[List[str]] = None,
             history: Optional[List[str]] = None) -> Optional[str]:
    """One-shot answer for `ask`. Returns None if no backend is available / the call fails."""
    if pick_backend() == "none":
        return None
    prompt = build_user_prompt(question, facts or [], history or [])
    try:
        return _complete([{"role": "user", "content": prompt}], SYSTEM_PROMPT, 400)
    except Exception:
        return None


def chat(messages: List[dict], facts: Optional[List[str]] = None) -> str:
    """Multi-turn conversation. `messages` alternates user/assistant and ends with a
    user turn. Raises LLMError (with a user-presentable message) on failure."""
    system = CHAT_SYSTEM_PROMPT
    if facts:
        system += "\n\nKnown facts:\n" + "\n".join(f"- {f}" for f in facts)
    try:
        return _complete(messages, system, 1024)
    except LLMError:
        raise
    except requests.Timeout:
        raise LLMError("the model took too long to answer. Try again.")
    except requests.RequestException:
        raise LLMError("could not reach the model (network problem).")


def status() -> str:
    backend = pick_backend()
    if backend == "none":
        return ("llm: off. Free options: set GROQ_API_KEY or GEMINI_API_KEY, "
                "or run Ollama. See README.")
    if backend == "anthropic":
        default = DEFAULT_ANTHROPIC_MODEL
    elif backend == "ollama":
        default = DEFAULT_OLLAMA_MODEL
    else:
        default = OPENAI_COMPAT[backend][2]
    return f"llm: {backend} ({os.environ.get('SPEKTRA_LLM_MODEL', default)})"
