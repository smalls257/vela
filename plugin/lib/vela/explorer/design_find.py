"""Find each app's team design doc when the build was not told where it is: `vela explore` with no `--design`.

    discover(vault, root, named) -> (["APP-x=<path>", ...], [report line, ...])

The team's doc lives in the team's own repository (docs/tech-design/<slug>.md), usually a sibling clone of the
vault's. Typing `--design` for every app on every build is how the Inside view ends up empty in a live call, so
the vault says where each one is, in the order below. The first source that names a readable doc wins, and an app
named by `--design` is never looked up.

  1. `design: <path>` in the app page's frontmatter;
  2. `designs: {APP-x: <path>}` in .vela.yaml;
  3. the vault's own docs/tech-design/*.md, where tech-design-grill writes when run from the vault root (a design
     is a vault file, so a team needs nothing configured): the doc whose frontmatter `vault.app` is the app, else
     whose `prereqs` name the app's page, else whose file name is the app's slug (`booking` for APP-booking, or the
     app page `booking-building-blocks.md`). Docs that match nothing are named in the report;
  4. the app's GitHub, Code, Repo or Repository link, when it is a local path or a file:// URL to a repository that
     holds docs/tech-design/*.md, taking the doc whose frontmatter `vault.app` names the app.

A relative path is relative to the vault root; `~` is the home folder. Only the local disk is read. A link to a web
address is never fetched, and is not a design source. A path that does not lead to a doc, a repository with no doc
naming the app, a doc whose frontmatter cannot be read: each is a warning line in the build report and the app is
simply "not loaded", never a failed build. A silent miss would leave a reader wondering why the Inside view is
empty, so every app without a design is named in the report with what was looked at.
"""
import pathlib
import urllib.parse

import yaml

from .record import title_of

DOC_GLOB = "docs/tech-design/*.md"
VAULT_DOCS = "docs/tech-design"
CODE_LABELS = ("github", "code", "repo", "repository")
FRONTMATTER_LIMIT = 64 * 1024  # a doc's frontmatter is a few hundred bytes; never read a whole doc to find it


def discover(vault, root, named):
    """Design arguments for the apps in `vault` that `named` (the --design arguments) does not cover, and the report."""
    root = pathlib.Path(root)
    given = {arg.split("=", 1)[0].strip() for arg in named}
    configured, said = configured_designs(vault.config)
    in_vault = vault_designs(root, said)
    found, missing = [], []
    for app in vault.apps:
        if app.id in given:
            continue
        look = Look(app, root, said)
        look.page_field()
        look.config_entry(configured)
        look.vault_docs(in_vault)
        look.repo_link()
        if look.doc:
            found.append(f"{app.id}={look.doc}")
            said.append(f"{app_named(app)}: using the design {shown(look.doc, root)}, found {look.how}")
        else:
            missing.append((app, look.tried))
    if missing:
        said.append(f"no design yet for {', '.join(app_named(app) for app, _ in missing)}, so Inside this app shows only their containers. "
                    f"To add one, the app's team runs /vela:design --app <app ID> from the plan's folder (it writes {VAULT_DOCS}/<slug>.md), "
                    "or point to one with design: on the app page, designs: in .vela.yaml, or --design <app ID>=<path>.")
        said += [f"  {app_named(app)}: {'; '.join(tried)}" for app, tried in missing if tried]
    return found, said


def app_named(app):
    """An app as the report names it: its title, with the ID a lead types beside it."""
    title = title_of(app)
    return f"{title} ({app.id})" if title and title != app.id else app.id


def vault_designs(root, said):
    """[(doc, frontmatter)] for every docs/tech-design/*.md in the vault. A doc whose frontmatter cannot be read is one
    warning here, said once, and takes no part in matching."""
    found = []
    for doc in sorted((root / VAULT_DOCS).glob("*.md")):
        try:
            with doc.open(encoding="utf-8") as handle:
                head = handle.read(FRONTMATTER_LIMIT)
        except (OSError, UnicodeDecodeError) as exc:
            said.append(f"warning: cannot read {shown(doc, root)}: {exc}")
            continue
        meta = frontmatter(head)
        if meta is None:
            said.append(f"warning: {shown(doc, root)} has no readable frontmatter, so it cannot be matched to an app")
            continue
        found.append((doc, meta))
    return found


def prereq_paths(meta):
    """The paths a doc's `prereqs` point at: each entry is a path, or a map with a `path`."""
    raw = meta.get("prereqs")
    entries = raw if isinstance(raw, list) else [raw]
    paths = [e.get("path") if isinstance(e, dict) else e for e in entries]
    return [p for p in paths if isinstance(p, str)]


def configured_designs(config):
    """({app ID: path} from .vela.yaml's `designs:`, the warnings about it)."""
    raw = config.get("designs")
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["warning: .vela.yaml designs: is not a map of app ID to a design doc path, so none of it is used"]
    return {str(app): value for app, value in raw.items()}, []


class Look:
    """One app's search: the doc once found, how it was found, and what was looked at without a find. A path that
    leads nowhere is a warning in the report at once; a repository with nothing in it for this app is a note, said
    only if the app ends up with no design."""

    def __init__(self, app, root, said):
        self.app, self.root, self.said = app, root, said
        self.doc, self.how, self.tried = None, "", []

    def warn(self, text):
        self.said.append(f"warning: {app_named(self.app)}: {text}")

    def adopt(self, doc, how):
        self.doc, self.how = doc, how

    def page_field(self):
        value = self.app.meta.get("design")
        if value is not None:
            self.from_path(value, "from design: on its page")

    def config_entry(self, configured):
        if self.doc or self.app.id not in configured:
            return
        self.from_path(configured[self.app.id], "from designs: in .vela.yaml")

    def from_path(self, value, where):
        doc = self.file_at(value, where)
        if doc:
            self.adopt(doc, where)

    def file_at(self, value, where):
        if not isinstance(value, str) or not value.strip():
            self.warn(f"{where.removeprefix('from ')} is not a path to a design doc ({value!r})")
            return None
        path = local_path(value.strip(), self.root)
        if path is None:
            self.warn(f"{where.removeprefix('from ')} is a web address ({value}); Vela never fetches one, so point it to a local copy of the repo instead")
            return None
        if not path.is_file():
            self.warn(f"{where.removeprefix('from ')} is {value}, which is not a file ({path})")
            return None
        why = not_a_doc(path, "tech-design")
        if why:
            self.warn(f"{where.removeprefix('from ')} is {value}, which {why}, so it isn't read")
            return None
        return path

    def vault_docs(self, docs):
        if self.doc or not docs:
            return
        slugs = {self.app.id.removeprefix("APP-").lower(), self.app.name.lower().removesuffix("-building-blocks")}
        page_name = self.app.path.rsplit("/", 1)[-1]
        rules = (("it names this app", lambda doc, meta: (meta.get("vault") or {}).get("app") == self.app.id if isinstance(meta.get("vault"), dict) else False),
                 ("it points to this app's page", lambda doc, meta: any(p.rsplit("/", 1)[-1] == page_name for p in prereq_paths(meta))),
                 ("its file name matches the app", lambda doc, meta: doc.stem.lower() in slugs))
        for why, matches in rules:
            hits = [doc for doc, meta in docs if matches(doc, meta)]
            if hits:
                if len(hits) > 1:
                    self.warn(f"{len(hits)} docs in {VAULT_DOCS} match it ({why}: {', '.join(d.name for d in hits)}); using {hits[0].name}")
                self.adopt(hits[0], f"in {VAULT_DOCS}/ in the plan's folder, because {why}")
                return
        self.tried.append(f"{VAULT_DOCS}/ holds {len(docs)} design doc{'s' if len(docs) != 1 else ''}, but none is for this app (none names it, points to its page or has its file name)")

    def repo_link(self):
        if self.doc:
            return
        links = self.app.meta.get("links")
        if not isinstance(links, dict):
            return
        for label, value in links.items():
            if str(label).strip().lower() not in CODE_LABELS or not isinstance(value, str):
                continue
            path = local_path(value.strip(), self.root)
            if path is None:
                continue  # an https link to the repository: the usual case, and nothing to read from it
            self.in_repo(label, value, path)
            if self.doc:
                return

    def in_repo(self, label, value, repo):
        where = f"its {label} link {value}"
        if not repo.is_dir():
            self.warn(f"{where} is not a folder ({repo})")
            return
        docs = sorted(repo.glob(DOC_GLOB))
        if not docs:
            self.tried.append(f"{where} has no {DOC_GLOB}")
            return
        names = [doc for doc in docs if self.names_this_app(doc)]
        if not names:
            self.tried.append(f"{where} holds {len(docs)} design doc{'s' if len(docs) != 1 else ''}, but none of them is for this app (none has vault: app: {self.app.id})")
            return
        if len(names) > 1:
            self.warn(f"{where} holds {len(names)} docs that name it ({', '.join(d.name for d in names)}); using {names[0].name}")
        self.adopt(names[0], f"through {where}, because it names this app")

    def names_this_app(self, doc):
        try:
            with doc.open(encoding="utf-8") as handle:
                head = handle.read(FRONTMATTER_LIMIT)
        except (OSError, UnicodeDecodeError) as exc:
            self.warn(f"cannot read {doc}: {exc}")
            return False
        meta = frontmatter(head)
        if meta is None:
            self.warn(f"{doc.name} has no readable frontmatter, so it cannot be matched to an app")
            return False
        vault = meta.get("vault")
        return isinstance(vault, dict) and vault.get("app") == self.app.id


def not_a_doc(path, folder):
    """Why a path named by a page is not read, or "" when it is. A page can come from outside (a pulled branch, a proposal), and
    what this module reads is copied into dashboard.html and published; so only a Markdown file under docs/<folder>/ is read,
    never `~/Documents/salary-notes.md` or an `id_rsa`."""
    parts = path.resolve().parts
    if path.suffix.lower() != ".md":
        return "is not a Markdown file"
    if not any(parts[i:i + 2] == ("docs", folder) for i in range(len(parts) - 1)):
        return f"is not under a docs/{folder} folder"
    return ""


def local_path(value, root):
    """The Path a local reference names: a file:// URL, `~/x`, an absolute path or one relative to the vault root.
    None for an http(s) or other URL with a host, which this module never opens."""
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme == "file":
        return pathlib.Path(urllib.parse.unquote(parsed.path))
    if parsed.scheme and len(parsed.scheme) > 1:  # not a Windows drive letter
        return None
    path = pathlib.Path(value).expanduser()
    return path if path.is_absolute() else (root / path)


def frontmatter(text):
    """The doc's frontmatter mapping, or None when it has none or it is not valid YAML."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def shown(path, root):
    """A path as the report names it: inside the vault, relative to it; otherwise as the disk has it."""
    try:
        return pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)
