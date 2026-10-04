"""Epics as CSV rows for an issue tracker's import. Pure: the CLI writes the file.

This is an export only. Nothing reads the tracker back, and no page carries a
tracker field, so the vault never depends on one.
"""
import csv
import io
import re

from planner import trace
from planner.parse import FENCE

COLUMNS = ("Summary", "Description", "Epic Name", "Owner team", "Vault link")
WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
LABEL_LINE = re.compile(r"^(- )?\*\*[^*]+:\*\*")
NUMBERED = re.compile(r"^\s*\d+\.\s+")
FORMULA_LEADS = ("=", "+", "-", "@", "\t", "\r")


def plain(text):
    """Wikilinks become their label, or their target when they have none."""
    def label(match):
        inner = match.group(1).replace("\\|", "|")
        target, _, alias = inner.partition("|")
        return alias.strip() or target.split("#", 1)[-1].strip() or target.strip()
    return WIKILINK.sub(label, text)


def body_lines(epic):
    """(line, in acceptance criteria) for each body line outside fences and generated blocks,
    with the heading text it sits under."""
    skip = set()
    for block in epic.blocks:
        skip.update(range(block.start, block.end + 1))
    lines = epic.text.split("\n")
    start = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), 0) + 1
    fence, section = None, ""
    for n, raw in enumerate(lines[start:], start=start + 1):
        if fence:
            if raw.strip().startswith(fence):
                fence = None
            continue
        opening = FENCE.match(raw)
        if opening:
            fence = opening.group(1)
            continue
        if n in skip:
            continue
        heading = trace.SECTION_HEADING.match(raw)
        if heading:
            section = heading["text"].strip().lower()
            continue
        yield raw, section


def description(epic):
    """The paragraphs between the title and the first ## heading, without fact or label lines."""
    paragraphs, current = [], []
    for raw, section in body_lines(epic):
        if section:
            break
        line = raw.strip()
        if not line or line.startswith("#") or LABEL_LINE.match(line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(plain(p) for p in paragraphs)


def criteria(epic):
    """The numbered acceptance criteria as written, struck ones left out."""
    found = []
    for raw, section in body_lines(epic):
        if section.endswith("acceptance criteria") and NUMBERED.match(raw):
            body = NUMBERED.sub("", raw, count=1).strip()
            if not body.startswith("~~"):
                found.append(plain(body))
    return found


def rows(vault, link_for):
    """One row per epic, by ID. `link_for(path)` gives the Vault link for a vault-relative path."""
    out = []
    for epic in trace.epics(vault):
        acs = criteria(epic)
        text = description(epic)
        if acs:
            text += ("\n\n" if text else "") + "Acceptance criteria:\n" + "\n".join(f"{i}. {c}" for i, c in enumerate(acs, start=1))
        title = epic.meta.get("title")
        owner = epic.meta.get("owner")
        out.append((title if isinstance(title, str) else epic.id, text, epic.id,
                    owner if isinstance(owner, str) else "", link_for(epic.path)))
    return out


def defuse(cell):
    """A spreadsheet reads a cell that opens with = + - @ tab or CR as a formula; a leading ' makes it text."""
    return "'" + cell if cell.startswith(FORMULA_LEADS) else cell


def to_csv(table):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    writer.writerows([defuse(cell) for cell in row] for row in table)
    return buffer.getvalue()


def web_url(remote):
    """A browsable https URL for a git remote, or "" when it cannot be made one."""
    remote = remote.strip()
    ssh = re.match(r"^git@([^:]+):(.+?)(?:\.git)?/?$", remote)
    if ssh:
        return f"https://{ssh.group(1)}/{ssh.group(2)}"
    https = re.match(r"^(https?://[^\s]+?)(?:\.git)?/?$", remote)
    return https.group(1) if https else ""
