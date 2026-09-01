from tabnanny import filename_only

import requests
import json
import os
import subprocess

from datalog_parser import ParseError, Judgment, Fact, Rule, Comment, parse_declaration
from query_parser import QueryParseError, QueryResult, parse_query_result, parse_query_results


datalog_prompt = """
<system>
You are running in ProbDatalog mode. Every response you give must be either a
Datalog fact, an inference rule, or a comment.

Grammar you must adhere to:

- A judgment `J` is of the form `F(x, y, z, ...)`: a name `F` (e.g., `Edge`) followed by a comma-separated list of arguments. Every name `F` must begin with a capital letter.
- A fact is of the form `J :: P.`, where `J` is a judgment and `P` is a probability. All of the arguments to `J` must be strings.
    - Example: `Edge("x", "y") :: 0.5.`

Grammar for Datalog inferences: `J :- J, J, ... .` where each argument to the judgments are either strings or lowercase variables.
    - The variables are universally quantified over the inference rule.
        - Example: `Foo(x, y, "z") :- Edge(x, y).` This means that `Foo(x, y, "z")` holds IF `Edge(x, y)` holds, for any `x` and `y`.
        - Example: `Bar(x) :- Foo(x, y)`. This means that `Bar(x)` holds IF `Foo(x, y)` holds, for any `x` and `y`.
    - Every judgment on the RHS of the inference MUST be defined previously.

You must output only ONE fact or ONE inference rule.
Your datalog program is in service of answering a yes/no answer.
If you have built up enough of the program to answer the query,
you define an inference `Query() :- ... .` to finish the program.

</system>
"""

def make_prompt(prog, query):
    return f"{datalog_prompt}\n<query>{query} Think VERY CAREFULLY and RIGOUROUSY step by step by using Datalog.</query>\n<prog>{prog}</prog>"

def make_parse_error_prompt(prog, query, error):
    return f"<error>PARSE ERROR: {error}</error>\n{make_prompt(prog, query)}"

def llm(msg):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
    "model": "qwen/qwen3.8-27b",
    "reasoning" : {
        "effort": "none"
    },
    "messages": [
        {
        "role": "user",
        "content": msg
        }
    ]
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']

def runProg(contents):
    with open("tmp.rkt", "w") as f:
        f.write(contents)

    result = subprocess.run(
        ["racket", "tmp.rkt"],
        capture_output=True,
        text=True
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }

rkt_header = """
#lang roulette/example/probalog

% LIBRARY FUNCTIONS
IsZero("0").
Succ("0", "1").
Succ("1", "2").
Succ("2", "3").
Succ("3", "4").
Succ("4", "5").
Succ("5", "6").
Succ("6", "7").
Succ("7", "8").
Succ("8", "9").
Succ("9", "10").
Succ("10", "11").
Succ("11", "12").
Succ("12", "13").
Succ("13", "14").
Succ("14", "15").
Succ("15", "16").
Succ("16", "17").
Succ("17", "18").
Succ("18", "19").
Succ("19", "20").
Succ("20", "21").
Succ("21", "22").

IsLt(a, b) :- Succ(a, b).
IsLt(a, b) :- IsLt(a, c), Succ(c, b).

% LLM PROMPT BELOW
"""
rkt_footer = "? Query()."

def pp_judgment(judgment: Judgment) -> str:
    """Render a judgment as `Name(arg, arg, ...)`. String args already carry quotes."""
    return f"{judgment.name}({', '.join(judgment.args)})"


def pp_declaration(decl) -> str:
    """Render a Fact, Rule, or Comment back into the concrete syntax of the prompt grammar."""
    if isinstance(decl, Fact):
        return f"{pp_judgment(decl.judgment)} :: {decl.probability}."
    if isinstance(decl, Rule):
        body = ", ".join(pp_judgment(j) for j in decl.body)
        return f"{pp_judgment(decl.head)} :- {body}."
    if isinstance(decl, Comment):
        return f";{decl.text}"
    raise TypeError(f"Not a declaration: {decl!r}")


def pp_prog(prog) -> str:
    return "\n".join(pp_declaration(decl) for decl in prog)


def is_query_rule(decl) -> bool:
    """True if `decl` is the terminating `Query() :- ... .` inference."""
    return isinstance(decl, Rule) and decl.head.name == "Query"


MAX_DECLARATIONS = 20
MAX_PARSE_RETRIES = 5


def next_declaration(prog, query, max_parse_retries=MAX_PARSE_RETRIES):
    """Ask the LLM for one more declaration, re-prompting until it parses."""
    prompt = make_prompt(pp_prog(prog), query)
    for _ in range(max_parse_retries + 1):
        response = llm(prompt).strip()
        try:
            return parse_declaration(response)
        except ParseError as e:
            prompt = make_parse_error_prompt(
                pp_prog(prog), query, f"{e} (while parsing {response!r})"
            )
    raise RuntimeError(
        f"LLM failed to produce a parseable declaration after {max_parse_retries + 1} attempts"
    )


def make_racket_prog(query, max_declarations=MAX_DECLARATIONS, max_parse_retries=MAX_PARSE_RETRIES):
    """Build a probalog program answering `query` by accumulating LLM-generated
    declarations until it emits a `Query() :- ... .` rule."""
    prog = []
    for _ in range(max_declarations):
        print("Querying..")
        decl = next_declaration(prog, query, max_parse_retries)
        prog.append(decl)
        if is_query_rule(decl):
            return f"{rkt_header}\n\n{pp_prog(prog)}\n\n{rkt_footer}\n"
    raise RuntimeError(
        f"LLM did not define Query() within {max_declarations} declarations"
    )

print(make_racket_prog("Could the members of The Police perform lawful arrests?"))
