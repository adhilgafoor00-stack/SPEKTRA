import re
from typing import List, Tuple

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "what", "who", "how", "why", "when",
    "where", "of", "to", "in", "on", "and", "or", "do", "does", "me", "my",
    "about", "tell", "explain", "define",
}


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def score(topic: str, query: str) -> int:
    return len(_words(topic) & _words(query))


def best_match(topics: List[str], query: str) -> Tuple[str, int]:
    best = ("", 0)
    for t in topics:
        s = score(t, query)
        if s > best[1]:
            best = (t, s)
    return best


def top_matches(topics: List[str], query: str, limit: int = 3) -> List[str]:
    """Topics with a non-zero overlap with the query, best first."""
    scored = [(score(t, query), t) for t in topics]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [t for _, t in scored[:limit]]
