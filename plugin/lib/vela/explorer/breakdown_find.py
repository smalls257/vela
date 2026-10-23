"""Find each app's work-breakdown plan when the build was not told where it is: `vela explore` with no `--breakdown`.

    discover(vault, root, named, design_args) -> (["APP-x=<path>", ...], [report line, ...])

The plan lives in the team's repository beside the design (docs/plan/<slug>-breakdown.md; the work-breakdown skill
writes it after tech design), so the lookup mirrors design_find.py, in this order. The first source that names a
readable file wins, and an app named by `--breakdown` is never looked up.

  1. `breakdown: <path>` in the app page's frontmatter;
  2. `breakdowns: {APP-x: <path>}` in .vela.yaml;
  3. beside the app's design: the same repository's docs/plan/*-breakdown.md whose frontmatter `prereqs` name that
     design doc (by its file name). Two plans naming one design is a warning, and the first is used.

A relative path is relative to the vault root; `~` is the home folder. Only the local disk is read. A path that leads
nowhere, or a plan whose frontmatter cannot be read, is a warning line in the build report and the app simply has no
plan, never a failed build. An app that has a design but no plan is named in the report with what was looked at, so a
reader who sees "No build plan yet" can find out why.
"""
import pathlib

from . import design_data
from .design_find import FRONTMATTER_LIMIT, frontmatter, local_path, app_named, not_a_doc, shown

PLAN_GLOB = "*-breakdown.md"


def discover(vault, root, named, design_args):
    """Breakdown arguments for the apps in `vault` that `named` (the --breakdown arguments) does not cover, and the report."""
    root = pathlib.Path(root)
    given = {arg.split("=", 1)[0].strip() for arg in named}
    configured, said = configured_breakdowns(vault.config)
    designs = {m.group(1): pathlib.Path(m.group(2)) for m in (design_data.SPEC.match(a.strip()) for a in design_args) if m}
    found, missing = [], []
    for app in vault.apps:
        if app.id in given:
            continue
        look = Look(app, root, said)
        look.page_field()
        look.config_entry(configured)
        look.beside_design(designs.get(app.id))
        if look.plan:
            found.append(f"{app.id}={look.plan}")
            said.append(f"{app_named(app)}: using the build plan {shown(look.plan, root)}, found {look.how}")
        elif app.id in designs:
            missing.append((app, look.tried))
    if missing:
        said.append(f"no build plan yet for {', '.join(app_named(app) for app, _ in missing)}; their Build plan level says so. "
                    "Point to one with breakdown: on the app page, breakdowns: in .vela.yaml, or --breakdown <app ID>=<path>.")
        said += [f"  {app_named(app)}: {'; '.join(tried)}" for app, tried in missing if tried]
    return found, said


def configured_breakdowns(config):
    """({app ID: path} from .vela.yaml's `breakdowns:`, the warnings about it)."""
    raw = config.get("breakdowns")
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["warning: .vela.yaml breakdowns: is not a map of app ID to a breakdown path, so none of it is used"]
    return {str(app): value for app, value in raw.items()}, []


class Look:
    """One app's search: the plan once found, how it was found, and what was looked at without a find."""

    def __init__(self, app, root, said):
        self.app, self.root, self.said = app, root, said
        self.plan, self.how, self.tried = None, "", []

    def warn(self, text):
        self.said.append(f"warning: {app_named(self.app)}: {text}")

    def page_field(self):
        value = self.app.meta.get("breakdown")
        if value is not None:
            self.from_path(value, "from breakdown: on its page")

    def config_entry(self, configured):
        if self.plan or self.app.id not in configured:
            return
        self.from_path(configured[self.app.id], "from breakdowns: in .vela.yaml")

    def from_path(self, value, where):
        said = where.removeprefix("from ")
        if not isinstance(value, str) or not value.strip():
            self.warn(f"{said} is not a path to a build plan ({value!r})")
            return
        path = local_path(value.strip(), self.root)
        if path is None:
            self.warn(f"{said} is a web address ({value}); Vela never fetches one, so point it to a local copy of the repo instead")
        elif not path.is_file():
            self.warn(f"{said} is {value}, which is not a file ({path})")
        elif not_a_doc(path, "plan"):
            self.warn(f"{said} is {value}, which {not_a_doc(path, 'plan')}, so it isn't read")
        else:
            self.plan, self.how = path, where

    def beside_design(self, design):
        if self.plan or design is None:
            return
        folder = design.resolve().parent.parent / "plan"  # docs/tech-design/x.md -> docs/plan
        plans = sorted(folder.glob(PLAN_GLOB)) if folder.is_dir() else []
        if not plans:
            self.tried.append(f"no {PLAN_GLOB} in {folder}, beside the design")
            return
        names = [plan for plan in plans if self.names_design(plan, design.name)]
        if not names:
            self.tried.append(f"{len(plans)} plan{'s' if len(plans) != 1 else ''} in {folder}, but none of them is for the {design.name} design")
            return
        if len(names) > 1:
            self.warn(f"{len(names)} plans name {design.name} in their prereqs ({', '.join(p.name for p in names)}); using {names[0].name}")
        self.plan, self.how = names[0], f"beside its design, because it points to {design.name}"

    def names_design(self, plan, design_name):
        try:
            with plan.open(encoding="utf-8") as handle:
                head = handle.read(FRONTMATTER_LIMIT)
        except (OSError, UnicodeDecodeError) as exc:
            self.warn(f"cannot read {plan}: {exc}")
            return False
        meta = frontmatter(head)
        if meta is None:
            self.warn(f"{plan.name} has no readable frontmatter, so it cannot be matched to a design")
            return False
        return design_name in prereq_names(meta)


def prereq_names(meta):
    """The file names a plan's `prereqs` point at: each entry is a path, or a map with a `path`."""
    raw = meta.get("prereqs")
    entries = raw if isinstance(raw, list) else [raw]
    paths = [e.get("path") if isinstance(e, dict) else e for e in entries]
    return [pathlib.PurePosixPath(p).name for p in paths if isinstance(p, str)]
