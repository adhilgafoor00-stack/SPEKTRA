from typing import Dict, Callable
from core.memory import Memory
from core import tools
from core.learn import best_match, top_matches
from core import llm
from core.safety import (
    MAX_WRITE_BYTES, SandboxError, resolve_in_workspace, valid_project_name,
)
import importlib, pkgutil, os, re

class Assistant:
    def __init__(self):
        self.memory = Memory()
        self.history = []  # chat turns for this server session: [{"role","content"}, ...]
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
        self._register("ask", self.cmd_ask, "Ask (LLM + your taught facts, falls back to Wikipedia)")
        self._register("llm", self.cmd_llm, "Show which LLM backend is active")
        self._register("chat", self.cmd_chat, "Chat explicitly: chat <message> (plain text works too)")
        self._register("reset", self.cmd_reset, "Forget the current chat conversation")
        self._register("teach", self.cmd_teach, "Teach a fact: teach <topic>: <fact>")
        self._register("facts", self.cmd_facts, "List learned topics")
        self._register("search", self.cmd_search, "Web search via DuckDuckGo")
        self._register("save", self.cmd_save, "Save note: save note <text>")
        self._register("notes", self.cmd_notes, "List notes")
        self._register("recall", self.cmd_recall, "Show last interactions")
        self._register("gen", self.cmd_gen, "Create a workspace file: gen file <path> <content>")
        self._register("genproj", self.cmd_genproj, "Scaffold a project in the workspace: genproj <python-cli|flask-app|tkinter-app> <dir>")

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
        # relevant taught facts (used as context for the LLM, or as the answer offline)
        topics = top_matches(self.memory.list_topics(), q, limit=3)
        facts = []
        for t in topics:
            for f in self.memory.get_facts(t)[-3:]:
                facts.append(f"{t}: {f['fact']}")
        history = []
        for it in self.memory.last(3):
            history.append(f"user: {it['user']}")
            history.append(f"spektra: {it['assistant']}")
        # 1) LLM, grounded in learned facts
        ans = llm.generate(q, facts=facts, history=history)
        if ans:
            self.memory.log_interaction(f"ask: {q}", ans)
            return ans
        # 2) learned facts only
        if facts:
            ans = "(learned) " + "; ".join(facts)
            self.memory.log_interaction(f"ask: {q}", ans)
            return ans
        # 3) wikipedia
        ans = tools.wiki_summary(q, sentences=2)
        if "error" in ans or "not installed" in ans:
            ans = f"(base) Recap for '{q}': " + tools.summarize(q)
        self.memory.log_interaction(f"ask: {q}", ans)
        return ans

    def cmd_llm(self, _: str) -> str:
        return llm.status()

    NO_ARG_COMMANDS = {"help", "quit", "facts", "notes", "llm", "reset"}
    MAX_HISTORY = 20  # messages kept in the live conversation

    NO_LLM_MESSAGE = (
        "I can chat once a model is connected. Free options:\n"
        "1) Groq: get a free key at console.groq.com, then set GROQ_API_KEY.\n"
        "2) Gemini: free key from Google AI Studio, then set GEMINI_API_KEY.\n"
        "3) Local: install Ollama, run `ollama pull llama3.2`, set SPEKTRA_LLM=ollama.\n"
        "(Paid: ANTHROPIC_API_KEY or OPENAI_API_KEY.) Restart after setting a key.\n"
        "Until then I still do commands. Type 'help'."
    )

    def _relevant_facts(self, text: str):
        facts = []
        for t in top_matches(self.memory.list_topics(), text, limit=3):
            for f in self.memory.get_facts(t)[-3:]:
                facts.append(f"{t}: {f['fact']}")
        return facts

    def cmd_chat(self, rest: str) -> str:
        text = rest.strip()
        if not text:
            return "say something! e.g. chat explain pull-up resistors"
        if llm.pick_backend() == "none":
            return self.NO_LLM_MESSAGE
        messages = self.history[-(self.MAX_HISTORY - 1):] + [{"role": "user", "content": text}]
        # the API needs the first turn to be from the user
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        try:
            reply = llm.chat(messages, facts=self._relevant_facts(text))
        except llm.LLMError as e:
            return f"(chat error) {e}"
        # only remember the exchange once it succeeded, so history stays well-formed
        self.history.extend([{"role": "user", "content": text},
                             {"role": "assistant", "content": reply}])
        del self.history[:-self.MAX_HISTORY]
        self.memory.log_interaction(f"chat: {text}", reply)
        return reply

    def cmd_reset(self, _: str) -> str:
        self.history.clear()
        return "conversation cleared."

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
        if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            return "gen error: content too large"
        try:
            abspath = resolve_in_workspace(path)
            os.makedirs(os.path.dirname(abspath), exist_ok=True)
            with open(abspath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"file created: {os.path.relpath(abspath, resolve_in_workspace('.'))}"
        except SandboxError as e:
            return f"gen error: {e}"
        except Exception as e:
            return f"gen error: {e}"

    TEMPLATES = {
        "python-cli": {
            "main.py": "#!/usr/bin/env python3\nimport sys\n\n\ndef main(argv):\n    print('Hello CLI')\n\n\nif __name__ == '__main__':\n    main(sys.argv[1:])\n",
        },
        "flask-app": {
            "app.py": "from flask import Flask\n\napp = Flask(__name__)\n\n\n@app.get('/')\ndef home():\n    return 'Hello Flask'\n\n\nif __name__ == '__main__':\n    app.run(host='127.0.0.1', port=5000)\n",
            "requirements.txt": "flask\n",
        },
        "tkinter-app": {
            "app.py": "import tkinter as tk\n\nroot = tk.Tk()\nroot.title('App')\ntk.Label(root, text='Hello').pack()\nroot.mainloop()\n",
        },
    }

    def cmd_genproj(self, rest: str) -> str:
        parts = rest.strip().split()
        if len(parts) != 2:
            return "usage: genproj <python-cli|flask-app|tkinter-app> <dir>"
        template, dest = parts
        files = self.TEMPLATES.get(template)
        if files is None:
            return "unknown template. choose: " + ", ".join(self.TEMPLATES)
        if not valid_project_name(dest):
            return "genproj error: use a simple folder name (letters, digits, . _ -)"
        try:
            root = resolve_in_workspace(dest)
            os.makedirs(root, exist_ok=True)
            for name, body in files.items():
                with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                    f.write(body)
            return f"{template} scaffolded at workspace/{dest}"
        except SandboxError as e:
            return f"genproj error: {e}"
        except Exception as e:
            return f"genproj error: {e}"

    def handle(self, text: str):
        if not text: return ""
        parts = text.split(" ", 1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        func = self.commands.get(cmd)
        # "help me with X" is conversation, not the `help` command
        if cmd in self.NO_ARG_COMMANDS and rest.strip():
            func = None
        if func:
            return func(rest)
        # not a command: treat it as conversation
        return self.cmd_chat(text)
