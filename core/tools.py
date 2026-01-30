import ast, operator
from textwrap import shorten

try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

try:
    import wikipedia
except Exception:
    wikipedia = None

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

def _eval(node):
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Unsupported expression")

def safe_calc(expr: str) -> str:
    import ast
    try:
        node = ast.parse(expr, mode="eval")
        val = _eval(node.body)
        return str(val)
    except Exception as e:
        return f"calc error: {e}"

def summarize(text: str, max_chars: int = 280) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars-3] + "..."

def ddg_search(query: str, max_results: int = 5):
    if DDGS is None:
        return ["duckduckgo-search not installed"]
    try:
        out = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title") or ""
                body = r.get("body") or ""
                href = r.get("href") or ""
                snippet = shorten(body, width=160, placeholder="...")
                out.append(f"- {title}\n  {snippet}\n  {href}")
        return out or ["No results"]
    except Exception as e:
        return [f"search error: {e}"]

def wiki_summary(topic: str, sentences: int = 2) -> str:
    if wikipedia is None:
        return "wikipedia not installed"
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(topic, sentences=sentences)
    except Exception as e:
        return f"wikipedia error: {e}"
