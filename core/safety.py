"""Filesystem sandbox helpers.

All file-touching commands (ls, cat, gen, genproj) resolve paths through
`resolve_in_workspace`, so they can never escape the workspace folder.
Override the folder with the SPEKTRA_WORKSPACE environment variable.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKSPACE = os.path.join(_ROOT, "workspace")

MAX_READ_BYTES = 4000
MAX_WRITE_BYTES = 100_000


class SandboxError(ValueError):
    pass


def workspace_dir() -> str:
    path = os.path.abspath(os.environ.get("SPEKTRA_WORKSPACE", DEFAULT_WORKSPACE))
    os.makedirs(path, exist_ok=True)
    return path


def resolve_in_workspace(user_path: str) -> str:
    """Return an absolute path inside the workspace or raise SandboxError."""
    root = os.path.realpath(workspace_dir())
    user_path = (user_path or ".").strip()
    if os.path.isabs(user_path):
        raise SandboxError("absolute paths are not allowed; use a path inside the workspace")
    target = os.path.realpath(os.path.join(root, user_path))
    if target != root and not target.startswith(root + os.sep):
        raise SandboxError("path escapes the workspace")
    return target


_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def valid_project_name(name: str) -> bool:
    return bool(_NAME_RE.match(name)) and name not in (".", "..")
