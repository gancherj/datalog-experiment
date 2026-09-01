import re
from dataclasses import dataclass
from typing import List, Optional


class QueryParseError(Exception):
    pass


@dataclass
class QueryResult:
    query: str
    true_probability: Optional[float]
    false_probability: Optional[float]


_LINE_RE = re.compile(
    r"^(?P<query>.+?):\s*#<pmf:\s*(?P<entries>\[#[tf]\s+[\d.]+\](?:\s*\[#[tf]\s+[\d.]+\])?)\s*>$"
)
_ENTRY_RE = re.compile(r"\[#(?P<bool>[tf])\s+(?P<prob>[\d.]+)\]")


def parse_query_result(line: str) -> QueryResult:
    """Parse a single line of racket output for a `?` query, e.g.:

    `Query(): #<pmf: [#t 0.6] [#f 0.4]>`
    `Query(): #<pmf: [#f 1]>`
    """
    line = line.strip()
    m = _LINE_RE.match(line)
    if not m:
        raise QueryParseError(f"Malformed query result line: {line!r}")

    query = m.group("query").strip()
    entries = _ENTRY_RE.findall(m.group("entries"))

    probs = {}
    for bool_char, prob_str in entries:
        if bool_char in probs:
            raise QueryParseError(f"Duplicate '#{bool_char}' entry in line: {line!r}")
        probs[bool_char] = float(prob_str)

    return QueryResult(
        query=query,
        true_probability=probs.get("t"),
        false_probability=probs.get("f"),
    )


def parse_query_results(text: str) -> List[QueryResult]:
    """Parse every query result line found in racket's stdout."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        results.append(parse_query_result(line))
    return results
