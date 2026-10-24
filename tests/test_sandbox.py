import os

from core.safety import workspace_dir


def test_gen_and_cat_roundtrip(assistant):
    assert "file created" in assistant.handle("gen file notes/a.txt hello world")
    assert assistant.handle("cat notes/a.txt") == "hello world"
    assert "a.txt" in assistant.handle("ls notes")


def test_path_traversal_blocked(assistant):
    assert "escapes the workspace" in assistant.handle("cat ../../etc/passwd")
    assert "escapes the workspace" in assistant.handle("gen file ../evil.txt x")
    assert "not allowed" in assistant.handle("cat /etc/passwd")
    assert "not allowed" in assistant.handle("ls /")


def test_symlink_escape_blocked(assistant, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("top secret")
    os.symlink(secret, os.path.join(workspace_dir(), "link.txt"))
    assert "escapes the workspace" in assistant.handle("cat link.txt")


def test_genproj_templates(assistant):
    assert "scaffolded" in assistant.handle("genproj flask-app myapp")
    assert os.path.exists(os.path.join(workspace_dir(), "myapp", "app.py"))
    assert os.path.exists(os.path.join(workspace_dir(), "myapp", "requirements.txt"))


def test_genproj_rejects_bad_names(assistant):
    assert "simple folder name" in assistant.handle("genproj python-cli ../x")
    assert "simple folder name" in assistant.handle("genproj python-cli ..")
    assert "unknown template" in assistant.handle("genproj nope x")
