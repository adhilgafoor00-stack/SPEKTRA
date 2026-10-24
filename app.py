#!/usr/bin/env python3
import os
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify

from core.envfile import load_env

load_env()  # read API keys from .env (git-ignored) before anything else

from core.assistant import Assistant  # noqa: E402
from core.widgets import get_widgets

app = Flask(__name__, template_folder="templates", static_folder="static")
jarvis = Assistant()

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_INPUT_CHARS = 4000


@app.before_request
def block_cross_site_requests():
    """SPEKTRA runs locally and can touch files, so refuse requests that a random
    website could trigger from the user's browser (CSRF / DNS rebinding)."""
    host = urlparse("//" + (request.host or "")).hostname or ""
    allowed = set(LOCAL_HOSTS) | {h for h in os.environ.get("SPEKTRA_ALLOWED_HOSTS", "").split(",") if h}
    if host not in allowed:
        return jsonify({"ok": False, "reply": "forbidden host"}), 403
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).hostname not in allowed:
            return jsonify({"ok": False, "reply": "forbidden origin"}), 403


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/handle")
def handle():
    if not request.is_json:
        return jsonify({"ok": False, "reply": "send JSON: {\"text\": \"...\"}"}), 415
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "reply": "Please type a command. Try 'help'."})
    if len(text) > MAX_INPUT_CHARS:
        return jsonify({"ok": False, "reply": "input too long"}), 413
    try:
        out = jarvis.handle(text) or ""
        return jsonify({"ok": True, "reply": out})
    except SystemExit:
        return jsonify({"ok": True, "reply": "bye! (server still running)"})
    except Exception as e:
        return jsonify({"ok": False, "reply": f"error: {e}"})


@app.get("/api/widgets")
def widgets():
    try:
        return jsonify({"ok": True, "data": get_widgets()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "data": {}}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Debug mode exposes the Werkzeug console; keep it opt-in.
    debug = os.environ.get("SPEKTRA_DEBUG") == "1"
    host = os.environ.get("SPEKTRA_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=debug)
