# SPEKTRA

**Smart Programmable Engine for Knowledge, Technology & Responsive Automation**

A modular, locally-run AI assistant with a sci-fi browser UI (Flask + Three.js). It answers questions with an LLM grounded in facts *you* teach it, scaffolds projects, and talks to real hardware (Arduino / ESP32) or a built-in simulator.

## Features

| Area | What it does |
|---|---|
| **Chat** | Just type. Anything that isn't a command becomes a multi-turn conversation with Claude (API) or a local model (Ollama). `reset` starts a fresh conversation. |
| **Grounded answers** | Facts you `teach` are injected as context for chat and `ask`. `ask` falls back to facts, then Wikipedia, when no LLM is available. |
| **Self-learning memory** | `teach <topic>: <fact>`, `facts`, notes, and a capped interaction log, all in JSON under `data/`. |
| **Hardware bridge** | `hw read temp`, `hw led on`. Simulation mode by default; real boards over USB serial. Live HUD widget. |
| **Dev helpers** | `genproj <python-cli\|flask-app\|tkinter-app> <dir>`, `gen file`, `code`, `calc`, `search`. |
| **HUD widgets** | Clock, system stats, network status, hardware readings. |
| **Plugin skills** | Drop a module with `register(app)` into `skills/` and it loads automatically. |
| **Hardened** | Sandboxed file access, bounded calculator, CSRF/host checks, no debug server by default. |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

Docker: `docker compose up --build` (reachable only from your machine).

## Commands

```
help                              list commands
(any plain sentence)              chat with the model, remembers the conversation
reset                             start a new conversation
ask what is recursion             LLM + your taught facts
llm                               show active LLM backend
teach python: readable language   store a fact
facts                             list taught topics
calc 23*(5+2)                     safe arithmetic
search duckduckgo python venv
save note Buy milk   /  notes  /  recall 3
code python "fizzbuzz"
genproj flask-app myapp           scaffold into workspace/myapp
gen file notes/todo.txt hello     create a file in workspace/
ls [path]  /  cat <path>          browse workspace/ only
hw status | hw read temp|hum|light | hw led on|off | hw reconnect
```

## Turning on the LLM

SPEKTRA picks a backend automatically (`SPEKTRA_LLM=auto`):

```bash
# Option A: Claude API
export ANTHROPIC_API_KEY=sk-ant-...
export SPEKTRA_LLM_MODEL=claude-haiku-5-5     # optional: cheaper/faster (default is claude-sonnet-5-5)

# Option B: fully local/offline
ollama pull llama3.2 && ollama serve
export SPEKTRA_LLM=ollama
```

Get a key at console.anthropic.com (API usage is billed separately from a Claude subscription). Run `llm` in the console to see what is active.

The chat personality lives in `CHAT_SYSTEM_PROMPT` in `core/llm.py`; edit it to change how SPEKTRA talks. Set `SPEKTRA_LLM=none` to disable.

## Using real hardware

1. Flash `docs/firmware/spektra_board.ino` to an Arduino/ESP32 (DHT11 + LDR + LED, pins editable at the top).
2. `pip install -r requirements-hardware.txt`
3. Run with the serial port set:

```bash
export SPEKTRA_HW=serial
export SPEKTRA_SERIAL_PORT=/dev/ttyUSB0   # COM3 on Windows
python app.py
```

Protocol is plain text over serial (`PING`, `GET TEMP`, `LED ON`, ...), documented in `core/hardware.py`, so any board can implement it.

## Security notes

SPEKTRA can read and write files, so it is built to stay local:

- `ls`, `cat`, `gen`, `genproj` only touch the `workspace/` folder (override with `SPEKTRA_WORKSPACE`). Absolute paths, `..` and symlink escapes are rejected.
- `calc` parses arithmetic only (no names or calls) with limits on length, exponent and result size.
- The API rejects non-JSON bodies and requests whose `Host`/`Origin` are not local, so a website you visit cannot drive your assistant.
- Debug mode is opt-in (`SPEKTRA_DEBUG=1`). The server binds to `127.0.0.1` unless `SPEKTRA_HOST` is set.

## Project layout

```
app.py              Flask server and API
core/assistant.py   command router, ask/teach/gen logic
core/llm.py         Claude + Ollama backends
core/hardware.py    simulator + serial device
core/safety.py      workspace sandbox
core/memory.py      JSON memory (facts, notes, log)
skills/             plugins (general, file_manager, hardware)
tests/              pytest suite
docs/firmware/      board firmware
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Writing a skill

```python
# skills/hello.py
def register(app):
    app._register("hello", lambda rest: f"hi {rest or 'there'}", "Say hi")
```

## Roadmap

Voice input/output, MQTT hardware transport, streaming LLM replies, per-skill permissions.
