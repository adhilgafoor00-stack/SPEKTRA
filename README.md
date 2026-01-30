# SPEKTRA v2 (No Voice) — Widgets + Learning + Programming

New in v2:
- HUD widgets: **clock**, **system stats**, **network status** (auto-refresh).
- Self-learning: `teach <topic>: <fact>` and `facts` + retrieval used by `ask`.
- Programming helper: `genproj <template> <dir>` (templates: `python-cli`, `flask-app`, `tkinter-app`).
- Wikipedia Q&A (`ask ...`) — requires `wikipedia` package (included).

## Quick Start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

## Commands
- `help` — show commands
- `ask what is recursion`
- `teach python: a language focused on readability` — store a fact
- `facts` — list stored topics
- `calc 23*(5+2)`
- `search duckduckgo python venv`
- `save note Buy milk` → `notes`
- `recall 3`
- `code python "fizzbuzz"` — tiny snippet
- `genproj flask-app myapp` — scaffold a starter project
- `ls` / `cat path/to/file`

## Notes
- If `psutil` fails to install on Termux, widgets will gracefully degrade.
- If `wikipedia` fails, `ask` falls back to local reasoning + learned facts.
