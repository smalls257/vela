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
    try:
        digest = plan_digest(root)
    except errors.ToolError:  # a digest that can't be read is rebuilt by `explain`; a session panel just has no suggestion
        return "", ""
    found = (digest or {}).get("next") or {}
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
        files[base / "published.json"] = json.dumps(_published(base / "published.json", kind, data)) + "\n"
    atomic.write_all_atomic(files)
    return list(files)


def _published(path, kind, data):
    """published.json: the session panel's capture and the explain panel's view, each under its own entry, so
    publishing one never erases what the other said it drew."""
    try:
        held = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, UnicodeDecodeError, ValueError):  # a marker that can't be read is rewritten from this publish
        held = {}
    if kind == "session":
        held.update({"capture": data.get("capture", 0), "at": data.get("as_of", ""),
                     "session": (data.get("session") or {}).get("id", "")})
    else:
        held["explain"] = {"view": data.get("view", ""), "at": data.get("as_of", "")}
    return held


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


BASE_CSS = pathlib.Path(__file__).resolve().parent.parent / "explorer" / "assets" / "css" / "base.css"


def palette():
    """The `:root { ... }` block of the dashboard's palette, through its end marker, so the panel and the dashboard
    share one set of colors. A palette that can't be read raises: a page with no colors would be unreadable ink on ink."""
    try:
        text = BASE_CSS.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.ToolError(f"The dashboard's colors couldn't be read ({exc}).") from exc
    end = text.find("/* end of palette */")
    start = text.find(":root {")
    if start < 0 or end < 0:
        raise errors.ToolError("The dashboard's palette has no end marker, so the panel has no colors to use.")
    return text[start:end] + "}"


PLAN = FOLDER + "/plan.json"


def plan_digest(root):
    """The stored plan digest, None when there isn't one. One that can't be read raises ToolError: it is never read as
    an empty plan."""
    path = pathlib.Path(root) / PLAN
    if not path.is_file():
        return None
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise errors.ToolError(f"The plan digest couldn't be read ({exc}).") from exc
    if not isinstance(found, dict) or "version" not in found:
        raise errors.ToolError("The plan digest isn't one this vela wrote.")
    return found


def write_plan_digest(root, digest):
    write_json(pathlib.Path(root) / PLAN, digest)


def copy_source(root):
    """Where this copy came from, in words for the digest: "GitHub <repository>" or "a published copy" for a reader's
    copy, "this repository" for an owner's."""
    root = pathlib.Path(root)
    if not sessiongit.is_read_copy(root):
        return "this repository"
    try:
        stamp = json.loads((root / ".vela" / "published.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):  # a copy with no readable stamp is still a published copy
        return "a published copy"
    given = stamp.get("from") if isinstance(stamp, dict) else ""
    return str(given) if given else "a published copy"


def made_of(root, today, made_commit):
    """{"date", "commit", "from"} of the copy. A reader's copy is dated and numbered by its stamp (the owner's publish
    day and short commit), not by today and a git it doesn't have: every draft the reader saves changes the files, and
    stamping today on each re-prepare would roll "since last time" without a new copy (plan ruling 16)."""
    made = {"date": today, "commit": made_commit, "from": copy_source(root)}
    if not sessiongit.is_read_copy(root):
        return made
    try:
        stamp = json.loads((pathlib.Path(root) / ".vela" / "published.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):  # no readable stamp: the copy can't be told apart, today it is
        return made
    if isinstance(stamp, dict):
        made["date"] = str(stamp.get("date") or today)
        made["commit"] = str(stamp.get("short") or "")
    return made


def prepare_digest(vault, root, today, data, made_commit=""):
    """Cut the digest from the dashboard's own `data` and write it. `vault` is the loaded plan (for vela's own next
    line). The fingerprint is of the files as they are now."""
    from vela import cli, companionplan
    made = made_of(root, today, made_commit)
    digest = companionplan.digest(data, made, vaultfiles.fingerprint(root), cli.next_step_text(vault, today))
    write_plan_digest(root, digest)
    return digest


SEEN = FOLDER + "/seen.json"


def seen(root):
    """What the reader saw last ({"previous", "current"}), {} on the first copy. A file that can't be read raises
    ToolError: the caller says so and starts again, never reads it as "nothing changed"."""
    path = pathlib.Path(root) / SEEN
    if not path.is_file():
        return {}
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise errors.ToolError(f"What you saw last time couldn't be read ({exc}).") from exc
    return found if isinstance(found, dict) else {}


def write_seen(root, found):
    write_json(pathlib.Path(root) / SEEN, found)


def viewer(root):
    """(handle with its @, onboarding audience): from `.vela/handle` and the role saved by `vela whoami --role`, "" for
    each that isn't there."""
    root = pathlib.Path(root)
    handle = sessiongit.read_handle(root) or ""
    role = ""
    try:
        role = (root / ".vela" / "role").read_text(encoding="utf-8").split("\n", 1)[0].strip()
    except FileNotFoundError:
        role = ""
    except (OSError, UnicodeDecodeError):  # an unreadable role file is no role; the handle is what the views need
        role = ""
    handle = handle.strip()
    return ("@" + handle.lstrip("@") if handle else ""), role


def published(root):
    """What the Cowork publish path last drew ({"capture", "at", "session", "explain"}); {} when nothing was published
    here. A marker that can't be read raises ToolError."""
    path = pathlib.Path(root) / FOLDER / "published.json"
    if not path.is_file():
        return {}
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise errors.ToolError(f"The published-panel marker couldn't be read ({exc}).") from exc
    return found if isinstance(found, dict) else {}
