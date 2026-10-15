"""`add epic`: a new epic's skeleton, or one acceptance criterion added to an epic (epics skill; CONVENTIONS "Epics
and traceability").

- **One owning team.** An epic is one team's block of work; two owning teams is two epics, because a criterion two
  teams own is one nobody is accountable for. A second team is refused, never merged into the line.
- **The template.** A new epic is written in the template's order (title, `**Owning team:**`, `## Who this is for and
  what changes`, `## Done when`, `## History`) with its frontmatter lists, `state: draft`, and a tracker link left to
  the skill. The summary, the people and the criteria are the session's to write.
- **AC numbers are written, never counted.** A new criterion takes the number after the highest the epic has ever
  written (struck criteria keep theirs, and a number another open branch wrote for this epic counts too), so
  `EPC-nnn.ACn` keeps meaning the same criterion however many are added, moved or struck. Counting the headings would
  hand out a struck criterion's number again. This is the thing models get wrong, so code does it.
- **The Trace line** is written by code, `- Trace: <IDs, requirement first>  ·  AC<n>  ·  [concern] ...`, under the
  criterion's sentences; a concern marker names a concern page that exists.
"""
import re

from vela.decisions import textedit
from vela.decisions.schema import Write

FOLDER = "13-epics"
DOT = "  ·  "
HANDLE_IN = re.compile(r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9._-]+)?")

FIELDS = {"id": "an existing epic's ID to add a criterion to; leave null for a new epic",
          "title": "a new epic's title, in plain words",
          "team": "the one owning team's handle",
          "apps": "the APP- IDs it touches",
          "delivers": "what it builds or changes: capabilities, provider-side contracts, goals",
          "consumes": "contracts it builds a client for",
          "flows": "the FLO- IDs it runs in",
          "criterion": "the criterion's heading: a short plain phrase",
          "says": "one or two sentences a tester could read aloud, under the criterion's heading",
          "trace": "the IDs the criterion traces to, requirement first, at least one contract or flow",
          "concerns": "concern names for its markers, such as testing (for concern-testing)",
          "capture": "the capture where the lead agreed to it",
          }
REQUIRED = ()
EXAMPLE = {"title": "Sell at the till", "team": "@till-team", "apps": ["APP-till"], "delivers": ["CAP-001"],
           "criterion": "A sale is recorded", "says": "The till records the sale.", "trace": ["CAP-001.FR1", "CON-001"],
           "concerns": ["testing"]}


def teams(item):
    value = item.get("team") or []
    values = value if isinstance(value, list) else [value]
    return [handle for v in values for handle in HANDLE_IN.findall(str(v))] or [str(v) for v in values if v]


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if item.get("id"):
        located = textedit.find(vault, str(item["id"]))
        if located is None or located[1] is not None:
            found.append(textedit.refusal("add-epic-missing", "I can't find that epic, so I added nothing to it.",
                                          f"{item['id']} is no epic page in this vault; leave id out for a new epic."))
        if not item.get("criterion"):
            found.append(textedit.refusal("decision-unfilled", "I still need one of your answers before I can file "
                                                               "these.", "Adding to an epic needs criterion."))
        if item.get("title") or item.get("team"):
            found.append(textedit.refusal("add-epic-fields", "That mixes a new epic with an existing one.",
                                          "Give title and team for a new epic only, without id."))
    else:
        if not item.get("title") or not item.get("apps"):
            found.append(textedit.refusal("decision-unfilled", "I still need one of your answers before I can file "
                                                               "these.", "A new epic needs title, team and apps."))
        owners = teams(item)
        if len(owners) > 1:
            found.append(textedit.refusal("epic-one-team", "An epic belongs to one team; with two, I'd split it in "
                                                           "two.",
                                          f"It names {len(owners)} owning teams; offer the cut as two epics, one per "
                                          "team.", override="none in the grammar: an epic page has one Owning team"))
        elif not owners:
            found.append(textedit.refusal("decision-unfilled", "I still need one of your answers before I can file "
                                                               "these.", "A new epic needs team: its owning team."))
    for name in item.get("concerns") or []:
        if textedit.page_path(vault, f"concern-{name}") is None:
            found.append(textedit.refusal("add-epic-concern", "One of those concerns isn't one this vault has.",
                                          f"There is no concern-{name} page; use a concern page's name."))
    if (item.get("says") or item.get("trace")) and not item.get("criterion"):
        found.append(textedit.refusal("add-epic-criterion", "I need the criterion's short heading too.",
                                      "Give criterion with says and trace."))
    return found


def highest_ac(text, epic_id, branch_texts):
    numbers = [int(n) for n in re.findall(r"(?<![\w.])AC(\d+)\b", _trace_text(text))]
    numbers += [int(n) for n in _old_shape_numbers(text)]
    for other in branch_texts:
        numbers += [int(n) for n in re.findall(rf"\b{re.escape(epic_id)}\.AC(\d+)\b", other)]
    return max(numbers, default=0)


def _trace_text(text):
    return "\n".join(line for line in text.split("\n") if re.match(r"^\s*- (?:\*\*)?Trace:?(?:\*\*)?", line))


def _old_shape_numbers(text):
    """The numbers of a first-shape epic's criteria: numbered lines under `## Epic acceptance criteria`."""
    found, inside = [], False
    for line in text.split("\n"):
        if line.startswith("## "):
            inside = line[3:].strip().lower() == "epic acceptance criteria"
        elif inside:
            match = re.match(r"^(\d+)\.\s", line)
            if match:
                found.append(match.group(1))
    return found


def criterion_lines(item, number):
    parts = [", ".join(str(t) for t in item.get("trace") or []), f"AC{number}",
             " ".join(f"[{c}]" for c in item.get("concerns") or [])]
    lines = [f"### {textedit.inline(item['criterion']).strip()}", ""]
    if item.get("says"):
        lines += [textedit.inline(item["says"]), ""]
    return lines + ["- Trace: " + DOT.join(p for p in parts if p)]


def _list(values):
    return "[" + ", ".join(str(v) for v in values or []) + "]"


def new_epic(item, vault, record):
    ident = textedit.new_id(item, vault, "EPC")
    title = str(item["title"]).strip()
    team = teams(item)[0]
    path = f"{FOLDER}/{ident}-{textedit.slug(title)}.md"
    lines = ["---", f"id: {ident}", "type: epic", f"title: {textedit.yaml_value(title)}", "state: draft",
             f'owner: "{team}"', "authored: mixed", f"apps: {_list(item.get('apps'))}",
             f"delivers: {_list(item.get('delivers'))}", f"consumes: {_list(item.get('consumes'))}"]
    if item.get("flows"):
        lines.append(f"flows: {_list(item['flows'])}")
    lines += ["---", "", f"# {ident} {title}", "", f"**Owning team:** {team}", "",
              "## Who this is for and what changes", "", "## Done when", ""]
    if item.get("criterion"):
        lines += criterion_lines(item, 1) + [""]
    lines += ["## History", ""]
    return ident, path, "\n".join(lines).rstrip("\n") + "\n"


def apply(item, vault, record):
    rec = textedit.record_text(record, vault)
    if item.get("id"):
        ident = str(item["id"])
        path = textedit.find(vault, ident)[0]
        text = vault.text(path)
        number = highest_ac(text, ident, getattr(vault, "branch_texts", ()) or ()) + 1
        text = textedit.insert_block(text, "Done when", criterion_lines(item, number),
                                     before=("Traces to", "Depends on", "History"))
        return [Write(path, text)] + textedit.record_writes(record, vault, rec)
    ident, path, text = new_epic(item, vault, record)
    if item.get("capture"):
        rec = textedit.add_change(rec, ident, "-", "draft", textedit.capture_link(record.id, item["capture"]))
    return [Write(path, text)] + textedit.record_writes(record, vault, rec)
