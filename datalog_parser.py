import re
from dataclasses import dataclass
from typing import List, Union


class ParseError(Exception):
    pass


@dataclass
class Judgment:
    name: str
    args: List[str]  # each arg is either a quoted string literal (with quotes) or a variable name


@dataclass
class Fact:
    judgment: Judgment
    probability: float


@dataclass
class Rule:
    head: Judgment
    body: List[Judgment]


@dataclass
class Comment:
    text: str  # everything after the leading ';', kept raw so it round-trips exactly


_TOKEN_SPEC = [
    ("COMMENT", r";[^\n]*"),
    ("STRING", r'"[^"]*"'),
    ("OP2", r"::|:-"),
    ("NAME", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("NUMBER", r"\d+(?:\.\d+)?"),
    ("PUNCT", r"[(),.]"),
    ("SKIP", r"\s+"),
    ("MISMATCH", r"."),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC))


def _tokenize(text):
    tokens = []
    for m in _TOKEN_RE.finditer(text):
        kind = m.lastgroup
        value = m.group()
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            raise ParseError(f"Unexpected character {value!r} at position {m.start()}")
        tokens.append((kind, value))
    tokens.append(("EOF", ""))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind, value=None):
        kind_actual, value_actual = self.peek()
        if kind_actual != kind or (value is not None and value_actual != value):
            expected = value if value is not None else kind
            raise ParseError(f"Expected {expected!r} but found {value_actual!r}")
        return self.advance()

    def parse_arg(self):
        kind, value = self.peek()
        if kind == "STRING":
            self.advance()
            return value
        if kind == "NAME":
            self.advance()
            if not value[0].islower():
                raise ParseError(f"Judgment arguments must be strings or lowercase variables, found {value!r}")
            return value
        raise ParseError(f"Expected an argument (string or variable) but found {value!r}")

    def parse_judgment(self):
        _, name = self.expect("NAME")
        self.expect("PUNCT", "(")
        args = []
        if self.peek() != ("PUNCT", ")"):
            args.append(self.parse_arg())
            while self.peek() == ("PUNCT", ","):
                self.advance()
                args.append(self.parse_arg())
        self.expect("PUNCT", ")")
        return Judgment(name=name, args=args)

    def parse_declaration(self):
        kind, value = self.peek()
        if kind == "COMMENT":
            self.advance()
            self.expect("EOF")
            return Comment(text=value[1:])

        head = self.parse_judgment()
        kind, value = self.advance()
        if kind == "OP2" and value == "::":
            if not all(arg.startswith('"') for arg in head.args):
                raise ParseError("All arguments to a fact's judgment must be strings")
            _, num_str = self.expect("NUMBER")
            probability = float(num_str)
            self.expect("PUNCT", ".")
            self.expect("EOF")
            return Fact(judgment=head, probability=probability)
        if kind == "OP2" and value == ":-":
            body = [self.parse_judgment()]
            while self.peek() == ("PUNCT", ","):
                self.advance()
                body.append(self.parse_judgment())
            self.expect("PUNCT", ".")
            self.expect("EOF")
            return Rule(head=head, body=body)
        raise ParseError(f"Expected '::' or ':-' but found {value!r}")


def parse_declaration(text: str) -> Union[Fact, Rule, Comment]:
    """Parse a single Datalog fact, inference rule, or comment, per the datalog_prompt grammar."""
    parser = _Parser(_tokenize(text))
    return parser.parse_declaration()


def rule_is_query(rule: Rule) -> bool:
    """Return True if the rule is a query (i.e., its head is Query())."""
    return rule.judgment.name == "Query"
