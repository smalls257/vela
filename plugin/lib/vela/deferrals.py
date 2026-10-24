"""Prose that leaves a matter for a later Grill. Pure: a page's text in, the lines that defer out.

The Violation this exists to prevent is a Silent Fallback at process level: the record says "later" and nothing ever
asks. A deferral is only honest while an open question with an owner and an ask-by date carries it, so a page that
says "left for a Grill" must link one.
"""
import re

LEFT = r"(?:left|leave|leaves|leaving|saved|parked|deferred|pushed|kept|held)"
DEFERS = re.compile(
    rf"\b{LEFT}\b[^.\n]{{0,50}}\bgrill\b"
    r"|\bfor (?:a|the|next|another|that) (?:later |next )?grill\b"
    r"|\b(?:a|the|next) grill\s+(?:will|should|can|must|to)\s+(?:decide|settle|confirm|resolve|answer)\b"
    r"|\bsettle (?:it |this |that )?later\b"
    r"|\b(?:to be )?(?:decided|settled|confirmed|resolved|answered) (?:later|in a grill|at a grill|by a grill|in the next grill)\b",
    re.IGNORECASE)
UNKNOWN_TOKEN = re.compile(r"\bUNK-\d{3}\b")


def paragraph_of(lines, number):
    """(first, last) 1-based line numbers of the run of non-blank lines holding line `number`."""
    first = last = number
    while first > 1 and lines[first - 2].strip():
        first -= 1
    while last < len(lines) and lines[last].strip():
        last += 1
    return first, last


def prose_lines(page, history_heading):
    """Line numbers outside fences, generated blocks and the page's History."""
    skip, fenced, generated = set(), False, False
    history = next((n for n, l in enumerate(page.text.split("\n"), 1) if l.strip().lower() == f"## {history_heading.lower()}"), None)
    for n, line in enumerate(page.text.split("\n"), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if line.startswith("<!-- generated:"):
            generated = True
        if fenced or generated or (history is not None and n >= history) or line.startswith("<!--"):
            skip.add(n)
        if line.startswith("<!-- /generated:"):
            generated = False
    return skip


def deferrals(page, history_heading, open_unknowns):
    """(line, phrase) for each line that leaves a matter for a Grill with no open unknown linked in its paragraph."""
    lines = page.text.split("\n")
    skip = prose_lines(page, history_heading)
    found = []
    for n, line in enumerate(lines, 1):
        match = DEFERS.search(line) if n not in skip else None
        if not match:
            continue
        first, last = paragraph_of(lines, n)
        text = "\n".join(lines[first - 1:last])
        if not any(token in open_unknowns for token in UNKNOWN_TOKEN.findall(text)):
            found.append((n, match.group(0)))
    return found
