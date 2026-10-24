import json, os, time
from typing import Any, Dict, List

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_PATH = os.path.join(DEFAULT_DIR, "memory.json")
FACTS_PATH = os.path.join(DEFAULT_DIR, "facts.json")

class Memory:
    def __init__(self, path: str = DEFAULT_PATH, facts_path: str = FACTS_PATH):
        self.path = path
        self.facts_path = facts_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump({"notes": [], "log": []}, f, indent=2)
        if not os.path.exists(self.facts_path):
            with open(self.facts_path, "w") as f:
                json.dump({"facts": {}}, f, indent=2)
        self._load()
        self._load_facts()

    def _load(self):
        with open(self.path, "r") as f:
            self.data = json.load(f)

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def _load_facts(self):
        with open(self.facts_path, "r") as f:
            self.facts = json.load(f)

    def _save_facts(self):
        with open(self.facts_path, "w") as f:
            json.dump(self.facts, f, indent=2)

    # notes / log
    def add_note(self, text: str):
        self.data.setdefault("notes", []).append({"text": text, "ts": time.time()})
        self._save()

    def list_notes(self):
        return list(self.data.get("notes", []))

    MAX_LOG = 500

    def log_interaction(self, user: str, assistant: str):
        log = self.data.setdefault("log", [])
        log.append({"user": user, "assistant": assistant, "ts": time.time()})
        if len(log) > self.MAX_LOG:
            del log[:len(log) - self.MAX_LOG]
        self._save()

    def last(self, n: int = 5):
        return self.data.get("log", [])[-n:]

    # facts
    def add_fact(self, topic: str, fact: str):
        topic = topic.strip().lower()
        if not topic: return
        self.facts.setdefault("facts", {}).setdefault(topic, [])
        self.facts["facts"][topic].append({"fact": fact.strip(), "ts": time.time()})
        self._save_facts()

    def list_topics(self):
        return sorted(self.facts.get("facts", {}).keys())

    def get_facts(self, topic: str):
        return self.facts.get("facts", {}).get(topic.strip().lower(), [])
