import re
from typing import List, Tuple

def score(topic: str, query: str) -> int:
    t = set(re.findall(r"[a-z0-9]+", topic.lower()))
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    return len(t & q)

def best_match(topics: List[str], query: str) -> Tuple[str, int]:
    best = ("", 0)
    for t in topics:
        s = score(t, query)
        if s > best[1]:
            best = (t, s)
    return best
