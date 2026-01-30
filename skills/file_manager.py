import os

def register(app):
    app._register("ls", ls, "List files: ls [path]")
    app._register("cat", cat, "Show file content: cat <path>")

def ls(rest: str) -> str:
    path = rest.strip() or "."
    try:
        entries = os.listdir(path)
        return "\n".join(entries) if entries else "(empty)"
    except Exception as e:
        return f"ls error: {e}"

def cat(rest: str) -> str:
    path = rest.strip()
    if not path: return "usage: cat <path>"
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(4000)
        return data
    except Exception as e:
        return f"cat error: {e}"
