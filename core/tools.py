import ast
import operator
from textwrap import shorten

try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

try:
    import wikipedia
except Exception:
    wikipedia = None

MAX_EXPR_LEN = 200
MAX_POW_EXPONENT = 1000
MAX_ABS_VALUE = 10 ** 100

BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _check(value):
    if isinstance(value, (int, float)) and abs(value) > MAX_ABS_VALUE:
        raise ValueError("result too large")
    return value


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return _check(UNARY_OPS[type(node.op)](_eval(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POW_EXPONENT:
            raise ValueError("exponent too large")
        return _check(BIN_OPS[type(node.op)](left, right))
    raise ValueError("unsupported expression")


def safe_calc(expr: str) -> str:
    """Evaluate arithmetic only (no names, calls, attributes). Bounded to avoid DoS."""
    if len(expr) > MAX_EXPR_LEN:
        return "calc error: expression too long"
    try:
        node = ast.parse(expr, mode="eval")
        return str(_eval(node.body))
    except ZeroDivisionError:
        return "calc error: division by zero"
    except Exception as e:
        return f"calc error: {e}"


def summarize(text: str, max_chars: int = 280) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


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
