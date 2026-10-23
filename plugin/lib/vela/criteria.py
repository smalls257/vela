"""An epic's acceptance criteria, in both of the shapes a page may use. Pure: a page in, criteria out.

The Violation this exists to prevent is a Distributed Monolith in miniature: the trace rules, the allocation view, the
explorer's epic panels and QA door, the design's `EPC-nnn.ACn` targets and the ticket export each used to carry their
own copy of "find the numbered lines under the criteria heading". A new shape for the criteria would have meant six
edits and a seventh forgotten. One reader here, and every consumer takes its fields from it.

Two shapes, and a page may hold both (an old epic is rewritten the next time a session touches it):

- **Numbered** (the first shape): numbered lines under `## Epic acceptance criteria`, the concern markers ending the
  sentence, a `- Trace:` line under each. Its AC number is the number as written.

      1. A first call with a client still gets a note. [testing]
         - Trace: CAP-001.FR5, CON-001, FLO-001

- **Headed** (the epic template): under `## Done when`, one `###` heading per criterion, one or two sentences under it,
  and a Trace line that carries the stable AC id and the markers after the IDs, divided by a middle dot.

      ### A first call still gets a note
      A first call with a client still gets a note. It says there is no earlier call and lists who is on the call.
      - Trace: CAP-001.FR5, CON-001, FLO-001  ·  AC1  ·  [testing]

  The AC id is written, not counted, so adding, striking or moving a criterion never renumbers the others, and
  `EPC-001.AC3` keeps meaning the same criterion. More than about seven criteria are grouped: a `###` group heading
  and the criteria one level deeper (`####`). A heading with a deeper heading under it and no Trace line of its own is a
  group; a numbered line under a heading makes that heading a group too, as the first shape always allowed.

On the Trace line, divided by `·`, commas or spaces: vault IDs, then `AC<n>`, then `[marker]` names. Any order reads
the same. A criterion whose heading or sentence starts with `~~` is struck: its number stays taken, and it carries no
marker.
"""
import re
from dataclasses import dataclass

from vela.parse import FENCE, closes_fence
from vela.reading import TRACE_LINE

SECTION = re.compile(r"^##\s+(?P<text>.*?)\s*#*\s*$")
HEADING = re.compile(r"^(?P<hashes>#{3,6})\s+(?P<text>.*?)\s*#*\s*$")
NUMBERED = re.compile(r"^\s*(?P<n>\d+)\.\s+(?P<body>.*?)\s*$")
TRAILING_MARKERS = re.compile(r"^(?P<body>.*?)(?P<markers>(?:\s*(?<!\[)\[[A-Za-z][A-Za-z0-9-]*\](?!\]))+)\.?\s*$")
TRACE_TOKEN = re.compile(r"\[[A-Za-z][A-Za-z0-9-]*\]|[^\s,;·]+")
AC_ID = re.compile(r"^AC(\d+)$", re.I)
CRITERIA_HEADINGS = ("done when",)


@dataclass(frozen=True)
class Criterion:
    n: int  # the AC number: as written (numbered), or on its Trace line (headed)
    line: int  # the line of the numbered sentence, or of the heading
    form: str  # "numbered" or "headed"
    heading: str  # the short heading, "" for a numbered criterion
    text: str  # the sentence, or the one or two sentences under the heading; concern markers taken off
    struck: bool
    markers: tuple  # concern names, lower case: [testing] is "testing"
    trace: tuple  # vault IDs from the Trace line
    declared: bool  # False when a headed criterion's Trace line carries no AC id, so n is its place in the list
    group: str  # the group heading above it, "" when there is none

    @property
    def raw(self):
        """The criterion as one string: the sentence for a numbered one, 'heading. sentences' for a headed one."""
        if not self.heading:
            return self.text
        return f"{self.heading}. {self.text}".strip() if self.text else self.heading


@dataclass(frozen=True)
class Trace:
    ids: tuple
    ac: int  # 0 when the line carries no AC id
    markers: tuple


def is_criteria_heading(text):
    lowered = text.strip().lower()
    return lowered.endswith("acceptance criteria") or lowered in CRITERIA_HEADINGS


def parse_trace(text):
    """A Trace line's content (what follows `Trace:`) as vault IDs, the AC id and the concern markers."""
    ids, ac, markers = [], 0, []
    for token in TRACE_TOKEN.findall(text):
        found = AC_ID.match(token)
        if token.startswith("["):
            markers.append(token[1:-1].lower())
        elif found:
            ac = int(found.group(1))
        else:
            ids.append(token)
    return Trace(tuple(ids), ac, tuple(markers))


def _section_lines(page):
    """(line number, text) for each line under a criteria `##` heading, outside code fences and generated blocks."""
    skip = set()
    for block in page.blocks:
        skip.update(range(block.start, block.end + 1))
    out, fence, inside = [], None, False
    for n, raw in enumerate(page.text.split("\n"), start=1):
        opening = FENCE.match(raw)
        if fence:
            if closes_fence(raw, fence):
                fence = None
            continue
        if opening:
            fence = opening.group(1)
            continue
        if n in skip:
            continue
        section = SECTION.match(raw)
        if section:
            inside = is_criteria_heading(section["text"])
            continue
        if inside:
            out.append((n, raw))
    return out


def _blocks(lines):
    """[(heading line, level, text, [(n, raw)...])]: the lines before the first heading come first, with level 0."""
    blocks = [(0, 0, "", [])]
    for n, raw in lines:
        found = HEADING.match(raw)
        if found:
            blocks.append((n, len(found["hashes"]), found["text"], []))
        else:
            blocks[-1][3].append((n, raw))
    return blocks


def _numbered(lines, group):
    """The numbered criteria among `lines`, each with the Trace line under it."""
    out = []
    for n, raw in lines:
        found = NUMBERED.match(raw)
        if found:
            body = found["body"]
            marked = TRAILING_MARKERS.match(body)
            text, markers = (marked["body"], marked["markers"]) if marked else (body, "")
            struck = body.lstrip().startswith("~~")
            out.append({"n": int(found["n"]), "line": n, "text": text.strip(), "struck": struck,
                        "markers": [m.lower() for m in re.findall(r"\[([^\]]+)\]", markers)], "trace": (), "group": group})
        elif out and TRACE_LINE.match(raw):
            parts = parse_trace(TRACE_LINE.match(raw)["ids"])
            out[-1]["trace"] = parts.ids
            out[-1]["markers"] += [m for m in parts.markers if m not in out[-1]["markers"]]
    return [Criterion(c["n"], c["line"], "numbered", "", c["text"], c["struck"], () if c["struck"] else tuple(c["markers"]),
                      c["trace"], True, c["group"]) for c in out]


def read(page):
    """Every criterion of the page, both shapes, in page order, struck ones included (their numbers stay taken)."""
    blocks = _blocks(_section_lines(page))
    out, group, group_level = _numbered(blocks[0][3], ""), "", 0
    headed = []
    for i, (n, level, text, lines) in enumerate(blocks[1:], start=1):
        numbered = _numbered(lines, text)
        trace_at = next((TRACE_LINE.match(raw) for _, raw in lines if TRACE_LINE.match(raw)), None)
        deeper = i + 1 < len(blocks) and blocks[i + 1][1] > level
        if group and level <= group_level:
            group = ""
        if numbered or (not trace_at and deeper):
            out += numbered
            group, group_level = text, level
            continue
        body = " ".join(raw.strip() for _, raw in lines if raw.strip() and not TRACE_LINE.match(raw))
        if not trace_at and not body:
            continue  # an empty heading says nothing
        parts = parse_trace(trace_at["ids"]) if trace_at else Trace((), 0, ())
        struck = text.lstrip().startswith("~~") or body.lstrip().startswith("~~")
        headed.append((n, text.lstrip("~ ").rstrip("~ ") if struck else text, body, struck, parts, group))
    taken = [c.n for c in out] + [p.ac for *_, p, _ in headed if p.ac]
    for n, heading, body, struck, parts, group_name in headed:
        number = parts.ac
        if not number:  # no AC id written: the next number not taken, and problems() says so
            number = len(out) + 1
            while number in taken:
                number += 1
            taken.append(number)
        out.append(_headed(number, parts.ac > 0, n, heading, body, struck, parts, group_name))
    return sorted(out, key=lambda c: c.line)


def _headed(number, declared, line, heading, body, struck, parts, group):
    marked = TRAILING_MARKERS.match(body)
    markers = list(parts.markers) + ([m.lower() for m in re.findall(r"\[([^\]]+)\]", marked["markers"])] if marked else [])
    return Criterion(number, line, "headed", heading, (marked["body"] if marked else body).strip(), struck,
                     () if struck else tuple(dict.fromkeys(markers)), parts.ids, declared, group)


def numbers(page):
    """The AC numbers a reference such as EPC-001.AC3 may name on this page."""
    return [c.n for c in read(page)]


def problems(page):
    """(line, message) for each headed criterion whose AC id is missing, repeated, or taken by a numbered line."""
    seen, out = {}, []
    for c in read(page):
        if c.form == "headed" and not c.declared:
            out.append((c.line, f"The criterion '{c.heading}' has no AC id on its Trace line, so nothing can refer to it by number."))
        if c.n in seen:
            out.append((c.line, f"AC{c.n} is on two criteria, '{seen[c.n] or 'a numbered one'}' and '{c.heading or 'a numbered one'}'."))
        seen.setdefault(c.n, c.heading)
    return out
