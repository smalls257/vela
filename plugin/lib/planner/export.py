"""Epics as CSV rows for an issue tracker's import. Pure: the CLI writes the file.

This is an export only. Nothing reads the tracker back, and no page carries a
tracker field, so the vault never depends on one.
"""
import csv
import io
import re
import urllib.parse

from planner import override, trace
from planner.parse import FENCE

EPICS_FOLDER = "13-epics/"
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


def decision_lines(epic):
    """How the epic was decided when the rules were set aside: its overrides and on-behalf
    decisions, page level and items alike, from planner.override's parser. A tracker reader
    sees the same trail the vault carries."""
    lines = []
    for found, behalf in override.decisions(epic):
        lines += [f"Override: {item.describe()}" for item in found]
        if behalf is None:
            continue
        who = f"Decided by {behalf.by} on behalf of {' '.join(behalf.owners)}"
        lines.append(who + (f" (confirmed by {behalf.confirmed_by} on {behalf.confirmed_on})" if behalf.confirmed_by
                            else " (not yet confirmed)"))
    return lines


def handles(owner):
    """The owner field as team names: every handle loses its leading @ (a tracker wants a name, not a mention)."""
    if isinstance(owner, list):
        owner = ", ".join(o for o in owner if isinstance(o, str))
    if not isinstance(owner, str):
        return ""
    return re.sub(r"(^|[\s,;])@", r"\1", owner)


def unloaded(vault):
    """Paths of pages in the epics folder that are neither epics nor the folder index (frontmatter failed to parse, or wrong type)."""
    return sorted(p.path for p in vault.pages if p.path.startswith(EPICS_FOLDER) and p.type not in ("epic", "index"))


def rows(vault, link_for):
    """One row per epic, by ID. `link_for(path)` gives the Vault link for a vault-relative path."""
    out = []
    for epic in trace.epics(vault):
        acs = criteria(epic)
        text = description(epic)
        if acs:
            text += ("\n\n" if text else "") + "Acceptance criteria:\n" + "\n".join(f"{i}. {c}" for i, c in enumerate(acs, start=1))
        trail = decision_lines(epic)
        if trail:
            text += ("\n\n" if text else "") + "\n".join(trail)
        title = epic.meta.get("title")
        name = epic.id or epic.path
        out.append((title if isinstance(title, str) and title.strip() else name, text, name,
                    handles(epic.meta.get("owner")), link_for(epic.path)))
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
    remote = remote.strip().split("#", 1)[0].split("?", 1)[0]
    if re.search(r"\s", remote):
        return ""
    scp = re.match(r"^[\w.-]+@([^:/]+):(.+?)(?:\.git)?/?$", remote)
    if scp:
        return f"https://{scp.group(1)}/{scp.group(2)}"
    # user:token@ never reaches the CSV; an ssh port means nothing on the web host.
    hosted = re.match(r"^(https?|ssh)://(?:[^@/]+@)?([^/:@]+)(?::\d+)?/(.+?)(?:\.git)?/?$", remote)
    if not hosted:
        return ""
    scheme = "http" if hosted.group(1) == "http" else "https"
    port = re.match(r"^https?://(?:[^@/]+@)?[^/:@]+(:\d+)", remote) if hosted.group(1) != "ssh" else None
    return f"{scheme}://{hosted.group(2)}{port.group(1) if port else ''}/{hosted.group(3)}"


def link_path(path):
    return urllib.parse.quote(path, safe="/")
