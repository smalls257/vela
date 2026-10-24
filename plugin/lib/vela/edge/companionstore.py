"""The companions' files on disk, git and the two caches (Buffer: the pure modules never touch these).

Everything lives under `.vela/companion/` in the vault: like the rest of `.vela/` it stays on this machine and is
never staged. Nobody edits these files by hand; a file vela cannot read is said, never read as empty.
"""
import json
import os
import pathlib

from vela import catalog, errors, pageindex, privaterecord, sessions, topicmap, vaultpaths
from vela.edge import atomic, sessiongit, vaultfiles

FOLDER = ".vela/companion"
INDEX = FOLDER + "/pages.json"


def folder(root):
    return pathlib.Path(root) / FOLDER


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, json.dumps(data, indent=1, sort_keys=True) + "\n")


def _read_index(path):
    """(index, why): the stored index, or (None, the reason it can't be used). Missing is not an error."""
    if not path.is_file():
        return None, ""
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return None, f"the page index could not be read ({exc})"
    if not isinstance(stored, dict) or stored.get("version") != pageindex.VERSION or not isinstance(stored.get("pages"), dict):
        return None, "the page index was written by another version of vela"
    return stored, ""


def page_index(root):
    """{"version": 1, "pages": {rel: {"mtime_ns", "size", **pageindex.entries(...)}}}: stats every page, re-parses only
    new or changed ones, drops deleted ones, and writes the file back only when something changed. An index that can't
    be read, or of another VERSION, is rebuilt whole and returned with "rebuilt": "<why>" so the caller can say it;
    it is never read as an empty plan."""
    root = pathlib.Path(root)
    path = root / INDEX
    stored, why = _read_index(path)
    old = stored["pages"] if stored else {}
    current = vaultfiles.stats(root)
    pages, changed = {}, bool(why) or set(old) != {rel for rel in current if rel.endswith(".md")}
    for rel, (mtime, size) in current.items():
        if not rel.endswith(".md"):
            continue
        kept = old.get(rel)
        if kept and kept["mtime_ns"] == mtime and kept["size"] == size:
            pages[rel] = kept
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise errors.ToolError(f"Cannot read {rel}: {exc}") from exc
        pages[rel] = {"mtime_ns": mtime, "size": size, **pageindex.entries(rel, text)}
        changed = True
    index = {"version": pageindex.VERSION, "pages": pages}
    if changed:
        write_json(path, index)
    if why:
        index["rebuilt"] = why
    return index


class NoSession(Exception):
    """No session is open in this folder; `problems` names each record whose header could not be read."""

    def __init__(self, problems=()):
        super().__init__("No session is open in this folder.")
        self.problems = list(problems)


class Several(Exception):
    """More than one session is open; the lead picks. `records` are sessions.Record values."""

    def __init__(self, records):
        super().__init__("More than one session is open here.")
        self.records = list(records)


def open_session(root):
    """(stub meta, notes text or None, problems): the one open session, read from the folder in place (no git, so it is
    fast and works in a reader copy). Raises NoSession or Several. Notes that are missing or can't be read come back
    as None with the reason in problems: never as empty text."""
    root = pathlib.Path(root)
    try:
        found = sessiongit.folder_records(root)
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.ToolError(f"I couldn't read the session records here ({exc}).") from exc
    opened, problems = sessions.find_open(found)
    if not opened:
        raise NoSession(problems)
    if len(opened) > 1:
        raise Several(opened)
    record = opened[0]
    try:
        stub = privaterecord.stub_meta((root / record.path).read_text(encoding="utf-8"))
        notes = sessiongit.private_text(root, record.id)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return {"id": record.id, "title": record.title, "date": record.date, "modes": list(record.modes)}, None, \
            [f"The session's notes couldn't be read ({exc})."]
    if notes is None:
        return stub, None, ["The session's notes aren't on this machine."]
    return stub, notes, list(problems)


def touched(root, start_commit, started):
    """The vault pages changed since the session began, as a tuple of vault-relative paths. Under git: what differs
    from `start_commit` plus the untracked files. In a copy with no git (a reader's), the pages modified after
    `started` (seconds since the epoch). Raises vaultgit.GitUnavailable with git's words: the caller says so,
    never reads a failure as "nothing changed"."""
    root = pathlib.Path(root)
    if sessiongit.is_read_copy(root):  # a reader's copy has no history of its own; never read some other repo's
        return tuple(sorted(rel for rel, (mtime, _) in vaultfiles.stats(root).items()
                            if rel.endswith(".md") and mtime / 1e9 > started))
    from vela.edge import vaultgit
    changed = vaultgit.git_out(root, "diff", "--name-only", "--relative", start_commit or "HEAD", "--", ".")
    fresh = vaultgit.git_out(root, "ls-files", "--others", "--exclude-standard")
    found = {line.strip() for line in (changed + "\n" + fresh).split("\n") if line.strip()}
    return tuple(sorted(rel for rel in found if rel.endswith(".md") and vaultpaths.page_kind(rel) == "page"))


def map_next(root, session_id):
    """(the topic map's first move in words, why it couldn't be read): ("", "") when there is no map or no move."""
    path = pathlib.Path(root) / topicmap.FOLDER / f"{session_id}.json"
    if not path.is_file():
        return "", ""
    try:
        state = topicmap.parse(path.read_text(encoding="utf-8"))
        kinds = catalog.parse_catalog(catalog.load_yaml(CATALOG.read_text(encoding="utf-8"))).kinds
    except (OSError, UnicodeDecodeError, topicmap.MapUnreadable, catalog.CatalogError, ValueError) as exc:
        return "", f"I couldn't read the topic map ({exc})."
    found = topicmap.moves(state, kinds)
    return (found[0].text, "") if found else ("", "")


CATALOG = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "catalog" / "questions.yaml"


def plan_next(root):
    """(text, made date) of the digest's suggestion, ("", "") when there is no digest or it holds none."""
    path = pathlib.Path(root) / FOLDER / "plan.json"
    if not path.is_file():
        return "", ""
    try:
        found = json.loads(path.read_text(encoding="utf-8")).get("next") or {}
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return "", ""
    return str(found.get("text", "")), str(found.get("made", ""))


def write_forms(root, kind, data, md, html, html_out=None, published=False):
    """.vela/companion/<kind>.json|.md|.html, atomic; `html_out` too when given; published.json {capture, at, session}
    only when `published` is True (plan ruling 10: only the Cowork publish path writes it). The paths written."""
    base = folder(root)
    base.mkdir(parents=True, exist_ok=True)
    files = {base / f"{kind}.json": json.dumps(data, indent=1, ensure_ascii=False) + "\n",
             base / f"{kind}.md": md, base / f"{kind}.html": html}
    if html_out:
        files[pathlib.Path(html_out)] = html
    if published:
        files[base / "published.json"] = json.dumps(
            {"capture": data.get("capture", 0), "at": data.get("as_of", ""),
             "session": (data.get("session") or {}).get("id", "")}) + "\n"
    atomic.write_all_atomic(files)
    return list(files)


def clear_forms(root, kind):
    """Remove a kind's three files and the published marker, so a panel can't keep showing a session that has closed."""
    base = folder(root)
    for name in (f"{kind}.json", f"{kind}.md", f"{kind}.html", "published.json"):
        (base / name).unlink(missing_ok=True)


DESIGN_DOCS = "docs/tech-design"


def design_session(root):
    """What a design session is made of, or None when this folder isn't on a `design/<slug>` branch (or has no git):
    {"branch", "slug", "record", "doc_rel", "doc_text", "design", "touched"}. The yes record is
    `.vela/design/<slug>.md` by `commands/record.design_record_path`'s rule, the doc `docs/tech-design/<slug>.md`;
    either may not exist yet (a design just begun), and then it is empty text, not an error. `touched` is the pages
    changed under docs/ and CONTEXT.md since the vault commit the doc cites, None when git could not say."""
    from vela.commands import record as record_command
    from vela.edge import vaultgit
    from vela.explorer import design_data
    root = pathlib.Path(root)
    try:
        branch = vaultgit.current_branch(root)
    except vaultgit.GitUnavailable:
        return None
    record_rel = record_command.design_record_path(branch or "")
    if not record_rel:
        return None
    slug = pathlib.Path(record_rel).stem
    doc_rel = f"{DESIGN_DOCS}/{slug}.md"
    record = _read_or_empty(root / record_rel)
    doc_text = _read_or_empty(root / doc_rel)
    design = _design_of(root / doc_rel, design_data, slug) if doc_text else _blank_design(slug)
    commits = design["vault"]["commits"] if design.get("vault") else []
    try:
        changed = vaultgit.git_out(root, "diff", "--name-only", "--relative", commits[0] if commits else "HEAD", "--", ".")
        fresh = vaultgit.git_out(root, "ls-files", "--others", "--exclude-standard")
        found = {line.strip() for line in (changed + "\n" + fresh).split("\n") if line.strip()}
        touched = tuple(sorted(rel for rel in found if rel.startswith("docs/") or rel == "CONTEXT.md"))
    except vaultgit.GitUnavailable:
        touched = None
    return {"branch": branch, "slug": slug, "record": record, "doc_rel": doc_rel, "doc_text": doc_text,
            "design": design, "touched": touched}


def _read_or_empty(path):
    """The file's text, "" when it isn't there yet. A file that is there and can't be read raises, never reads as empty."""
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.ToolError(f"Cannot read {path.name}: {exc}") from exc


def _design_of(path, design_data, slug):
    try:
        return design_data.read_design(path)
    except design_data.DesignError as exc:
        raise errors.ToolError(str(exc)) from exc


def _blank_design(slug):
    return {"title": "", "frontmatter": {"slug": slug, "gaps": [], "deferred": []}, "summary": {"text": "", "mermaid": []},
            "open_questions": [], "vault": None, "problems": []}
