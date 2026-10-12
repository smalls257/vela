"""Protected tokens before and after a prose rewrite. Pure: the CLI reads the two texts.

A voice rewrite may change words. It may not change what the words point at: IDs,
numbers, dates, versions, links, code spans, table cells, frontmatter and negations. If any of them is missing,
added or moved, the rewrite fails, and close keeps the earlier draft.
"""
import re
from collections import Counter
from dataclasses import dataclass
from planner.parse import protect_link_pipes

CODE_SPAN = re.compile(r"``[^\n]+?``|`[^`\n]+`")
WIKILINK = re.compile(r"!?\[\[[^\]\n]+?\]\]")
LINK_URL = re.compile(r"(?<=\])\([^)\s]+\)")
BARE_URL = re.compile(r"https?://[^\s<>)\]]*[^\s<>)\].,;:!?]")
DATE = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?(?![\w-])")
VERSION = re.compile(r"(?<![\w.-])[vV]\d+(?:\.\d+)*(?![\w-])")
# Any CAPS-nnn ID counts, so an ID prefix added to schema.py later is protected without a change here.
ID = re.compile(r"(?<![\w-])(?:(?:APP|RUN)-[a-z0-9]+(?:-[a-z0-9]+)*|VX-[a-z-]+-\d{3}|concern-[a-z0-9]+(?:-[a-z0-9]+)*"
                r"|[A-Z][A-Z0-9]*-\d+(?:\.[A-Za-z]*\d+)*|G\d+(?:\.[A-Za-z]*\d+)*)(?![\w])")
UNIT = r"(?i:ms|s|secs?|seconds?|mins?|minutes?|h|hrs?|hours?|days?|weeks?|months?|years?|[kmgt]b|x)"
CURRENCY = "£$€¥"
# A number keeps its currency symbol, its sign and the unit that follows it ("10 ms", "10ms", "5xx", "3rd").
NUMBER = re.compile(rf"(?:[{CURRENCY}]|(?<![\w.,])(?:[-+−~≈](?=[{CURRENCY}]?\d))?[{CURRENCY}]?)"
                    rf"\d+(?:[.,]\d+)*(?:%|[A-Za-z_]\w*|\s?{UNIT}\b)?")
WORD_WITH_DIGIT = re.compile(r"(?<![\w.,])[A-Za-z_]+\d\w*")  # HTTP2, p99, S3, a block ID or a short hash
TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
LEADING_MARKER = re.compile(r"^[ \t]*(?:>[ \t]*)*(?:(?:[-*+]|\d+[.)])[ \t]+|#{1,6}[ \t]+(?:(?:\d+(?:\.\d+)+\.?|\d+\.)[ \t]+)?)*")
NEGATION = re.compile(r"\b(?:not|no|never|cannot|without|nobody|nothing|none|nor|neither|nowhere|\w+n't)\b")
KINDS = ((CODE_SPAN, "code"), (WIKILINK, "link"), (LINK_URL, "link"), (BARE_URL, "link"), (DATE, "date"),
         (VERSION, "version"), (ID, "id"), (NUMBER, "number"), (WORD_WITH_DIGIT, "number"))


@dataclass(frozen=True)
class Token:
    kind: str  # link, code, date, version, id, number, cell or frontmatter
    text: str
    line: int


@dataclass(frozen=True)
class Result:
    missing: tuple  # Tokens in the before text with no partner after
    added: tuple  # Tokens in the after text with no partner before
    moved: tuple  # (before Token, after Token) at the first place the shared tokens part order
    negation: tuple = ()  # ((before count, after count),) when the negation words of the whole file changed

    @property
    def same(self):
        return not (self.missing or self.added or self.moved or self.negation)


def cells(line):
    body = line.strip().strip("|")
    return [c.strip().replace("\x00", "|") for c in protect_link_pipes(body.replace("\\|", "\x00")).split("|")]


def normalised_lines(text):
    return text.replace("\r\n", "\n").split("\n")


def frontmatter_length(lines):
    """Number of lines the opening `---` block takes, or 0 when the text has none."""
    if not lines or lines[0].rstrip() != "---":
        return 0
    for n, line in enumerate(lines[1:], start=2):
        if line.rstrip() == "---":
            return n
    return 0


def strip_marker(line):
    """A list marker or heading number is layout. Blank it out so it is not read as a number."""
    marker = LEADING_MARKER.match(line).group(0)
    return " " * len(marker) + line[len(marker):]


def line_tokens(line, n):
    """Tokens of one prose line in column order. Each kind is masked before the next is read."""
    spans, masked = [], strip_marker(line)
    for pattern, kind in KINDS:
        for match in pattern.finditer(masked):
            text = re.sub(r"\s+", " ", match.group(0)) if kind == "number" else match.group(0)
            spans.append((match.start(), Token(kind, text, n)))
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    return [token for _, token in sorted(spans, key=lambda s: s[0])]


def tokens(text):
    """Protected tokens in document order. Frontmatter gives one token per line. A table row
    gives one token per cell and nothing else."""
    lines = normalised_lines(text)
    skip = frontmatter_length(lines)
    found = [Token("frontmatter", line, n) for n, line in enumerate(lines[:skip], start=1)]
    for n, line in enumerate(lines[skip:], start=skip + 1):
        if line.lstrip().startswith("|"):
            if not TABLE_SEPARATOR.match(line.strip()):
                found.extend(Token("cell", c.replace("\x00", "|"), n) for c in cells(line))
            continue
        found.extend(line_tokens(line, n))
    return found


def negations(text):
    """Number of negation words in the prose of a text. n't counts as not. The count is for the
    whole file, so splitting, merging or moving paragraphs does not change it."""
    lines = normalised_lines(text)
    total = 0
    for line in lines[frontmatter_length(lines):]:
        if line.lstrip().startswith("|"):
            continue
        prose = line.lower().replace("\u2019", "'")
        for pattern, _ in KINDS[:4]:  # words inside code spans, links and URLs are not prose
            prose = pattern.sub(" ", prose)
        total += len(NEGATION.findall(prose))
    return total


class NotRedundant(ValueError):
    """A sentence named as redundant is not in the text before the rewrite, or is still in the text after it."""


def removed_sentences(before, after, named):
    """The sentences the reviewer named as redundant, each checked: it must stand in the text before (spaces and line
    breaks do not count) and be gone from the text after. A name that fails either would excuse a negation nobody
    removed, so it is an error and never a quiet pass."""
    flat = lambda text: re.sub(r"\s+", " ", text)
    for sentence in named:
        wanted = flat(sentence).strip()
        if not wanted or wanted not in flat(before):
            raise NotRedundant(f"'{sentence}' is not in the text before the rewrite, so it cannot have been removed.")
        if wanted in flat(after):
            raise NotRedundant(f"'{sentence}' is still in the text after the rewrite, so nothing was removed.")
    return [re.sub(r"\s+", " ", s).strip() for s in named]


def negation_changes(before, after, named=()):
    """The negation counts before and after, when they differ. A sentence the reviewer named as redundant takes its
    own negation words out of the count before: the claim it made stands elsewhere, which the reviewer said. Its IDs,
    numbers and links still have to survive in the after text, so a sentence that carried a fact cannot be excused."""
    gone = sum(negations(sentence) for sentence in removed_sentences(before, after, named))
    a, b = negations(before) - gone, negations(after)
    return ((a, b),) if a != b else ()


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


def compare(before, after, redundant=()):
    """`redundant` is the sentences a reviewer named as already said elsewhere; a rewrite may drop their negations."""
    a, b = tokens(before), tokens(after)
    keep = Counter((t.kind, t.text) for t in a) & Counter((t.kind, t.text) for t in b)
    common_a, common_b = shared(a, keep), shared(b, keep)
    moved = next(((x, y) for x, y in zip(common_a, common_b) if (x.kind, x.text) != (y.kind, y.text)), None)
    return Result(leftover(a, b), leftover(b, a), (moved,) if moved else (), negation_changes(before, after, redundant))


def describe(result):
    lines = [f"missing: {t.text} ({t.kind}), before line {t.line}" for t in result.missing]
    lines += [f"added: {t.text} ({t.kind}), after line {t.line}" for t in result.added]
    lines += [f"moved: {x.text} ({x.kind}) at before line {x.line} now has {y.text} ({y.kind}) in its place, after line {y.line}"
              for x, y in result.moved]
    lines += [f"negation: {x} negation words before, {y} after (negation)" for x, y in result.negation]
    return lines
