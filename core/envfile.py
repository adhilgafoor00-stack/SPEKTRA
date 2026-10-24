"""Tiny .env loader (no dependency). Lines look like KEY=value; # comments allowed.
Existing environment variables win, so a real `export` still overrides the file.
Keep .env out of git (it is in .gitignore) because it holds your API keys."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path: str = None) -> int:
    path = path or os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return 0
    loaded = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
                loaded += 1
    return loaded
