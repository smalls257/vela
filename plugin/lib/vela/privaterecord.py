"""The two session files and the one reference form that points from the plan into them.

The Violation this exists to prevent is a Distributed Monolith: one ID shape (`<id>`, a part, `c07`) spread over
fourteen parsers, so that changing it means editing every one of them. Every reader and writer of the stub, the
private file and a capture reference goes through here.

A session is two files. The stub (`sessions/<id>.md`) is committed and carries only the header: id, modes, status,
the item IDs waiting for a decision, and a fingerprint per part. The private file (`sessions/private/<id>.md`)
holds every word and stays on one machine. Inside a private file a capture is still `^cNN`; the part appears only
in the committed references, `[[<id>]] c07` or `[[<id>]] 2.c07`. The private file knows which part it is, but a
reference lives in the plan, where `c07` alone would be ambiguous across parts, and the file it points into is not
there to ask.

The ready-entry grammar and the decline line are defined here; the modules that read them import them from this
one. Only `vela.parse` is imported besides the standard library, so there is no cycle.
"""
import hashlib
import json
import re
from dataclasses import dataclass

from vela import parse

PRIVATE_DIR = "sessions/private"
PENDING = "pending"
LISTS = ("ready", "challenges", "harvest_declined")
STUB_KEYS = ("id", "type", "title", "date", "modes", "status", "branch", "start_commit", "captures_sha256",
             "ready", "challenges", "harvest_declined", "title_override")
READY_HEADING = "Ready to decide"
READY_LINE = re.compile(r"^- (?P<id>\S+): the lead said yes in (?P<session>\S+)(?: \((?P<yes>\^c\d+)\))?\s*$")
DECLINE = re.compile(r"^Harvest declined: PR (?P<pr>\d+) (?P<page>.+) (?P<hash>[0-9a-f]{12})\s*$")
DECLINE_PREFIX = "Harvest declined: "
CHALLENGE_TITLE = re.compile(r"^Challenge:\s*(?P<id>\S+)")
CITATION = re.compile(r"\[\[(?P<record>[^\]#|]+)\]\] (?P<ref>(?:\d+\.)?c\d+)\b")
ANCHOR_LINK = re.compile(r"\[\[(?P<record>\d{4}-\d{2}-\d{2}-[^\]#|\\]+)#\^c(?P<n>\d+)(?:\\?\|[^\]]*)?\]\]")
_REF = re.compile(r"(?:(\d+)\.)?c(\d+)")
_NEW_RECORD_TABLE = "## Captures\n\n## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"


# ---- paths -------------------------------------------------------------------------------------------------------

def stub_path(record_id):
    return f"sessions/{record_id}.md"


def private_path(record_id):
    return f"{PRIVATE_DIR}/{record_id}.md"


def is_private(rel):
    """True for a path with `sessions/private` in it at any depth and in any case: the guard must not be beaten by a
    nested plan folder or a capital letter."""
    names = [p.lower() for p in re.split(r"[\\/]+", rel) if p]
    return any(a == "sessions" and b == "private" for a, b in zip(names, names[1:]))


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- frontmatter: read by parse.split_frontmatter, written in one fixed shape ------------------------------------

def _read(text):
    """(meta, body): the frontmatter as a dict and everything after the closing `---`. The one place a reader
    meets a bad header, so every caller gets the same ValueError."""
    meta, body_line, error = parse.split_frontmatter(text)
    if error is not None:
        raise ValueError(f"unreadable session frontmatter: {error.message}")
    return meta, "\n".join(parse.lines_of(text)[body_line - 1:])


def _encode(key, value):
    if key == "modes":
        return "[" + ", ".join(str(m) for m in value) + "]"
    if key == "captures_sha256":
        return "{" + ", ".join(f"{part}: {json.dumps(v)}" for part, v in sorted(value.items())) + "}"
    if key in ("id", "type", "date", "status", "part"):
        return str(value)
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(list(value) if isinstance(value, tuple) else value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _assemble(meta, body=""):
    """The frontmatter in the stub's key order (keys this module doesn't know follow, in the order given), then body."""
    rank = {key: i for i, key in enumerate(STUB_KEYS)}
    ordered = sorted(enumerate(meta), key=lambda ik: (rank.get(ik[1], len(rank)), ik[0]))
    head = "".join(f"{key}: {_encode(key, meta[key])}\n" for _, key in ordered)
    return f"---\n{head}---\n{body}"


def _set(meta, key, value):
    """`meta` with `key` set, or dropped when `value` is empty."""
    out = {k: v for k, v in meta.items() if k != key}
    if value in (None, "", [], (), {}):
        return out
    return {**meta, key: value}


# ---- the stub ----------------------------------------------------------------------------------------------------

def render_stub(meta):
    """A stub from its meta, keys in the fixed order; empty values are left out, the body is empty."""
    return _assemble({key: meta[key] for key in STUB_KEYS if meta.get(key) not in (None, "", [], ())})


def new_stub(record_id, title, today, modes, branch="", start_commit="", challenges=(), title_override=""):
    """`title_override` is the day the lead kept a title the name check refused; empty when none was."""
    return render_stub({"id": record_id, "type": "session", "title": title, "date": today, "modes": list(modes),
                        "status": "open", "branch": branch, "start_commit": start_commit,
                        "captures_sha256": {1: PENDING}, "challenges": list(challenges),
                        "title_override": title_override})


def stub_meta(text):
    return _read(text)[0]


def parts(meta):
    """{part: fingerprint or PENDING}."""
    held = meta.get("captures_sha256") or {}
    return {int(part): str(value) for part, value in held.items()}


def next_part(meta):
    held = parts(meta)
    return max(held) + 1 if held else 1


def with_part(stub_text, part, value):
    meta, body = _read(stub_text)
    held = parts(meta)
    held[part] = value
    return _assemble(_set(meta, "captures_sha256", held), body)


def with_status(stub_text, status):
    meta, body = _read(stub_text)
    return _assemble({**meta, "status": status}, body)


def listed(meta, key):
    return tuple(str(item) for item in (meta.get(key) or ()))


def lists_of(private_text):
    """The ready item IDs and the declined harvest entries a private file holds."""
    ready, declined, inside = [], [], False
    for line in private_text.split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip() == READY_HEADING
        found = READY_LINE.match(line.strip()) if inside else None
        if found and found["id"] not in ready:
            ready.append(found["id"])
        decline = DECLINE.match(line)
        if decline:
            declined.append(decline_entry(decline))
    return {"ready": ready, "harvest_declined": declined}


def decline_entry(match):
    return f"PR {match['pr']} {match['page']} {match['hash']}"


def with_lists(text, lists):
    meta, body = _read(text)
    for key, items in lists.items():
        meta = _set(meta, key, list(items))
    return _assemble(meta, body)


def synced_stub(stub_text, private_text):
    return with_lists(stub_text, lists_of(private_text))


# ---- the private file --------------------------------------------------------------------------------------------

def new_private(record_id, title, today, part):
    return (f"---\nid: {record_id}\npart: {part}\nsummary: {json.dumps('In progress.')}\n---\n\n"
            f"# {today} {title}\n\n{_NEW_RECORD_TABLE}")


def part_of(private_text):
    try:
        return int(_read(private_text)[0]["part"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("this private file does not say which part it is") from exc


def summary_of(private_text):
    return str(_read(private_text)[0].get("summary", ""))


def with_summary(private_text, summary):
    meta, body = _read(private_text)
    return _assemble(_set(meta, "summary", summary), body)


# ---- the reference grammar ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Ref:
    part: int
    n: int

    @property
    def text(self):
        return ref_text(self.part, self.n)


def ref_text(part, n):
    return f"c{n:02d}" if part == 1 else f"{part}.c{n:02d}"


def parse_ref(text):
    found = _REF.fullmatch(text)
    if not found or int(found[1] or 1) < 1:
        return None
    return Ref(int(found[1] or 1), int(found[2]))


def citation(record_id, part, n):
    return f"[[{record_id}]] {ref_text(part, n)}"


def parse_citation(text):
    found = CITATION.fullmatch(text.strip().strip('"'))
    return (found["record"], parse_ref(found["ref"])) if found else None


def rewrite_anchor_links(text):
    """Old `[[<id>#^c09]]` links as `[[<id>]] c09`, with the count; the record needn't be in this vault."""
    return ANCHOR_LINK.subn(lambda m: f"[[{m['record']}]] c{m['n']}", text)


# ---- splitting a whole record ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Split:
    stub: str
    private: str


def split_record(full_text, part=1):
    """A whole record as its stub and its private file: every word goes to the private file, the header stays."""
    meta, body = _read(full_text)
    private = _assemble({"id": meta["id"], "part": part, "summary": str(meta.get("summary", ""))}, body)
    lists = lists_of(private)
    lists["challenges"] = _challenges(meta)
    kept = {key: meta[key] for key in STUB_KEYS if key in meta and key not in LISTS and key != "captures_sha256"}
    kept["captures_sha256"] = {part: fingerprint(private)}
    for key in LISTS:
        kept = _set(kept, key, lists[key])
    return Split(stub=_assemble(kept), private=private)


def _challenges(meta):
    if "challenge" not in (meta.get("modes") or ()):
        return []
    found = CHALLENGE_TITLE.match(str(meta.get("title", "")))
    return [found["id"]] if found else []
