from typing import Dict, Callable
from core.memory import Memory
from core import tools
from core.learn import best_match
import importlib, pkgutil, os, re

class Assistant:
    def __init__(self):
        self.memory = Memory()
        self.commands: Dict[str, Callable[[str], str]] = {}
        self._register_builtin()
        self._load_skills()

    def _register(self, cmd: str, func: Callable[[str], str], help_text: str):
        self.commands[cmd] = func
        setattr(self, f"help_{cmd}", help_text)

    def _register_builtin(self):
        self._register("help", self.cmd_help, "Show this help")
        self._register("quit", self.cmd_quit, "Exit the assistant (server keeps running)")
        self._register("calc", self.cmd_calc, "Calculate: calc 2*(3+4)")
        self._register("summarize", self.cmd_summarize, "Summarize a long text")
        self._register("ask", self.cmd_ask, "Ask (learned facts + Wikipedia)")
        self._register("teach", self.cmd_teach, "Teach a fact: teach <topic>: <fact>")
        self._register("facts", self.cmd_facts, "List learned topics")
        self._register("search", self.cmd_search, "Web search via DuckDuckGo")
        self._register("save", self.cmd_save, "Save note: save note <text>")
        self._register("notes", self.cmd_notes, "List notes")
        self._register("recall", self.cmd_recall, "Show last interactions")
        self._register("gen", self.cmd_gen, "Generate helper files: gen file <path> <content>")
        self._register("genproj", self.cmd_genproj, "Scaffold a project: genproj <python-cli|flask-app|tkinter-app> <dir>")

    def _load_skills(self):
        skills_pkg = "skills"
        pkg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), skills_pkg)
        for _, modname, ispkg in pkgutil.iter_modules([pkg_path]):
            if ispkg: continue
            module = importlib.import_module(f"{skills_pkg}.{modname}")
            if hasattr(module, "register"):
                module.register(self)

    # --- builtins ---
    def cmd_help(self, _: str) -> str:
        lines = ["Commands:"]
        for k in sorted(self.commands.keys()):
            if k == "help": continue
            desc = getattr(self, f"help_{k}", "")
            lines.append(f"- {k}: {desc}")
        return "\n".join(lines)

    def cmd_quit(self, _: str) -> str:
        return "bye!"

    def cmd_calc(self, rest: str) -> str:
        expr = rest.strip()
        return tools.safe_calc(expr) if expr else "usage: calc <expr>"

    def cmd_summarize(self, rest: str) -> str:
        return tools.summarize(rest.strip()) if rest.strip() else "usage: summarize <text>"

    def cmd_ask(self, rest: str) -> str:
        q = rest.strip()
        if not q: return "usage: ask <question>"
        # 1) check learned facts
        topics = self.memory.list_topics()
        match, score = best_match(topics, q)
        if score > 0:
            facts = self.memory.get_facts(match)
            if facts:
                merged = "; ".join(f["fact"] for f in facts[-3:])
                ans = f"(learned) {match}: {merged}"
                self.memory.log_interaction(f"ask: {q}", ans)
                return ans
        # 2) wikipedia
        ans = tools.wiki_summary(q, sentences=2)
        if "error" in ans or "not installed" in ans:
            ans = f"(base) Recap for '{q}': " + tools.summarize(q)
        self.memory.log_interaction(f"ask: {q}", ans)
        return ans

    def cmd_teach(self, rest: str) -> str:
        m = re.match(r"\s*([^:]+)\s*:\s*(.+)", rest)
        if not m:
            return "usage: teach <topic>: <fact>"
        topic, fact = m.group(1), m.group(2)
        self.memory.add_fact(topic, fact)
        self.memory.log_interaction(f"teach: {topic}", fact)
        return f"learned: {topic}"

    def cmd_facts(self, _: str) -> str:
        topics = self.memory.list_topics()
        if not topics: return "no facts yet. teach <topic>: <fact>"
        return "topics:\n- " + "\n- ".join(topics)

    def cmd_search(self, rest: str) -> str:
        q = rest.strip()
        if not q: return "usage: search duckduckgo <query>"
        m = re.match(r"duckduckgo\s+(.+)", q, flags=re.I)
        if not m:
            return "Only 'duckduckgo' is supported now. Try: search duckduckgo <query>"
        results = tools.ddg_search(m.group(1))
        return "Search results:\n" + "\n".join(results)

    def cmd_save(self, rest: str) -> str:
        if not rest.lower().startswith("note"):
            return "usage: save note <text>"
        text = rest[4:].strip()
        if not text:
            return "usage: save note <text>"
        self.memory.add_note(text)
        self.memory.log_interaction(f"save note: {text}", "saved")
        return "noted."

    def cmd_notes(self, _: str) -> str:
        notes = self.memory.list_notes()
        if not notes:
            return "no notes yet."
        lines = []
        for i, n in enumerate(notes, 1):
            lines.append(f"{i}. {n['text']}")
        return "\n".join(lines)

    def cmd_recall(self, rest: str) -> str:
        n = 5
        try:
            n = int(rest.strip()) if rest.strip() else 5
        except:
            pass
        items = self.memory.last(n)
        if not items: return "nothing yet."
        lines = []
        for it in items:
            lines.append(f"you: {it['user']}\njarvis: {it['assistant']}\n---")
        return "\n".join(lines)

    def cmd_gen(self, rest: str) -> str:
        parts = rest.strip().split(" ", 2)
        if len(parts) < 3 or parts[0] != "file":
            return "usage: gen file <path> <content>"
        path, content = parts[1], parts[2]
        try:
            abspath = os.path.abspath(path)
            with open(abspath, "w") as f:
                f.write(content)
            return f"file created: {abspath}"
        except Exception as e:
            return f"gen error: {e}"

    def cmd_genproj(self, rest: str) -> str:
        parts = rest.strip().split()
        if len(parts) < 2:
            return "usage: genproj <python-cli|flask-app|tkinter-app> <dir>"
        template, dest = parts[0], parts[1]
        try:
            os.makedirs(dest, exist_ok=True)
            if template == "python-cli":
                with open(os.path.join(dest, "main.py"), "w") as f:
                    f.write("#!/usr/bin/env python3\nimport sys\nif __name__ == '__main__':\n    print('Hello CLI')\n")
                return f"python-cli scaffolded at {os.path.abspath(dest)}"
            if template == "flask-app":
                with open(os.path.join(dest, "app.py"), "w") as f:
                    f.write("from flask import Flask\napp = Flask(__name__)\n@app.get('/')\ndef home(): return 'Hello Flask'\napp.run(debug=True)\n")
                with open(os.path.join(dest, "requirements.txt"), "w") as f:
                    f.write("flask\n")
                return f"flask-app scaffolded at {os.path.abspath(dest)}"
            if template == "tkinter-app":
                with open(os.path.join(dest, "app.py"), "w") as f:
                    f.write("import tkinter as tk\nr=tk.Tk(); r.title('App'); tk.Label(r,text='Hello').pack(); r.mainloop()\n")
                return f"tkinter-app scaffolded at {os.path.abspath(dest)}"
            return "unknown template"
        except Exception as e:
            return f"genproj error: {e}"

    def handle(self, text: str):
        if not text: return ""
        parts = text.split(" ", 1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        func = self.commands.get(cmd)
        if func:
            return func(rest)
        if "default" in self.commands:
            return self.commands["default"](text)
        return "unknown command. type 'help'."
