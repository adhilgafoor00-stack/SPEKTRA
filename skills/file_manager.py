import os

from core.safety import (
    MAX_READ_BYTES,
    SandboxError,
    resolve_in_workspace,
    workspace_dir,
)


def register(app):
    app._register("ls", ls, "List files in the workspace: ls [path]")
    app._register("cat", cat, "Show a workspace file: cat <path>")


def ls(rest: str) -> str:
    try:
        path = resolve_in_workspace(rest.strip() or ".")
        entries = sorted(os.listdir(path))
        return "\n".join(entries) if entries else "(empty)"
    except SandboxError as e:
        return f"ls error: {e}"
    except Exception as e:
        return f"ls error: {e}"


def cat(rest: str) -> str:
    path = rest.strip()
    if not path:
        return "usage: cat <path>"
    try:
        full = resolve_in_workspace(path)
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(MAX_READ_BYTES)
    except SandboxError as e:
        return f"cat error: {e}"
    except Exception as e:
        return f"cat error: {e}"


def workspace_hint() -> str:
    return f"workspace: {workspace_dir()}"
