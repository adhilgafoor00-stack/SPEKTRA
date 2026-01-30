from typing import Callable

def register(app):
    app._register("echo", lambda rest: rest, "Echo text back")
    app._register("code", codegen, "Generate tiny code snippet: code <lang> \"<intent>\"")
    app._register("default", fallback, "Fallback handler")

def fallback(text: str) -> str:
    return f"I didn't recognize that. Try 'help'. You said: {text}"

def codegen(rest: str) -> str:
    rest = rest.strip()
    if not rest:
        return 'usage: code <lang> "intent"'
    if rest.startswith("python"):
        intent = rest[len("python"):].strip().strip('"').strip("'")
        if "fizz" in intent.lower():
            return "def fizzbuzz(n):\n    for i in range(1, n+1):\n        s = ''\n        if i % 3 == 0: s += 'Fizz'\n        if i % 5 == 0: s += 'Buzz'\n        print(s or i)"
        if "http" in intent.lower():
            return "import requests\nr = requests.get('https://httpbin.org/get')\nprint(r.status_code)\nprint(r.json())"
        return f"# Python stub for: {intent}\nprint('TODO:', {repr(intent)})"
    if rest.startswith("html"):
        intent = rest[len("html"):].strip().strip('"').strip("'")
        return "<!doctype html><meta charset='utf-8'><title>Snippet</title><h1>"+intent+"</h1>"
    return "supported langs: python, html"
