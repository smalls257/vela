"""How far each prose paragraph sits from the owner's voice, measured with a style embedding.
Pure: the CLI reads the files, owns the model and the cache, and hands in an `embed` callable.

This is information for the drafter and the voice reviewer, never a gate. The voice reviewer is
an LLM judging LLM output; a style embedding is a second reading of a different kind, so it can
see drift the reviewer cannot (docs/research/2026-10-06-voice-models.md). Per-paragraph scores
on short text are noisy, so a paragraph is placed against the owner's own spread, never against
a fixed threshold, and never reported as a bare number.
"""
import hashlib
import math
import re
from dataclasses import dataclass

import yaml

from planner import parse, voicecheck

# StyleDistance (NAACL 2025): MIT, RoBERTa-base, one text in, one vector out, trained to ignore
# content, and it needs no trust_remote_code. The revision is pinned so a model update upstream
# can never change scores silently; bump it on purpose, and the cache key moves with it.
MODEL_ID = "StyleDistance/styledistance"
MODEL_REVISION = "b7df5f0b0480773c097ba3121d83ca32b71015ca"
MODEL_SIZE = "about 0.5 GB"
DEPENDENCY_SIZE = "it pulls in PyTorch, about 1–2 GB"
INSTALL_HINT = f"python3 -m pip install sentence-transformers ({DEPENDENCY_SIZE})"

# TinyStyler and LUAR both build a reference from about 16 texts. Fewer than 5 gives a range
# so coarse that one odd example decides it, so below this the score is flagged unreliable.
MIN_RELIABLE = 5
MIN_TO_SCORE = 2  # leave-one-out needs at least one other example to form a centroid
# Inside the range means no farther from the centroid than 90% of the owner's own examples are
# from theirs. One owner example in ten lands outside by design: this is a spread, not a gate.
INSIDE_UP_TO = 90

OWNER_SOURCES = ("owner", "owner-edit")
SEED_SOURCE = "public-seed"
AGAINST = ("owner", "seed")

FENCE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
LABEL_LINE = re.compile(r"^\s*\*\*[^*\n]+:\*\*")  # **Decision:**, **Owner:**, **Last session:**
BLOCK_ID = re.compile(r"\s+\^[A-Za-z0-9-]+\s*$")


class NotScorable(Exception):
    """The reference is too thin, or the input holds no prose. The CLI exits 2 with this message."""


@dataclass(frozen=True)
class Example:
    id: str
    folder: str  # "examples" or "local"
    source: str
    state: str
    text: str


@dataclass(frozen=True)
class Paragraph:
    number: int  # ¶ number, from 1, in file order
    line: int  # first line in the file, from 1
    text: str


@dataclass(frozen=True)
class Reference:
    against: str  # "owner" or "seed"
    examples: tuple
    warning: str  # "" when the reference is reliable

    @property
    def range_name(self):
        return "your range" if self.against == "owner" else "the seed's range"

    @property
    def described(self):
        if self.against == "owner":
            return f"your voice ({len(self.examples)} owner examples)"
        return f"the public seed, not your voice ({len(self.examples)} public-seed examples)"


@dataclass(frozen=True)
class Placement:
    percentile: int  # 0 to 100, against the leave-one-out range; 101 means beyond its widest
    inside: bool
    label: str
    distance: float  # cosine distance to the centroid; for JSON readers, never printed alone

    @property
    def shown(self):
        return "p100+" if self.percentile > 100 else f"p{self.percentile}"


@dataclass(frozen=True)
class Scored:
    paragraph: Paragraph
    placement: Placement


# --- examples -------------------------------------------------------------------------------

def read_example(folder, text):
    """An Example from a voice file's text, or None when its frontmatter cannot be read.
    The CLI reports the None ones, so a broken example is never dropped silently."""
    lines = voicecheck.normalised_lines(text)
    length = voicecheck.frontmatter_length(lines)
    if not length:
        return None
    try:
        meta = yaml.safe_load("\n".join(lines[1:length - 1])) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    body = "\n".join(lines[length:]).strip()
    return Example(str(meta.get("id", "")), folder, str(meta.get("source", "")), str(meta.get("state", "")), body)


def reference(examples, against="owner"):
    """The examples to measure against. The owner's active examples by default. The public seed
    only when asked for by name: falling back to it would score the owner against someone else's
    voice and call it theirs."""
    if against not in AGAINST:
        raise ValueError(f"against must be one of {AGAINST}, not {against!r}")
    wanted = OWNER_SOURCES if against == "owner" else (SEED_SOURCE,)
    chosen = tuple(sorted((e for e in examples if e.state == "active" and e.source in wanted and e.text),
                          key=lambda e: (e.folder != "local", e.id)))
    who = "owner" if against == "owner" else "public-seed"
    if len(chosen) < MIN_TO_SCORE:
        hint = (" `/planner:voice-seed` adds them. `--against seed` scores against the public seed instead, labelled as such."
                if against == "owner" else "")
        raise NotScorable(f"{len(chosen)} active {who} examples in voice/examples/ and voice/local/; "
                          f"at least {MIN_TO_SCORE} are needed to score and {MIN_RELIABLE} to trust it.{hint}")
    warning = ""
    if len(chosen) < MIN_RELIABLE:
        warning = (f"UNRELIABLE: only {len(chosen)} active {who} examples, and a range needs at least {MIN_RELIABLE}. "
                   f"Read every placement below as a rough hint.")
    return Reference(against, chosen, warning)


# --- paragraphs -----------------------------------------------------------------------------

def prose_lines(text):
    """(line number, line) for every line that may hold voiced prose, with "" standing in for each
    line that may not, so paragraphs never join across a skipped table, list or block."""
    lines = voicecheck.normalised_lines(text)
    start = voicecheck.frontmatter_length(lines)
    out, fenced, generated = [], False, False
    for n, line in enumerate(lines[start:], start=start + 1):
        if FENCE.match(line):
            fenced = not fenced
            out.append((n, ""))
            continue
        if parse.MARKER_ANY.match(line):
            generated = not line.lstrip().startswith("<!-- /")
            out.append((n, ""))
            continue
        if fenced or generated or not is_prose(line):
            out.append((n, ""))
            continue
        out.append((n, BLOCK_ID.sub("", line).strip()))
    return out


def is_prose(line):
    stripped = line.strip()
    return bool(stripped) and not (
        stripped.startswith(("#", "|", ">", "<!--", "![[", "---"))  # headings, tables, quotes, comments, embeds, rules
        or LIST_ITEM.match(line)  # every bullet: fact bullets carry labels, the rest are link lists
        or LABEL_LINE.match(line)
        or line.startswith(("    ", "\t"))  # indented code, or a list item's continuation
    )


def paragraphs(text):
    """The prose paragraphs of a page, in order. Frontmatter, headings, tables, code, generated
    blocks, quotes, list items and labelled lines are never voiced, so they are never scored."""
    found, current, first = [], [], 0
    for n, line in prose_lines(text) + [(0, "")]:
        if line:
            first = first or n
            current.append(line)
            continue
        if current:
            found.append(Paragraph(len(found) + 1, first, " ".join(current)))
        current, first = [], 0
    return found


def candidate_text(text):
    """The prose of one candidate draft, its paragraphs joined, for --rank."""
    return "\n\n".join(p.text for p in paragraphs(text))


# --- the cache key --------------------------------------------------------------------------

def cache_key(text, model_id=MODEL_ID, revision=MODEL_REVISION):
    """A vector depends on the text and on the exact model, so both go in the key: a pinned
    revision bump must miss the cache, not serve vectors from the old model."""
    return hashlib.sha256(f"{model_id}@{revision}\n{text}".encode("utf-8")).hexdigest()


# --- the range ------------------------------------------------------------------------------

def centroid(vectors):
    size = len(vectors)
    return [sum(column) / size for column in zip(*vectors)]


def cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        raise NotScorable("the embedder returned a zero vector, so no distance can be measured")
    return 1.0 - dot / norm


def leave_one_out(vectors):
    """Each example's distance to the centroid of the others, sorted. A new paragraph is never
    part of the centroid it is measured against, so the owner's examples are measured the same way."""
    return sorted(cosine_distance(v, centroid(vectors[:i] + vectors[i + 1:])) for i, v in enumerate(vectors))


def percentile(distance, spread):
    """Where a distance falls in the sorted leave-one-out spread, 0 to 100, interpolated between
    neighbours. Past the widest example it is 101, shown as p100+."""
    if distance <= spread[0]:
        return 0
    if distance > spread[-1]:
        return 101
    for i in range(1, len(spread)):
        low, high = spread[i - 1], spread[i]
        if distance <= high:
            within = (distance - low) / (high - low) if high > low else 1.0
            return round((i - 1 + within) / (len(spread) - 1) * 100)
    return 100


def place(distance, spread, range_name="your range"):
    p = percentile(distance, spread)
    inside = p <= INSIDE_UP_TO
    label = f"inside {range_name}" if inside else f"outside {range_name} ({'p100+' if p > 100 else f'p{p}'})"
    return Placement(p, inside, label, distance)


# --- scoring --------------------------------------------------------------------------------

@dataclass(frozen=True)
class Measure:
    """The reference embedded once: its centroid and its own spread."""
    reference: Reference
    centre: list
    spread: list

    def place(self, vector):
        return place(cosine_distance(vector, self.centre), self.spread, self.reference.range_name)


def measure(ref, embed):
    vectors = [list(v) for v in embed([e.text for e in ref.examples])]
    return Measure(ref, centroid(vectors), leave_one_out(vectors))


def score(text, ref, embed):
    """[Scored] for each prose paragraph of a page."""
    found = paragraphs(text)
    if not found:
        raise NotScorable("the file holds no prose paragraph to score (headings, tables, lists, code and generated blocks are skipped)")
    m = measure(ref, embed)
    vectors = embed([p.text for p in found])
    return [Scored(p, m.place(v)) for p, v in zip(found, vectors)]


def rank(candidates, ref, embed):
    """[(name, Placement)] closest to the reference first. `candidates` is [(name, text)] of
    drafts of the same paragraph. Ties keep the order given."""
    texts = [(name, candidate_text(text)) for name, text in candidates]
    empty = [name for name, text in texts if not text]
    if empty:
        raise NotScorable(f"no prose paragraph in {', '.join(empty)}")
    m = measure(ref, embed)
    vectors = embed([text for _, text in texts])
    placed = [(name, m.place(v)) for (name, _), v in zip(texts, vectors)]
    return sorted(placed, key=lambda pair: pair[1].distance)


def summary(scored, range_name="your range"):
    """One line for the PR body: "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p96)"."""
    inside = sum(1 for s in scored if s.placement.inside)
    line = f"voicescore: {inside} of {len(scored)} paragraphs inside {range_name}"
    outside = [f"¶{s.paragraph.number} outside ({s.placement.shown})" for s in scored if not s.placement.inside]
    return line + ("; " + ", ".join(outside) if outside else "")
