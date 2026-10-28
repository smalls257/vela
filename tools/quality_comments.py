"""Comment gates: what-comments, restating docstrings and unexplained suppressions.

The Violation these prevent is Fossil Comments (and Forensic Coding where a docstring takes the slot the why
belongs in). A comment that says what the next line does rots into a lie when the line changes; a docstring that
repeats the signature tells the reader nothing and hides that no one wrote the why. A bare `noqa` is a Silent
Fallback: it switches a check off for the whole line without saying what was judged.

Each check is a word-overlap heuristic over content words, so it can be wrong in both directions. The bar is set
so a real why-comment that happens to share words with its next line passes: deleting a good comment is the
worse error.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize

from quality_report import Finding

STOP = frozenset("""a an the of to for and or in on is it this that with by from as be are its return returns get gets
set sets value values result results given self none true false""".split())
WHAT_OVERLAP = 0.7
DOC_OVERLAP = 0.8
DOC_MAX_WORDS = 15
MIN_COMMENT_WORDS = 2
# Comment lines that carry a directive or a banner rather than prose.
DIRECTIVE_STARTS = ("noqa", "nosemgrep", "type:", "pragma", "ruleid:", "ok:")
BANNER_STARTS = ("---", "===")
CODING_LINE = re.compile(r"coding[:=]")
LIZARD_FORGIVE = re.compile(r"lizard\s*forgive")
SUPPRESSION = re.compile(r"\b(noqa|nosemgrep)\b(.*)")
NOQA_CODES = re.compile(r"\s*:?\s*[A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*")
RULE_IDS = re.compile(r"\s*:?\s*[\w.\-]+(?:\s*,\s*[\w.\-]+)*")
MIN_REASON_WORDS = 2


def content_words(text: str) -> list[str]:
    """Lowercased words of the text with identifiers split on `_` and camelCase, minus the filler words."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return [w for w in (w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]*", spaced)) if w not in STOP]


def same_word(a: str, b: str) -> bool:
    """Equal, or the shorter has at least 4 letters and starts the longer (`parse` matches `parses`)."""
    short, long_ = sorted((a, b), key=len)
    return a == b or (len(short) >= 4 and long_.startswith(short))


def _overlap(words: list[str], against: list[str]) -> float:
    return sum(any(same_word(w, other) for other in against) for w in words) / len(words)


# ---------------------------------------------------------------- what-comments

def _comment_tokens(source: str) -> list[tokenize.TokenInfo]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [t for t in tokens if t.type == tokenize.COMMENT]


def _full_line_blocks(source: str) -> list[list[tokenize.TokenInfo]]:
    """Runs of consecutive comments that each sit alone on their line."""
    blocks: list[list[tokenize.TokenInfo]] = []
    for tok in _comment_tokens(source):
        if not tok.line.strip().startswith("#"):
            continue
        if blocks and blocks[-1][-1].start[0] == tok.start[0] - 1:
            blocks[-1].append(tok)
        else:
            blocks.append([tok])
    return blocks


def _is_directive_or_banner(first_line: str) -> bool:
    text = first_line.lstrip("#").strip()
    return (first_line.startswith("#!") or bool(CODING_LINE.search(first_line))
            or text.startswith(BANNER_STARTS + DIRECTIVE_STARTS))


def _next_code_line(lines: list[str], after: int) -> str:
    """The first line after 1-based line `after` that is neither blank nor a comment, or ''."""
    for line in lines[after:]:
        if line.strip() and not line.strip().startswith("#"):
            return line
    return ""


def what_comments(path: str, source: str) -> list[Finding]:
    """Comment blocks whose words mostly repeat the next line of code."""
    lines = source.splitlines()
    found = []
    for block in _full_line_blocks(source):
        if _is_directive_or_banner(block[0].string):
            continue
        words = content_words(" ".join(t.string.lstrip("#") for t in block))
        code = content_words(_next_code_line(lines, block[-1].start[0]))
        if len(words) >= MIN_COMMENT_WORDS and code and _overlap(words, code) >= WHAT_OVERLAP:
            found.append(Finding(path, block[0].start[0], "QG-CMT-WHAT",
                                 "this comment says what the next line does; say why, or delete it"))
    return found


# ---------------------------------------------------------------- docstrings

def _parameter_names(node: ast.AST) -> list[str]:
    args = node.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]
    return [a.arg for a in named if a]


def _restates_signature(node: ast.AST, doc: str) -> bool:
    words = content_words(doc)
    if len(doc.split()) > DOC_MAX_WORDS or not words:
        return False
    signature = content_words(" ".join([node.name, *_parameter_names(node)]))
    return bool(signature) and _overlap(words, signature) >= DOC_OVERLAP


def restating_docstrings(path: str, tree: ast.Module) -> list[Finding]:
    """Short function docstrings that say nothing the name and parameters did not."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if doc and _restates_signature(node, doc):
            found.append(Finding(path, node.body[0].lineno, "QG-CMT-DOC",
                                 "the docstring restates the signature; say why it exists or what it refuses"))
    return sorted(found, key=lambda f: f.line)


# ---------------------------------------------------------------- suppressions

def _has_reason(comment: str) -> bool:
    """Whether the text after `noqa: CODES` or `nosemgrep: rule-id` gives at least two words of why."""
    hit = SUPPRESSION.search(comment)
    rest = hit.group(2)
    codes = NOQA_CODES if hit.group(1) == "noqa" else RULE_IDS
    after_codes = rest[codes.match(rest).end():] if codes.match(rest) else rest
    return len(re.findall(r"\w+", after_codes)) >= MIN_REASON_WORDS


def unexplained_suppressions(path: str, source: str) -> list[Finding]:
    """In-line off switches with no reason, and any lizard forgive comment."""
    found = []
    for tok in _comment_tokens(source):
        line = tok.start[0]
        if LIZARD_FORGIVE.search(tok.string):
            found.append(Finding(path, line, "QG-CMT-SUPPRESS", "lizard waivers live in .quality/complexity-waivers.tsv, "
                                 "where they carry an owner and an expiry"))
        elif SUPPRESSION.search(tok.string) and not _has_reason(tok.string):
            found.append(Finding(path, line, "QG-CMT-SUPPRESS",
                                 "give this suppression a reason after the code: `# noqa: CODE -- why`"))
    return found
