"""Protected tokens before and after a prose rewrite. Pure: the CLI reads the two texts.

A voice rewrite may change words. It may not change what the words point at: IDs,
numbers, dates, wikilinks, code spans and table cells. If any of them is missing,
added or moved, the rewrite fails, and close keeps the earlier draft.
"""
import re
from collections import Counter
from dataclasses import dataclass

WIKILINK = re.compile(r"\[\[[^\]\n]+?\]\]")
CODE_SPAN = re.compile(r"`[^`\n]+`")
DATE = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?![\w-])")
ID = re.compile(r"(?<![\w-])(?:(?:APP|RUN)-[a-z0-9]+(?:-[a-z0-9]+)*|(?:CON|UNK|FLO|EPC|CAP)-\d{3}(?:\.FR\d+)?|ADR-\d{4}"
                r"|R-\d{2,}|SRC-\d{2,}|CST-\d+|INI-\d{3}|VX-[a-z-]+-\d{3}|G\d+|concern-[a-z0-9]+(?:-[a-z0-9]+)*)(?![\w-])")
NUMBER = re.compile(r"(?<![\w.,-])\d+(?:[.,]\d+)*%?(?![\w])")
TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
KINDS = ((WIKILINK, "link"), (CODE_SPAN, "code"), (DATE, "date"), (ID, "id"), (NUMBER, "number"))


@dataclass(frozen=True)
class Token:
    kind: str  # link, code, date, id, number or cell
    text: str
    line: int


@dataclass(frozen=True)
class Result:
    missing: tuple  # Tokens in the before text with no partner after
    added: tuple  # Tokens in the after text with no partner before
    moved: tuple  # (before Token, after Token) at the first place the shared tokens part order

    @property
    def same(self):
        return not (self.missing or self.added or self.moved)


def cells(line):
    body = line.strip().strip("|")
    return [c.strip() for c in body.replace("\\|", "\x00").split("|")]


def tokens(text):
    """Protected tokens in document order. A table row gives one token per cell and nothing else."""
    found = []
    for n, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        if line.lstrip().startswith("|"):
            if not TABLE_SEPARATOR.match(line.strip()):
                found.extend(Token("cell", c.replace("\x00", "|"), n) for c in cells(line))
            continue
        spans, masked = [], line
        for pattern, kind in KINDS:
            for match in pattern.finditer(masked):
                spans.append((match.start(), Token(kind, match.group(0), n)))
            masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
        found.extend(token for _, token in sorted(spans, key=lambda s: s[0]))
    return found


def shared(sequence, keep):
    left, out = Counter(keep), []
    for token in sequence:
        key = (token.kind, token.text)
        if left[key] > 0:
            left[key] -= 1
            out.append(token)
    return out


def leftover(sequence, other):
    extra = Counter((t.kind, t.text) for t in sequence) - Counter((t.kind, t.text) for t in other)
    out = []
    for token in reversed(sequence):  # the last copies are the ones without a partner
        key = (token.kind, token.text)
        if extra[key] > 0:
            extra[key] -= 1
            out.append(token)
    return tuple(reversed(out))


def compare(before, after):
    a, b = tokens(before), tokens(after)
    keep = Counter((t.kind, t.text) for t in a) & Counter((t.kind, t.text) for t in b)
    common_a, common_b = shared(a, keep), shared(b, keep)
    moved = next(((x, y) for x, y in zip(common_a, common_b) if (x.kind, x.text) != (y.kind, y.text)), None)
    return Result(leftover(a, b), leftover(b, a), (moved,) if moved else ())


def describe(result):
    lines = [f"missing: {t.text} ({t.kind}), before line {t.line}" for t in result.missing]
    lines += [f"added: {t.text} ({t.kind}), after line {t.line}" for t in result.added]
    lines += [f"moved: {x.text} ({x.kind}) at before line {x.line} now has {y.text} ({y.kind}) in its place, after line {y.line}"
              for x, y in result.moved]
    return lines
