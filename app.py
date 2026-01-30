#!/usr/bin/env python3
import os, time
from flask import Flask, render_template, request, jsonify
from core.assistant import Assistant
from core.widgets import get_widgets

app = Flask(__name__, template_folder="templates", static_folder="static")
jarvis = Assistant()

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/handle")
def handle():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "reply": "Please type a command. Try 'help'."})
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
    app.run(host="127.0.0.1", port=port, debug=True)
