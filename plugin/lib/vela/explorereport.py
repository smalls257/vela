"""What `vela explore --for-lead` says for each line the explorer build reports (overhaul Task 21c).

The Violation this module's shape prevents is the Leaky Narrative. explore/SKILL.md "What the build reports" listed
the kinds of build line and asked the model to put each into plain words on every run, so the raw lines reached the
lead: app IDs beside every name ("Rider app (APP-rider)"), check codes ("vela check reports it as E105"), a summary that
opens with the initiative's ID, design statuses as the file spells them. The same translation lived twice, once in
prose and once in each model's head. Here it lives once, in code (Filter): one row in `KINDS` per kind of line, and
the skill relays what the command prints.

The rules the skill held, kept with their reasons:

- An app on the "no design yet" list is never described as having a design, so the line opens "No design yet".
- A design whose status is not complete is said as "not complete", because the lead must never hear an unfinished
  design called done.
- The first build's pins line is said once, in the lead's words: the map stays put between builds.
- A page saved too far from the vault drops its "Open the file" links rather than writing an absolute path (a page
  carries no path of the machine that built it), so the lead hears how to get them back: build without -o.
- A link that could not be read is named by the page that holds it, not by its file path or its check code.

A line no row matches (a build line added after this module) is still said: every ID in it resolved to its name, and
the `--for-lead` leak check still runs on it, so a new line can never leak quietly. It just has not been given
its own wording yet; `test_every_kind_has_a_row` lists the kinds that have.

Pure: the caller hands in the report text and a `say.Resolver`; nothing here reads the disk.
"""
import re

PREFIX = "vela explore: "

# `explorer.build.VAULT_ID_KEY`, said literally here so this module stays light: importing the explorer pulls in the
# whole page builder.
VAULT_ID_KEY = "vault_id"


def entries(output):
    """The report printed by `cli.cmd_explore`, one entry per `vela explore:` line, with its indented lines under it."""
    found = []
    for raw in output.splitlines():
        if raw.startswith(PREFIX):
            found.append(raw[len(PREFIX):])
        elif found and raw.strip():
            found[-1] += "\n" + raw
    return found


def _head_and_details(entry):
    head, *details = entry.split("\n")
    return head, [d.strip() for d in details if d.strip()]


def _plural(n, word, many=None):
    n = int(n)
    return f"{n} {word if n == 1 else (many or word + 's')}"


def _and(names):
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def _names(listed, r):
    """'Rider app (APP-rider), Dock service (APP-docks)' or 'APP-rider, APP-docks' -> 'Rider app and Dock service'."""
    return _and([r.plain(part.strip()) for part in re.split(r",\s*|/", listed) if part.strip()])


def _many(listed):
    return len([p for p in re.split(r",\s*|/", listed) if p.strip()]) > 1


def _page_title_at(path, r):
    vault = r.vault
    for page in (vault.pages if vault is not None else ()):
        if page.path == path:
            title = page.meta.get("title")
            return str(title) if title else page.name
    return None


def _first_build(m, details, r):
    return "I saved where each app sits on the map, so it stays put next time."


def _pinned_new(m, details, r):
    names, many = _names(m["names"], r), _many(m["names"])
    return f"I saved where {names} {'sit' if many else 'sits'} on the map, so {'they stay' if many else 'it stays'} put next time."


def _moved(m, details, r):
    many = _many(m["names"])
    return (f"{_names(m['names'], r)} stood on top of other boxes on the map, so I moved {'them' if many else 'it'} "
            "to the nearest free spot.")


def _computed(m, details, r):
    return f"Nothing keeps this build's layout, so the next build may place {_names(m['names'], r)} somewhere else."


def _link_left_out(m, details, r):
    title = _page_title_at(m["path"], r)
    where = f"the {r.plain(title)} page" if title else "one of the plan's pages"
    return f"A link on {where} couldn't be read, so it isn't shown."


def _design_found(m, details, r):
    return f"I found {r.plain(m['app'])}'s design and put it on the page."


def _looked(details, r):
    said = []
    for detail in details:
        app, _, tried = detail.partition(": ")
        said.append(f"For {r.plain(app)} I looked here: {r.plain(tried)}." if tried else r.plain(detail))
    return said


def _no_design(m, details, r):
    many = _many(m["apps"])
    head = (f"No design yet for {_names(m['apps'], r)}, so Inside this app shows only {'their' if many else 'its'} containers. "
            f"{'Each' if many else 'The'} app's team can write one with /vela:design from the plan's folder, or you can "
            "point to an existing doc with design: on the app page.")
    return " ".join([head] + _looked(details, r))


_MISSING_FILE = re.compile(r"^(?P<app>.+?): (?:from )?(?P<key>design|breakdown): on its page is (?P<path>\S+?),? "
                           r"which is not a file")


def _warning(m, details, r):
    missing = _MISSING_FILE.match(m["rest"])
    if missing:
        what = "design" if missing["key"] == "design" else "build plan"
        return (f"{r.plain(missing['app'])}'s page points to a {what} file that isn't there, so the build went on "
                "without it.")
    said = " ".join([f"{_unpathed(r.plain(m['rest'])).rstrip('.')}. The build went on without it."]
                    + [_unpathed(r.plain(d)) for d in details])
    return said


def _unpathed(text):
    """A line with every file path taken out: an absolute one in brackets dropped, any other said as "a file"."""
    from vela import say
    text = re.sub(r"\s*\((?:/|~/)[^)]*\)", "", text)
    return say.LEAD_PATTERNS["file path"].sub("a file", text)


def _status(status):
    words = status.replace("-", " ").strip()
    return f"marked {words}" + ("" if words.startswith("complete") else ", not complete")


def _unreadable(count, details, r):
    if not int(count):
        return ""
    parts = "; ".join(r.plain(d) for d in details)
    return f" {_plural(count, 'part')} couldn't be read" + (f": {parts}." if parts else ".")


def _design_status(m, details, r):
    return (f"{r.plain(m['app'])}'s design is {_status(m['status'])}, with {_plural(m['n'], 'component')}."
            + _unreadable(m["bad"], details, r))


def _plan_found(m, details, r):
    return f"I found {r.plain(m['app'])}'s build plan and put it on the page."


def _no_plan(m, details, r):
    many = _many(m["apps"])
    head = (f"No build plan yet for {_names(m['apps'], r)}, and {'their' if many else 'its'} Build plan level on the page says so. "
            "You can point to one with breakdown: on the app page.")
    return " ".join([head] + _looked(details, r))


def _plan_status(m, details, r):
    status = "has no status" if m["status"] == "no status" else f"is marked {m['status'].replace('-', ' ')}"
    return (f"{r.plain(m['app'])}'s build plan {status}: {_plural(m['stories'], 'story', 'stories')}, "
            f"{_plural(m['tasks'], 'task')}, {_plural(m['points'], 'point')}." + _unreadable(m["bad"], details, r))


def _icon(m, details, r):
    return (f"{r.plain(m['key'])} asks for an icon called {m['icon']}, which isn't in the built-in set, so the map draws "
            "it by keyword instead.")


def _page_far_away(m, details, r):
    return ("The page is saved too far from the plan's files, so its 'Open the file' links were left out. "
            "Build it again without -o to get them.")


def _design_far_away(m, details, r):
    return (f"{r.plain(m['app'])}'s design doc is saved too far from the page, so its 'Open the design doc' link was left "
            "out. Build it again without -o to get it.")


def _plan_far_away(m, details, r):
    return (f"{r.plain(m['app'])}'s build plan is saved too far from the page, so its 'Open the plan' and Tickets links "
            "were left out. Build it again without -o to get them.")


def _gitignore(m, details, r):
    return (f"This plan's .gitignore leaves out {m['page']}, so colleagues who pull the repo won't get the page. "
            "Taking that line out of .gitignore fixes it.")


def _assets(m, details, r):
    """Nothing to say when every picture came from where it was asked to: the normal case is not news."""
    return ""


def _assets_fell_back(m, details, r):
    slots = []
    for detail in details:
        slot, _, because = detail.partition(": ")
        slots.append(f"{slot} ({because})" if because else slot)
    fell = int(m["fell"])
    return (f"The pictures came from the {m['provider']} art, but {_plural(fell, 'picture')} fell back to the built-in art"
            + (f": {'; '.join(slots)}." if slots else "."))


def _party(m, details, r):
    many = _many(m["cons"])
    return (f"The {_names(m['cons'], r)} {'contracts name their' if many else 'contract names its'} provider only in "
            f"{'their' if many else 'its'} text (\"{m['said']}\"), so the map shows \"{m['title']}\". Tell me who "
            "provides it and I'll add them as an outside party.")


def _draft_changed(m, details, r):
    return f"You've changed {_plural(m['n'], 'page')} since you opened this copy."


def _draft_conflicts(m, details, r):
    n = int(m["n"])
    return (f"{_plural(n, 'conflict')} from the last re-open {'is' if n == 1 else 'are'} still to settle. Your version "
            "sits beside each page as a .mine.md file.")


def _draft_unreadable(m, details, r):
    return f"I couldn't compare your draft with the copy you opened: {r.plain(m['why']).rstrip('.')}."


def _vault_id(m, details, r):
    return ("The browser could lose your saved marks, layout and Ask conversations if the plan is renamed, because "
            "the plan has no fixed name of its own yet. Want me to give it one? What was saved moves over once.")


def _summary(m, details, r):
    saved = m["out"].replace("\\", "/").rsplit("/", 1)[-1]
    return (f"The page for {r.plain(m['title'])} is ready: {_plural(m['apps'], 'app')}, "
            f"{_plural(m['cons'], 'contract')}, {_plural(m['unk'], 'open question')}, {_plural(m['epics'], 'epic')} "
            f"and {_plural(m['flows'], 'flow')}, as of {r.plain(m['today'])}. It's saved as {saved}.")


# kind -> (what the head line looks like, what the lead hears). Order matters only where two patterns could both
# match; each pattern is anchored on the build's own fixed words, so none does today.
KINDS = {
    "first build": (r"first build: wrote the pinned positions", _first_build),
    "pinned new": (r"pinned new positions in (?P<file>.+?): (?P<names>.+)$", _pinned_new),
    "moved": (r"moved (?P<names>.+?) to the nearest free cell in ", _moved),
    "computed": (r"computed positions for (?P<names>.+?); nothing keeps them", _computed),
    "link left out": (r"a link was left out, (?P<path>[^:]+): (?P<why>.*)$", _link_left_out),
    "design found": (r"(?P<app>.+?): using the design (?P<path>.+?), found (?P<how>.+)$", _design_found),
    "no design": (r"no design yet for (?P<apps>.+?), so Inside this app", _no_design),
    "warning": (r"warning: (?P<rest>.+)$", _warning),
    "design status": (r"(?P<app>\S+) design (?P<path>.+?): (?P<status>[^,]+), (?P<n>\d+) components, "
                      r"(?P<bad>\d+) things it could not read$", _design_status),
    "plan found": (r"(?P<app>.+?): using the build plan (?P<path>.+?), found (?P<how>.+)$", _plan_found),
    "no plan": (r"no build plan yet for (?P<apps>.+?); ", _no_plan),
    "plan status": (r"(?P<app>\S+) build plan (?P<file>.+?): (?P<status>.+?), (?P<stories>\d+) stories, (?P<tasks>\d+) tasks, "
                    r"(?P<points>\d+) points, (?P<bad>\d+) things it could not read$", _plan_status),
    "icon": (r"(?P<key>.+?) asks for icon: (?P<icon>.+?), which is not in the built-in set", _icon),
    "page far away": (r"no Open the file links, ", _page_far_away),
    "design far away": (r"no Open the design doc link for (?P<app>\S+), ", _design_far_away),
    "plan far away": (r"no Open the plan or Tickets link for (?P<app>\S+), ", _plan_far_away),
    "gitignore": (r"this vault's \.gitignore lists (?P<page>\S+?),? ", _gitignore),
    "assets": (r"assets from (?P<source>.+?), provider (?P<provider>\S+), \d+ slots, \d+ KB inlined, 0 fell back", _assets),
    "assets fell back": (r"assets from (?P<source>.+?), provider (?P<provider>\S+), \d+ slots, \d+ KB inlined, "
                         r"(?P<fell>[1-9]\d*) fell back", _assets_fell_back),
    "party": (r"(?P<cons>\S+) names its provider in running text, \"(?P<said>.*)\", so the map draws \"(?P<title>.*?)\"\.",
              _party),
    "draft changed": (r"draft: (?P<n>\d+) pages? changed since the copy you opened", _draft_changed),
    "draft conflicts": (r"draft: (?P<n>\d+) conflicts? from the last re-open", _draft_conflicts),
    "draft unreadable": (r"draft: cannot compare with the baseline, (?P<why>.+)$", _draft_unreadable),
    "vault id": (rf"this vault has no {VAULT_ID_KEY} in \.vela\.yaml, .*Add the line `(?P<line>[^`]+)`", _vault_id),
    "summary": (r"wrote (?P<out>.+?) for (?P<ini>\S+) (?P<title>.*?): (?P<apps>\d+) apps, (?P<cons>\d+) contracts, "
                r"(?P<unk>\d+) unknowns, (?P<epics>\d+) epics, (?P<flows>\d+) flows, as of (?P<today>[\d-]+)\.$", _summary),
}
_COMPILED = {kind: re.compile(pattern) for kind, (pattern, _) in KINDS.items()}


def _match(head):
    for kind, pattern in _COMPILED.items():
        found = pattern.match(head)
        if found:
            return kind, found
    return None, None


def kind_of(entry):
    """Which kind of build line `entry` is, or None for a line no row knows yet."""
    return _match(_head_and_details(entry)[0])[0]


def lead_line(entry, resolver):
    """What the lead hears for one report entry (its head line and the indented lines under it)."""
    head, details = _head_and_details(entry)
    kind, found = _match(head)
    if kind is None:
        return " ".join(resolver.plain(part) for part in [head, *details])
    return KINDS[kind][1](found.groupdict(), details, resolver)
