"""Inside an app: read a team's tech design doc into plain data for the explorer's "Inside this app" view.

    read_design(path, adr_dir=None, context=None) -> dict
    designs_for(["APP-booking=../booking/docs/tech-design/booking.md", ...]) -> {app_id: dict}

The vault stops at the app boundary. What is inside an app is written by the tech-design-grill skill into the team's
own repository, at docs/tech-design/<slug>.md, in the shape TECH-DESIGN-FORMAT.md gives, with ADRs beside it in
docs/adr/ and a CONTEXT.md at the root. This module reads that doc and nothing else: no vault, no network, no
writes. It is for `build.py --design APP-x=path`, which will put the result on the page. DESIGN-INSIDE.md, next to
this file, describes the view and the format gaps that limit it.

A team's doc drifts from the template, so nothing here raises on a malformed doc. Every part that cannot be read
as the format says is still returned as raw text, and the reason goes into the result's `problems` list, with the
line it was found on. The view shows that list; it never fills a hole with a guess it does not name. Only a missing
file, or a `--design` argument that is not `APP-x=path`, raises DesignError: those are the caller's mistakes, and a
design the caller asked for must not quietly turn into "no design".

The trace map is the one part the format does not record as data (see DESIGN-INSIDE.md). It is read from where
vault IDs appear: each component's own bullets, its Responsibility-matrix row and its "<Component> public surface"
section, each entry saying which of those it came from. A `## Trace` table (Target | Component), proposed in
integrations/tech-design-grill/inside-view.patch, is read first when a doc has one, and then the trace is
`recorded`, not `inferred`.
"""
import datetime
import pathlib
import re

import yaml

from planner import allocation, trace
from planner import criteria as criteria_reader
from planner.parse import FENCE, TABLE_SEPARATOR, closes_fence, split_row


class DesignError(Exception):
    """The caller named a design that cannot be read at all."""


STATUSES = ("in-progress", "complete", "complete-with-gaps")
GAP_FIELDS = ("id", "what", "acknowledged_by", "why", "revisit")
DEFERRED_FIELDS = ("id", "section", "reason", "blocks")

# canonical key -> headings that mean it; the first is the template's own spelling
SECTIONS = {
    "overview": ("architecture overview",),
    "boundaries": ("context boundaries",),
    "components": ("components",),
    "matrix": ("responsibility matrix",),
    "data_model": ("data model",),
    "api": ("api contracts",),
    "integrations": ("integration points",),
    "flows": ("key flows",),
    "diagrams": ("supporting diagrams",),
    "tech_stack": ("tech stack",),
    "nfrs": ("nfrs", "non-functional requirements"),
    "constraints": ("constraints register", "constraints"),
    "risks": ("risks & mitigations", "risks and mitigations", "risks"),
    "adrs": ("adrs", "architecture decision records"),
    "operations": ("operations",),
    # not required: OQ-XXX is defined in FRONTMATTER-FORMAT.md, Trace is read when present, and Summary and Walking
    # skeleton open a doc written by /planner:design (plugin/skills/design/TECH-DESIGN-FORMAT.md); older docs lack them
    "open_questions": ("open questions",),
    "trace": ("trace", "traceability"),
    "summary": ("summary",),
    "walking_skeleton": ("walking skeleton",),
}
OPTIONAL_SECTIONS = ("open_questions", "trace", "summary", "walking_skeleton")
TEMPLATE_SECTIONS = [k for k in SECTIONS if k not in OPTIONAL_SECTIONS]
HEADING_TO_KEY = {alias: key for key, aliases in SECTIONS.items() for alias in aliases}
TITLES = {key: aliases[0].capitalize() for key, aliases in SECTIONS.items()}

TABLE_HEADERS = {
    "matrix": ("Component", "Owns", "Reads from", "Writes to"),
    "integrations": ("System", "Direction", "Protocol", "Auth"),
    "tech_stack": ("Layer", "Choice", "Rationale"),
    "nfrs": ("Concern", "Target", "How enforced"),
    "constraints": ("ID", "Constraint", "Source", "Impact"),
    "risks": ("ID", "Risk", "Severity", "Mitigation"),
    "trace": ("Target", "Component"),
}
COMPONENT_FIELDS = ("Responsibility", "Owns", "Depends on", "Exposes")
OPERATIONS_FIELDS = ("Deploy", "Monitor", "Scale")

# What a vault-mode design traces (TECH-DESIGN-FROM-VAULT.md, "Trace targets"): allocated rows, contracts, criteria.
TRACE_ID = re.compile(r"\b(?:CAP-\d{3}\.FR\d+(?:@APP-[a-z0-9-]+)?|EPC-\d{3}\.AC\d+|CON-\d{3})\b")
# What an OQ may challenge: any vault ID. ADR-NNNN is left out on purpose: the team's ADRs share the pattern.
VAULT_ID = re.compile(r"\b(?:CAP-\d{3}(?:\.FR\d+(?:@APP-[a-z0-9-]+)?)?|EPC-\d{3}(?:\.AC\d+)?|CON-\d{3}|UNK-\d{3}"
                      r"|FLO-\d{3}|CST-\d+|INI-\d{3}|APP-[a-z0-9-]+|R-\d{2}|PTY-\d{3}|SV-\d{3}|G\d+)\b")
VAULT_CITE = re.compile(r"\bINI-\d{3}\b[^@\n]*@\s*([0-9a-f]{7,40})\b")
BULLET_FIELD = re.compile(r"^\s*[-*]\s+(?:\*\*)?([A-Za-z][A-Za-z /&-]*?)(?::\*\*|\*\*:|:)\s*(.*)$")
BOLD_FIELD = re.compile(r"^\s*(?:[-*]\s+)?\*\*([A-Za-z][A-Za-z /&-]*?)(?::\*\*|\*\*:)\s*(.*)$")
CHALLENGES = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?challenges(?::\*\*|\*\*:|:)\s*(.*)$", re.I)
OQ_HEADING = re.compile(r"^(OQ-\d{3})\b[:\s.-]*(.*)$")
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
ADR_ID = re.compile(r"\bADR-(\d{4})\b")
ADR_FILE = re.compile(r"^(\d{4})-.+\.md$")
ER_ENTITY = re.compile(r"^\s*([A-Za-z][\w-]*)\s*\{\s*$")
ER_RELATION = re.compile(r"^\s*([A-Za-z][\w-]*)\s+([|}o{.\-]{4,6})\s+([A-Za-z][\w-]*)\s*:\s*\"?([^\"]*)\"?\s*$")
SEQ_PARTICIPANT = re.compile(r"^\s*(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+?))?\s*$")
VAULT_PREREQ = re.compile(r"^(?P<vault>.*?)/?05-building-blocks/(?P<app>[a-z0-9-]+)-building-blocks\.md$")
SPEC = re.compile(r"^(APP-[A-Za-z0-9-]+)=(.+)$")
PERSISTENCE_LABELS = ("persistence", "store", "stores", "storage")


def read_design(path, adr_dir=None, context=None):
    """The design doc at `path` as plain data, with every part it could not read listed in `problems`.

    `adr_dir` defaults to the doc's ../adr (where the template's ADR links point) and `context` to CONTEXT.md at the
    repository root (two levels above docs/tech-design/). A default that is not there is not a problem, because
    both are created lazily; one the caller names and is not there raises DesignError.
    """
    path = pathlib.Path(path)
    if not path.is_file():
        raise DesignError(f"no tech design doc at {path}")
    problems = []
    text = _read_text(path, problems, "file")
    meta, body_start = _frontmatter(text, problems)
    lines = text.split("\n")
    title, sections, extra = _split_sections(lines, body_start, problems)

    design = {
        "path": path.name,  # basename only, to avoid leaking the builder's filesystem paths
        "title": title,
        "frontmatter": _frontmatter_fields(meta, problems),
        "vault": _vault_link(meta, text, problems),
        "summary": _prose_and_mermaid(sections.get("summary")),
        "walking_skeleton": _walking_skeleton(sections.get("walking_skeleton")),
        "overview": _prose_and_mermaid(sections.get("overview")),
        "boundaries": _boundaries(sections.get("boundaries"), problems),
        "components": [],
        "matrix": _table(sections.get("matrix"), "matrix", problems),
        "data_model": _data_model(sections.get("data_model")),
        "api": _api(sections.get("api")),
        "integrations": _table(sections.get("integrations"), "integrations", problems),
        "flows": _diagrams(sections.get("flows")),
        "diagrams": _diagrams(sections.get("diagrams")),
        "tech_stack": _table(sections.get("tech_stack"), "tech_stack", problems),
        "nfrs": _table(sections.get("nfrs"), "nfrs", problems),
        "constraints": _table(sections.get("constraints"), "constraints", problems),
        "risks": _table(sections.get("risks"), "risks", problems),
        "adrs": [],
        "operations": _operations(sections.get("operations"), problems),
        "open_questions": _open_questions(sections.get("open_questions"), problems),
        "extra_sections": extra,
        "context": None,
        "problems": problems,
    }
    for key in TEMPLATE_SECTIONS:
        if key not in sections:
            _problem(problems, None, TITLES[key], f"missing section: ## {TITLES[key]}")
    design["components"] = _components(sections.get("components"), problems)
    _check_components(design, problems)
    design["trace"], design["trace_source"] = _trace(design, sections.get("trace"), problems)
    design["mentions"] = _mentions(lines, body_start, sections)
    design["adrs"] = _adrs(sections.get("adrs"), path, adr_dir, problems)
    design["context"] = _context(path, context, problems)
    _check_status(design, problems)
    return design


def designs_for(args):
    """{app ID: design} for each `APP-x=path` argument, as `build.py --design` will pass them.

    Each design's frontmatter names the app it was written for (its vault prereq); a mismatch with the argument is
    a problem on that design, not an error, so the page can show both.
    """
    out = {}
    for arg in args or []:
        match = SPEC.match(arg.strip())
        if not match:
            raise DesignError(f"--design takes APP-x=path, not {arg!r}")
        app, where = match.group(1), match.group(2)
        if app in out:
            raise DesignError(f"--design names {app} twice")
        design = read_design(where)
        named = design["vault"]["app"]
        if named and named != app:
            _problem(design["problems"], None, "frontmatter",
                     f"--design gives this doc as {app}, but its vault prereq is {named}'s page")
        out[app] = design
    return out


def vault_ids(vault):
    """Every ID a design may cite: the vault's own IDs and initiative, each epic criterion as EPC-nnn.ACn, and each
    allocated row as CAP-nnn.FRn@APP-x."""
    ids = set(vault.known_ids())
    ids.update(p.meta["initiative"] for p in vault.pages if isinstance(p.meta.get("initiative"), str))
    for epic in trace.epics(vault):
        ids.update(f"{epic.id}.AC{n}" for n in epic_criteria_numbers(epic))
    ids.update(f"{row.requirement}@{row.app.id}" for row in allocation.rows(vault) if row.requirement)
    return ids


def trace_targets(vault, app_id):
    """What a vault-mode design of `app_id` must trace, as TECH-DESIGN-FROM-VAULT.md lists it."""
    app = next((a for a in vault.apps if a.id == app_id), None)
    if app is None:
        return set()
    targets = {f"{r.requirement}@{app_id}" for r in allocation.rows(vault) if r.app is app and r.requirement}
    for contract in vault.contracts:
        if contract.page is app or app in vault.consumers(contract):
            targets.add(contract.id)
    for epic in trace.epics(vault):
        if app_id in trace.listed(epic, "apps"):
            targets.update(f"{epic.id}.AC{n}" for n in epic_criteria_numbers(epic))
    return targets


def epic_criteria_numbers(epic):
    """The AC numbers an `EPC-nnn.ACn` reference may name on this epic: the numbers as written on numbered lines, and the
    ids on the Trace lines of headed criteria. Struck ones stay, so a reference to one does not read as invented."""
    return criteria_reader.numbers(epic)


def resolve(design, known, targets=None):
    """What the design cites that the vault does not hold, and, given `targets`, what no component owns.

    {"unresolved": [{id, where}], "untraced": [ids], "acknowledged": {id: gap ID}}: `where` is "trace:<component>"
    or "challenge:<OQ>". An untraced target is acknowledged when a gaps[] entry's `what` names it, or names its epic
    or capability on its own (EPC-039, not EPC-039.AC2), so the view can tell an accepted gap from a missed one.
    """
    unresolved = []
    for component, entries in design["trace"].items():
        unresolved += [{"id": e["id"], "where": f"trace:{component}"} for e in entries if e["id"] not in known]
    for oq in design["open_questions"]:
        unresolved += [{"id": i, "where": f"challenge:{oq['id']}"} for i in oq["challenges"] if i not in known]
    owned = {e["id"] for entries in design["trace"].values() for e in entries}
    untraced = sorted(set(targets or ()) - owned)
    acknowledged = {}
    for target in untraced:
        whole = re.compile(rf"\b{re.escape(target.split('@')[0])}\b")
        parent = re.compile(rf"\b{re.escape(target.split('.')[0])}\b(?!\.)")
        gap = next((g for g in design["frontmatter"]["gaps"]
                    if whole.search(str(g.get("what", ""))) or parent.search(str(g.get("what", "")))), None)
        if gap is not None:
            acknowledged[target] = gap.get("id")
    return {"unresolved": unresolved, "untraced": untraced, "acknowledged": acknowledged}


# --- reading the file -------------------------------------------------------------------------------------------

def _problem(problems, line, section, message):
    problems.append({"line": line, "section": section, "message": message})


def _read_text(path, problems, section):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _problem(problems, None, section, f"{path.name} is not UTF-8 ({exc}); undecodable bytes shown as U+FFFD")
        return raw.decode("utf-8", errors="replace")


def _frontmatter(text, problems):
    """(meta dict, line index where the body starts)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        _problem(problems, 1, "frontmatter", "no YAML frontmatter: the doc does not start with ---")
        return {}, 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        _problem(problems, 1, "frontmatter", "frontmatter is never closed with ---")
        return {}, 0
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        _problem(problems, mark.line + 2 if mark else 1, "frontmatter", f"frontmatter is not valid YAML: {exc}")
        return {}, end + 1
    if not isinstance(meta, dict):
        _problem(problems, 2, "frontmatter", "frontmatter is not a mapping")
        return {}, end + 1
    return meta, end + 1


def _plain(value):
    """YAML values as JSON-safe values: dates become ISO strings."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _entries(meta, key, fields, problems):
    value = meta.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        _problem(problems, None, "frontmatter", f"{key} is not a list")
        return []
    out = []
    for n, entry in enumerate(value, start=1):
        if not isinstance(entry, dict):
            _problem(problems, None, "frontmatter", f"{key}[{n}] is not a mapping: {entry!r}")
            continue
        entry = _plain(entry)
        missing = [f for f in fields if not entry.get(f)]
        if missing:
            _problem(problems, None, "frontmatter",
                     f"{key} entry {entry.get('id', n)} has no {', '.join(missing)}")
        out.append(entry)
    return out


def _frontmatter_fields(meta, problems):
    slug, status = meta.get("slug"), meta.get("status")
    if not slug:
        _problem(problems, None, "frontmatter", "no slug")
    if status not in STATUSES:
        _problem(problems, None, "frontmatter", f"status {status!r} is not one of {', '.join(STATUSES)}")
    if not meta.get("last_session"):
        _problem(problems, None, "frontmatter", "no last_session")
    prereqs = _entries(meta, "prereqs", ("path", "expected_status"), problems)
    return {
        "slug": slug,
        "status": status,
        "gaps": _entries(meta, "gaps", GAP_FIELDS, problems),
        "deferred": _entries(meta, "deferred", DEFERRED_FIELDS, problems),
        "last_session": _plain(meta.get("last_session")),
        "prereqs": prereqs,
        "other": {k: _plain(v) for k, v in meta.items()
                  if k not in ("slug", "status", "gaps", "deferred", "last_session", "prereqs", "vault")},
    }


def _vault_link(meta, text, problems):
    """Which vault app this design answers for, and the vault commit it read.

    The format records neither, so they are read from the prereq path (.../05-building-blocks/<app>-building-blocks.md)
    and from the citations' `INI-nnn ... @ <sha>`: `source` is "inferred". A `vault:` block, as the proposed patch
    adds, is read first, and then `source` is "recorded".
    """
    recorded = meta.get("vault") if isinstance(meta.get("vault"), dict) else None
    if meta.get("vault") is not None and recorded is None:
        _problem(problems, None, "frontmatter", "vault is not a mapping")
    found = None
    for prereq in meta.get("prereqs") or []:
        match = VAULT_PREREQ.match(str(prereq.get("path", ""))) if isinstance(prereq, dict) else None
        if match:
            found = (match, prereq)
            break
    if found is None and recorded is None:
        return {"mode": "requirements", "source": "none", "app": None, "vault_path": None, "building_blocks": None,
                "commits": []}
    app = vault_path = building_blocks = None
    if found:
        match, prereq = found
        app, vault_path, building_blocks = f"APP-{match.group('app')}", match.group("vault") or ".", prereq["path"]
        if prereq.get("expected_status") != "handed_off":
            _problem(problems, None, "frontmatter",
                     f"the vault prereq expects status {prereq.get('expected_status')!r}, not handed_off")
    cited = sorted(set(VAULT_CITE.findall(text)))
    if recorded:
        if found and recorded.get("app") != app:
            _problem(problems, None, "frontmatter", f"vault.app is {recorded.get('app')!r}, the prereq is {app}'s page")
        stray = [c for c in cited if recorded.get("commit") and not str(recorded["commit"]).startswith(c)
                 and not c.startswith(str(recorded["commit"]))]
        if stray:
            _problem(problems, None, "vault link", f"citations name {', '.join(stray)}, not vault.commit")
        return {"mode": "vault", "source": "recorded", "app": recorded.get("app") or app, "vault_path": vault_path,
                "building_blocks": building_blocks, "commits": [str(recorded["commit"])] if recorded.get("commit")
                else cited, "initiative": recorded.get("initiative")}
    if not cited:
        _problem(problems, None, "vault link", "no vault citation names a commit (INI-nnn ... @ <sha>), "
                                               "so links back to the vault cannot be pinned")
    elif len(cited) > 1:
        _problem(problems, None, "vault link", f"the doc cites more than one vault commit: {', '.join(cited)}")
    return {"mode": "vault", "source": "inferred", "app": app, "vault_path": vault_path,
            "building_blocks": building_blocks, "commits": cited}


def _split_sections(lines, start, problems):
    """(title, {key: Section}, [extra headings]): the body cut at its level-2 headings, fences respected."""
    title, sections, extra, current, fence = None, {}, [], None, None
    for i in range(start, len(lines)):
        raw = lines[i]
        opening = FENCE.match(raw)
        if fence:
            fence = None if closes_fence(raw, fence) else fence
        elif opening:
            fence = opening.group(1)
        elif raw.startswith("# ") and title is None:
            title = _title(raw[2:].strip(), i + 1, problems)
            continue
        elif raw.startswith("## "):
            heading = raw[3:].strip()
            key = HEADING_TO_KEY.get(heading.lower())
            if key is None:
                extra.append({"heading": heading, "line": i + 1})
                current = None
                continue
            if key in sections:
                _problem(problems, i + 1, heading, f"## {heading} appears twice; the first is read")
                current = None
                continue
            current = sections[key] = {"heading": heading, "line": i + 1, "lines": []}
            continue
        if current is not None:
            current["lines"].append((i + 1, raw))
    if title is None:
        _problem(problems, None, "title", "no # title")
    return title, sections, extra


def _title(text, line, problems):
    for dash in ("—", "–", " - "):
        if text.startswith("Tech Design") and dash in text:
            return text.split(dash, 1)[1].strip()
    _problem(problems, line, "title", f"title {text!r} is not '# Tech Design — <Title>'")
    return text


# --- section readers --------------------------------------------------------------------------------------------

def _raw(section):
    return "\n".join(t for _, t in section["lines"]).strip() if section else ""


def _blocks(section_lines):
    """Split lines into (kind, language, start line, text) runs: 'fence' or 'text'."""
    out, fence, buf, lang, start = [], None, [], "", None
    for n, raw in section_lines:
        opening = FENCE.match(raw)
        if fence:
            if closes_fence(raw, fence):
                out.append(("fence", lang, start, "\n".join(buf)))
                fence, buf = None, []
            else:
                buf.append(raw)
            continue
        if opening:
            if buf:
                out.append(("text", "", start, "\n".join(buf)))
            fence, lang, buf, start = opening.group(1), opening.group(2).lower(), [], n
            continue
        if not buf:
            start = n
        buf.append(raw)
    if buf:
        out.append(("fence" if fence else "text", lang if fence else "", start, "\n".join(buf)))
    return out


def _prose_and_mermaid(section):
    if not section:
        return {"text": "", "mermaid": []}
    blocks = _blocks(section["lines"])
    text = "\n".join(b[3] for b in blocks if b[0] == "text").strip()
    return {"text": text, "mermaid": [b[3] for b in blocks if b[0] == "fence" and b[1] == "mermaid"]}


def _walking_skeleton(section):
    """{text, fields}: the section's prose, and its `- **Flow:**`, `**Path:**`, `**Stubbed:**`, `**Carries:**` bullets."""
    if not section:
        return {"text": "", "fields": {}}
    fields = {label: value for label, (value, _) in _fields(section["lines"]).items()}
    text = "\n".join(t for _, t in section["lines"] if not BULLET_FIELD.match(t)).strip()
    return {"text": text, "fields": fields}


def _boundaries(section, problems):
    """**Inside the app:** and **Outside the app:**, each running on until the next field or a blank line."""
    out = {"inside": "", "outside": "", "raw": _raw(section)}
    last = None
    for _, raw in section["lines"] if section else []:
        match = BOLD_FIELD.match(raw)
        label = match.group(1).lower() if match else ""
        if label.startswith(("inside", "outside")):
            last = "inside" if label.startswith("inside") else "outside"
            out[last] = match.group(2).strip()
        elif match or not raw.strip():
            last = None
        elif last:
            out[last] = f"{out[last]} {raw.strip()}"
    for side in ("inside", "outside") if section else ():
        if not out[side]:
            _problem(problems, section["line"], "Context boundaries", f"no '**{side.capitalize()} the app:**' line")
    return out


def _subsections(section):
    """[(heading, line, [(n, text)])] for each ### under a section, and the lines before the first."""
    subs, lead, current = [], [], None
    for n, raw in section["lines"] if section else []:
        if raw.startswith("### "):
            current = (raw[4:].strip(), n, [])
            subs.append(current)
        elif current is None:
            lead.append((n, raw))
        else:
            current[2].append((n, raw))
    return subs, lead


def _fields(lines):
    """{label: (value, line)} from `- Label: value` or `- **Label:** value` bullets; indented lines continue one."""
    out, last = {}, None
    for n, raw in lines:
        match = BULLET_FIELD.match(raw)
        if match:
            last = match.group(1).strip()
            out[last] = (match.group(2).strip(), n)
        elif last and raw.startswith(("  ", "\t")) and raw.strip():
            value, line = out[last]
            out[last] = (f"{value} {raw.strip()}", line)
        elif not raw.strip():
            last = None
    return out


def _split_names(value, known=()):
    """'A, B (CON-003, CON-004) and C' -> ['A', 'B (CON-003, CON-004)', 'C']; 'none' -> [].

    A part whose bare name is in `known` (lower case, parentheses dropped) is kept whole, so a system called
    "Consent and identity" is one name and not two."""
    if value.strip().lower().rstrip(".") in ("none", "nothing", "-", "—", ""):
        return []
    parts, depth, buf = [], 0, ""
    for ch in value:
        depth += (ch == "(") - (ch == ")")
        if ch in ",;" and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    out = []
    for part in parts:
        if part.strip() and _bare(part.strip().rstrip(".")) in known:
            out.append(part.strip().rstrip("."))
            continue
        out += [p.strip().rstrip(".") for p in re.split(r"\s+and\s+(?![^(]*\))", part) if p.strip()]
    return out


def _bare(name):
    return re.sub(r"\s*\(.*?\)\s*", " ", name).strip().lower()


def _components(section, problems):
    subs, _ = _subsections(section)
    if section and not subs:
        _problem(problems, section["line"], "Components", "no ### component under ## Components")
    out = []
    for name, line, lines in subs:
        fields = _fields(lines)
        component = {"name": name, "line": line, "container": None, "other": {}}
        for label in COMPONENT_FIELDS:
            key = label.lower().replace(" ", "_")
            value = fields.get(label, ("", None))[0]
            component[key] = value
            if label not in fields:
                _problem(problems, line, f"Components › {name}", f"no '{label}:' bullet")
        component["depends_on_names"] = _split_names(component["depends_on"])
        if "Container" in fields:
            component["container"] = fields["Container"][0]
        component["other"] = {k: v for k, (v, _) in fields.items() if k not in COMPONENT_FIELDS + ("Container",)}
        component["_fields"] = fields
        out.append(component)
    return out


def _table(section, key, problems):
    """[{column: cell}] from the section's first table, columns keyed as snake_case of the template's header."""
    if not section:
        return []
    rows, header, title = [], None, section["heading"]
    lines = section["lines"]
    for i, (n, raw) in enumerate(lines):
        if not raw.lstrip().startswith("|"):
            if header is not None:
                break
            continue
        if header is None:
            if i + 1 < len(lines) and TABLE_SEPARATOR.match(lines[i + 1][1].strip()):
                header = list(split_row(raw))
                expected = TABLE_HEADERS.get(key)
                if expected and tuple(h.lower() for h in header) != tuple(e.lower() for e in expected):
                    _problem(problems, n, title, f"table header is {' | '.join(header)}; "
                                                 f"the format has {' | '.join(expected)}")
            continue
        if TABLE_SEPARATOR.match(raw.strip()):
            continue
        cells = list(split_row(raw))
        if len(cells) != len(header):
            _problem(problems, n, title, f"row has {len(cells)} cells, the header {len(header)}: {raw.strip()}")
        cells = (cells + [""] * len(header))[:len(header)]
        row = {_snake(h): c for h, c in zip(header, cells)}
        row["line"] = n
        rows.append(row)
    if header is None and _raw(section).lower().rstrip(".") not in ("none", ""):
        _problem(problems, section["line"], title, "no table, where the format has one")
    return rows


def _snake(header):
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def _data_model(section):
    """Entities, relationships and stores, best effort, from erDiagram blocks, then ### or bold bullets."""
    out = {"raw": _raw(section), "mermaid": [], "entities": [], "relationships": [], "stores": [],
           "parsed_from": "none"}
    if not section:
        return out
    for kind, lang, _, text in _blocks(section["lines"]):
        if kind != "fence" or lang != "mermaid":
            continue
        out["mermaid"].append(text)
        if text.lstrip().startswith("erDiagram"):
            out["parsed_from"] = "erDiagram"
            _er_diagram(text, out)
    subs, lead = _subsections(section)
    for label, (value, _) in _fields(lead + [x for s in subs for x in s[2]]).items():
        if label.lower() in PERSISTENCE_LABELS:
            out["stores"].append(value)
        elif out["parsed_from"] != "erDiagram" and label[:1].isupper():
            out["entities"].append({"name": label, "fields": [], "text": value})
    if out["parsed_from"] != "erDiagram":
        out["entities"] += [{"name": h, "fields": [], "text": "\n".join(t for _, t in ls).strip()} for h, _, ls in subs]
        out["parsed_from"] = "headings and bullets" if out["entities"] else "none"
    return out


def _er_diagram(text, out):
    entity = None
    for raw in text.split("\n")[1:]:
        line = raw.strip()
        if entity is not None:
            if line == "}":
                entity = None
            elif line:
                parts = line.split()
                entity["fields"].append({"type": parts[0], "name": parts[1] if len(parts) > 1 else "",
                                         "keys": [p for p in parts[2:] if p in ("PK", "FK", "UK")]})
            continue
        match = ER_ENTITY.match(raw)
        if match:
            entity = next((e for e in out["entities"] if e["name"] == match.group(1)), None)
            if entity is None:
                entity = {"name": match.group(1), "fields": [], "text": ""}
                out["entities"].append(entity)
            continue
        match = ER_RELATION.match(raw)
        if match:
            out["relationships"].append({"from": match.group(1), "cardinality": match.group(2),
                                         "to": match.group(3), "label": match.group(4).strip()})
            for name in (match.group(1), match.group(3)):
                if not any(e["name"] == name for e in out["entities"]):
                    out["entities"].append({"name": name, "fields": [], "text": ""})


def _api(section):
    """[{component, heading, raw, operations}], one per '### <Component> public surface'."""
    subs, _ = _subsections(section)
    out = []
    for heading, line, lines in subs:
        component = re.sub(r"\s+public surface\s*$", "", heading, flags=re.I).strip()
        operations = [re.sub(r"^\s*[-*]\s+", "", t).strip() for _, t in lines if re.match(r"^\s*[-*]\s+", t)]
        out.append({"component": component, "heading": heading, "line": line,
                    "raw": "\n".join(t for _, t in lines).strip(), "operations": operations, "_lines": lines})
    return out


def _diagrams(section):
    """[{title, kind, mermaid, participants, line}] for each mermaid block, titled by the ### above it."""
    if not section:
        return []
    out, title = [], None
    subs, lead = _subsections(section)
    for heading, lines in [(None, lead)] + [(h, ls) for h, _, ls in subs]:
        title = heading
        for kind, lang, start, text in _blocks(lines):
            if kind != "fence" or lang != "mermaid":
                continue
            first = text.strip().split("\n", 1)[0].split()
            participants = [{"id": m.group(1), "name": (m.group(2) or m.group(1)).strip()}
                            for m in map(SEQ_PARTICIPANT.match, text.split("\n")) if m]
            out.append({"title": title, "kind": first[0] if first else "", "mermaid": text,
                        "participants": participants, "line": start})
    return out


def _operations(section, problems):
    out = {"raw": _raw(section)}
    if not section:
        return out
    fields = _fields(section["lines"])
    for label in OPERATIONS_FIELDS:
        if label in fields:
            out[label.lower()] = fields[label][0]
        else:
            _problem(problems, section["line"], "Operations", f"no '**{label}:**' bullet")
    out["other"] = {k: v for k, (v, _) in fields.items() if k not in OPERATIONS_FIELDS}
    return out


def _open_questions(section, problems):
    subs, _ = _subsections(section)
    out, seen = [], set()
    for heading, line, lines in subs:
        match = OQ_HEADING.match(heading)
        if not match:
            _problem(problems, line, "Open questions", f"### {heading} is not 'OQ-XXX: <question>'")
            continue
        oq_id = match.group(1)
        if oq_id in seen:
            _problem(problems, line, "Open questions", f"{oq_id} appears twice")
        seen.add(oq_id)
        entry = {"id": oq_id, "title": match.group(2).strip(), "line": line, "what_we_know": "",
                 "what_would_unblock": "", "affects": "", "challenges": [], "challenges_form": None, "other": {}}
        for n, raw in lines:
            challenge = CHALLENGES.match(raw)
            if challenge:
                entry["challenges"] += VAULT_ID.findall(challenge.group(1))
                entry["challenges_form"] = "bold" if "**" in raw else "plain"
                if not VAULT_ID.findall(challenge.group(1)):
                    _problem(problems, n, f"Open questions › {oq_id}",
                             f"challenges: names no vault ID: {challenge.group(1).strip()!r}")
                continue
            field = BOLD_FIELD.match(raw)
            if field:
                key = _snake(field.group(1))
                if key in ("what_we_know", "what_would_unblock", "affects"):
                    entry[key] = field.group(2).strip()
                else:
                    entry["other"][field.group(1)] = field.group(2).strip()
        entry["affects_ids"] = VAULT_ID.findall(entry["affects"])
        out.append(entry)
    return out


# --- cross-section checks ---------------------------------------------------------------------------------------

def _check_components(design, problems):
    names = {c["name"].lower(): c for c in design["components"]}
    systems = {_bare(r.get("system", "")).split(" via ")[0] for r in design["integrations"]}
    for row in design["matrix"]:
        if row.get("component", "").lower() not in names:
            _problem(problems, row["line"], "Responsibility matrix",
                     f"row for {row.get('component')!r}, which is not a ### component")
    in_matrix = {r.get("component", "").lower() for r in design["matrix"]}
    known = set(names) | systems
    for c in design["components"]:
        c["depends_on_names"] = _split_names(c["depends_on"], known)
        if c["name"].lower() not in in_matrix:
            _problem(problems, c["line"], f"Components › {c['name']}", "no Responsibility-matrix row (format rule)")
        c["depends_on_components"], c["depends_on_other"] = [], []
        for name in c["depends_on_names"]:
            if _bare(name) in names:
                c["depends_on_components"].append(names[_bare(name)]["name"])
                continue
            c["depends_on_other"].append(name)
            if _bare(name) not in systems:
                _problem(problems, c["line"], f"Components › {c['name']}",
                         f"depends on {name!r}, which is neither a component nor an integration point")
    for api in design["api"]:
        api["component_found"] = api["component"].lower() in names
        if not api["component_found"]:
            _problem(problems, api["line"], "API contracts",
                     f"### {api['heading']} names no component")


def _trace(design, recorded, problems):
    """({component: [{id, via}]}, 'recorded' | 'inferred' | 'none')."""
    by_component = {c["name"]: {} for c in design["components"]}

    def add(component, vault_id, via):
        by_component.setdefault(component, {}).setdefault(vault_id, [])
        if via not in by_component[component][vault_id]:
            by_component[component][vault_id].append(via)

    source = "inferred"
    if recorded:
        source = "recorded"
        names = {c["name"].lower(): c["name"] for c in design["components"]}
        names["operations"] = "Operations"  # the proposed owner of a criterion met by running the service
        for row in _table(recorded, "trace", problems):
            ids = TRACE_ID.findall(row.get("target", ""))
            for owner in _split_names(row.get("component", "")):
                if owner.lower() not in names:
                    _problem(problems, row["line"], "Trace", f"{owner!r} is not a ### component")
                for vault_id in ids:
                    add(names.get(owner.lower(), owner), vault_id, "trace table")
    for c in design["components"]:
        for label, (value, _) in c.pop("_fields").items():
            for vault_id in TRACE_ID.findall(value):
                add(c["name"], vault_id, label.lower())
    for row in design["matrix"]:
        name = next((c["name"] for c in design["components"] if c["name"].lower() == row.get("component", "").lower()),
                    None)
        for column in ("owns", "reads_from", "writes_to"):
            for vault_id in TRACE_ID.findall(row.get(column, "")) if name else []:
                add(name, vault_id, f"matrix {column.replace('_', ' ')}")
    for api in design["api"]:
        name = next((c["name"] for c in design["components"] if c["name"].lower() == api["component"].lower()), None)
        for _, raw in api.pop("_lines") if name else []:
            for vault_id in TRACE_ID.findall(raw):
                add(name, vault_id, "api contracts")
    for api in design["api"]:
        api.pop("_lines", None)
    out = {name: [{"id": i, "via": via} for i, via in sorted(ids.items())] for name, ids in by_component.items()}
    if not any(out.values()):
        source = "none"
        if design["vault"]["mode"] == "vault":
            _problem(problems, None, "trace", "no component cites a trace target (CAP-nnn.FRn@APP-x, CON-nnn, "
                                             "EPC-nnn.ACn), so nothing links back to the vault")
    return out, source


def _mentions(lines, start, sections):
    """{vault ID: [section titles]} for every vault ID the body names, so an ID cited outside a component shows."""
    where = {}
    by_line = {n: s["heading"] for s in sections.values() for n, _ in s["lines"]}
    for i in range(start, len(lines)):
        for vault_id in VAULT_ID.findall(lines[i]):
            heading = by_line.get(i + 1, "title")
            if heading not in where.setdefault(vault_id, []):
                where[vault_id].append(heading)
    return dict(sorted(where.items()))


def _check_status(design, problems):
    fm = design["frontmatter"]
    open_ids = [oq["id"] for oq in design["open_questions"]]
    if fm["status"] == "complete" and open_ids:
        _problem(problems, None, "frontmatter", f"status is complete with open questions: {', '.join(open_ids)}")
    if fm["status"] == "complete-with-gaps" and not fm["gaps"]:
        _problem(problems, None, "frontmatter", "status is complete-with-gaps but gaps[] is empty")
    if fm["status"] != "complete-with-gaps" and fm["gaps"]:
        _problem(problems, None, "frontmatter", f"gaps[] is set but status is {fm['status']!r}")
    named = set()
    for gap in fm["gaps"]:  # the proposed `oq:` field, else an OQ-XXX the `what` line names
        for oq in [gap["oq"]] if gap.get("oq") else re.findall(r"\bOQ-\d{3}\b", str(gap.get("what", ""))):
            named.add(oq)
            if oq not in open_ids:
                _problem(problems, None, "frontmatter", f"gap {gap.get('id')} names {oq}, which is not in the doc")
    for oq in open_ids:
        if fm["status"] == "complete-with-gaps" and oq not in named:
            _problem(problems, None, "frontmatter", f"{oq} is open but no gaps[] entry names it")


# --- ADRs and CONTEXT.md ----------------------------------------------------------------------------------------

def _adrs(section, doc, adr_dir, problems):
    default = doc.parent.parent / "adr"
    if adr_dir is not None and not pathlib.Path(adr_dir).is_dir():
        raise DesignError(f"no ADR directory at {adr_dir}")
    adr_dir = pathlib.Path(adr_dir) if adr_dir is not None else default
    out, listed = [], set()
    for n, raw in section["lines"] if section else []:
        link = MD_LINK.search(raw)
        if not link:
            continue
        number = ADR_ID.search(link.group(1))
        title = re.sub(r"^[\s—–-]+", "", raw[link.end():]).strip()
        target = (doc.parent / link.group(2)).resolve()
        entry = {"id": link.group(1), "title": title, "href": link.group(2), "line": n, "found": target.is_file()}
        if not number:
            _problem(problems, n, "ADRs", f"link text {link.group(1)!r} is not ADR-NNNN")
        if entry["found"]:
            listed.add(target)
            entry.update(_read_adr(target, problems))
        else:
            _problem(problems, n, "ADRs", f"{link.group(1)} links to {link.group(2)}, which is not there")
        out.append(entry)
    if adr_dir.is_dir():
        for path in sorted(adr_dir.iterdir()):
            if ADR_FILE.match(path.name) and path.resolve() not in listed:
                _problem(problems, None, "ADRs", f"{path.name} is in {adr_dir.name}/ but not listed under ## ADRs")
    return out


def _read_adr(path, problems):
    text = _read_text(path, problems, f"ADR {path.name}")
    lines = text.split("\n")
    out = {"file": path.name, "adr_title": "", "status": "", "date": "", "slug": "", "context": "", "decision": "",
           "alternatives": [], "consequences": {}}
    section = None
    sections = {}
    for raw in lines:
        heading = re.match(r"^#\s+ADR-\d{4}:\s*(.+)$", raw)
        if heading:
            out["adr_title"] = heading.group(1).strip()
            continue
        if raw.startswith("## "):
            section = raw[3:].strip().lower()
            sections[section] = []
            continue
        if section is None:
            field = BOLD_FIELD.match(raw)
            if field and field.group(1).lower() in ("status", "date", "slug"):
                out[field.group(1).lower()] = field.group(2).strip()
        else:
            sections[section].append(raw)
    if not out["adr_title"]:
        _problem(problems, 1, f"ADR {path.name}", "first heading is not '# ADR-NNNN: <Title>'")
    for key in ("status", "date"):
        if not out[key]:
            _problem(problems, None, f"ADR {path.name}", f"no **{key.capitalize()}:** line")
    for key in ("context", "decision", "alternatives considered", "consequences"):
        if key not in sections:
            _problem(problems, None, f"ADR {path.name}", f"no ## {key.capitalize()} section")
    out["context"] = "\n".join(sections.get("context", [])).strip()
    out["decision"] = "\n".join(sections.get("decision", [])).strip()
    for raw in sections.get("alternatives considered", []):
        match = re.match(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*[—–-]*\s*(.*)$", raw)
        if match:
            out["alternatives"].append({"option": match.group(1).strip(), "why_not": match.group(2).strip()})
    out["consequences"] = {k.lower(): v for k, (v, _) in
                           _fields([(0, r) for r in sections.get("consequences", [])]).items()}
    return out


def _context(doc, context, problems):
    if context is not None and not pathlib.Path(context).is_file():
        raise DesignError(f"no CONTEXT.md at {context}")
    path = pathlib.Path(context) if context is not None else doc.parent.parent.parent / "CONTEXT.md"
    if not path.is_file():
        return None
    text = _read_text(path, problems, "CONTEXT.md")
    out = {"path": path.name, "glossary": [], "boundaries": {}}  # basename only, to avoid leaking the builder's filesystem paths
    section, term = None, None
    for raw in text.split("\n"):
        if raw.startswith("## "):
            section, term = raw[3:].strip().lower(), None
        elif raw.startswith("### ") and section == "glossary":
            term = {"term": raw[4:].strip(), "definition": "", "not_to_be_confused_with": "", "examples": ""}
            out["glossary"].append(term)
        else:
            field = BOLD_FIELD.match(raw)
            if field and term is not None and section == "glossary":
                term[_snake(field.group(1))] = field.group(2).strip()
            elif field and section == "boundaries":
                out["boundaries"][_snake(field.group(1))] = field.group(2).strip()
    if not out["glossary"]:
        _problem(problems, None, "CONTEXT.md", "no ### term under ## Glossary")
    return out
