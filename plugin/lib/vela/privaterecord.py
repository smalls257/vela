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

Standard library only, so the ready-entry grammar and the decline line are defined here; the modules that read
them import them from this one.
"""
import hashlib
import json
import re
from dataclasses import dataclass

PRIVATE_DIR = "sessions/private"
PENDING = "pending"
LISTS = ("ready", "challenges", "harvest_declined")
STUB_KEYS = ("id", "type", "title", "date", "modes", "status", "branch", "start_commit", "captures_sha256",
             "ready", "challenges", "harvest_declined")
READY_HEADING = "Ready to decide"
READY_LINE = re.compile(r"^- (?P<id>\S+): the lead said yes in (?P<session>\S+)(?: \((?P<yes>\^c\d+)\))?\s*$")
DECLINE = re.compile(r"^Harvest declined: PR (?P<pr>\d+) (?P<page>.+) (?P<hash>[0-9a-f]{12})\s*$")
DECLINE_PREFIX = "Harvest declined: "
CHALLENGE_TITLE = re.compile(r"^Challenge:\s*(?P<id>\S+)")
CITATION = re.compile(r"\[\[(?P<record>[^\]#|]+)\]\] (?P<ref>(?:\d+\.)?c\d+)\b")
ANCHOR_LINK = re.compile(r"\[\[(?P<record>\d{4}-\d{2}-\d{2}-[^\]#|\\]+)#\^c(?P<n>\d+)(?:\\?\|[^\]]*)?\]\]")
_REF = re.compile(r"(?:(\d+)\.)?c(\d+)")
_FIELD = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?:\s+(?P<value>.*?))?\s*$")
_PAIR = re.compile(r'(\d+)\s*:\s*("(?:[^"\\]|\\.)*"|[^,}\s]+)')
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


# ---- frontmatter, kept as ordered raw lines so keys this module doesn't know survive a rewrite -------------------

def _read(text):
    """(pairs, body): the frontmatter as [(key, raw value)] and everything after the closing `---`."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return _pairs(lines[1:end]), "\n".join(lines[end + 1:])
    raise ValueError("the frontmatter block is never closed")


def _pairs(lines):
    pairs = []
    for line in lines:
        if not line.strip():
            continue
        found = _FIELD.match(line)
        if not found:
            raise ValueError(f"unreadable frontmatter line: {line!r}")
        pairs.append((found["key"], found["value"] or ""))
    return pairs


def _decode(raw):
    raw = raw.strip()
    if raw.startswith('"'):
        return json.loads(raw)
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except ValueError:
            return [item.strip() for item in raw[1:-1].split(",") if item.strip()]
    if raw.startswith("{"):
        return {int(k): json.loads(v) if v.startswith('"') else v for k, v in _PAIR.findall(raw)}
    return raw


def _encode(key, value):
    if key == "modes":
        return "[" + ", ".join(value) + "]"
    if key == "captures_sha256":
        return "{" + ", ".join(f"{part}: {json.dumps(v)}" for part, v in sorted(value.items())) + "}"
    if key in LISTS:
        return json.dumps(list(value), ensure_ascii=False)
    if key in ("id", "type", "date", "status", "part"):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _assemble(pairs, body=""):
    rank = {key: i for i, key in enumerate(STUB_KEYS)}
    ordered = sorted(enumerate(pairs), key=lambda ip: (rank.get(ip[1][0], len(rank)), ip[0]))
    head = "".join(f"{key}: {raw}\n" for _, (key, raw) in ordered)
    return f"---\n{head}---\n{body}"


def _set(pairs, key, raw):
    """`pairs` with `key` set to `raw`, or dropped when `raw` is None."""
    kept = [(k, v) for k, v in pairs if k != key]
    if raw is None:
        return kept
    if any(k == key for k, _ in pairs):
        return [(k, raw if k == key else v) for k, v in pairs]
    return kept + [(key, raw)]


def _meta(text):
    pairs, _ = _read(text)
    return {key: _decode(raw) for key, raw in pairs}


# ---- the stub ----------------------------------------------------------------------------------------------------

def render_stub(meta):
    """A stub from its meta, keys in the fixed order; empty values are left out, the body is empty."""
    pairs = [(key, _encode(key, meta[key])) for key in STUB_KEYS if meta.get(key) not in (None, "", [], ())]
    return _assemble(pairs)


def new_stub(record_id, title, today, modes, branch="", start_commit="", challenges=()):
    return render_stub({"id": record_id, "type": "session", "title": title, "date": today, "modes": list(modes),
                        "status": "open", "branch": branch, "start_commit": start_commit,
                        "captures_sha256": {1: PENDING}, "challenges": list(challenges)})


def stub_meta(text):
    try:
        return _meta(text)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"unreadable session frontmatter: {exc}") from exc


def parts(meta):
    """{part: fingerprint or PENDING}."""
    held = meta.get("captures_sha256") or {}
    return {int(part): str(value) for part, value in held.items()}


def next_part(meta):
    held = parts(meta)
    return max(held) + 1 if held else 1


def with_part(stub_text, part, value):
    pairs, body = _read(stub_text)
    held = parts({key: _decode(raw) for key, raw in pairs})
    held[part] = value
    return _assemble(_set(pairs, "captures_sha256", _encode("captures_sha256", held)), body)


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
    pairs, body = _read(text)
    for key, items in lists.items():
        pairs = _set(pairs, key, _encode(key, items) if items else None)
    return _assemble(pairs, body)


def synced_stub(stub_text, private_text):
    return with_lists(stub_text, lists_of(private_text))


# ---- the private file --------------------------------------------------------------------------------------------

def new_private(record_id, title, today, part):
    return (f"---\nid: {record_id}\npart: {part}\nsummary: {json.dumps('In progress.')}\n---\n\n"
            f"# {today} {title}\n\n{_NEW_RECORD_TABLE}")


def part_of(private_text):
    try:
        return int(_meta(private_text)["part"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("this private file does not say which part it is") from exc


def summary_of(private_text):
    return str(_meta(private_text).get("summary", ""))


def with_summary(private_text, summary):
    pairs, body = _read(private_text)
    return _assemble(_set(pairs, "summary", json.dumps(summary, ensure_ascii=False)), body)


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
    return Ref(int(found[1] or 1), int(found[2])) if found else None


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
    pairs, body = _read(full_text)
    meta = {key: _decode(raw) for key, raw in pairs}
    private = (f"---\nid: {meta['id']}\npart: {part}\nsummary: {json.dumps(str(meta.get('summary', '')), ensure_ascii=False)}"
               f"\n---\n{body}")
    lists = lists_of(private)
    lists["challenges"] = _challenges(meta)
    header = {key: raw for key, raw in pairs if key in STUB_KEYS}
    stub_pairs = [(key, header[key]) for key in header if key not in LISTS and key != "captures_sha256"]
    stub_pairs.append(("captures_sha256", _encode("captures_sha256", {part: fingerprint(private)})))
    for key in LISTS:
        if lists[key]:
            stub_pairs.append((key, _encode(key, lists[key])))
    return Split(stub=_assemble(stub_pairs), private=private)


def _challenges(meta):
    if "challenge" not in (meta.get("modes") or ()):
        return []
    found = CHALLENGE_TITLE.match(str(meta.get("title", "")))
    return [found["id"]] if found else []
