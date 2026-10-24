"""`add fr`: a functional requirement, `### CAP-nnn.FRn <short name>` under `## Functional requirements` on its
capability page (requirements section 3; REQUIREMENTS-IN-VAULT).

- **Numbered after the highest**, on the page and on every open branch: numbers are never reused, because a dropped
  requirement's links and release rows must not start pointing at a new one.
- **The heading format**: the capability's ID, `.FR<n>`, and a short name of at most six words.
- **`**State:** assumption`** at most: a new requirement starts as not decided yet; `vela decide` settles it.
- **`**Source:**`** links the capture the lead said it in, so the requirement keeps the words it came from.
- **Criteria** are plain sentences, one bullet each, with a `- Trace:` line under any that cites an item; a requirement
  with more than about seven criteria is two requirements (the skill proposes the split before writing).
"""
import re

from vela.decisions import textedit
from vela.decisions.schema import Write

SECTION = "Functional requirements"
STATES = ("inkling", "assumption")

FIELDS = {"capability": "the capability's ID, CAP-nnn",
          "name": "the requirement's short name: at most six words",
          "need": "one paragraph: what the business needs, in the domain's words",
          "criteria": "the acceptance criteria, one plain sentence each",
          "traces": "for each criterion, the IDs it cites (a list of lists, in order; optional)",
          "state": "inkling or assumption (default)",
          "capture": "the capture the lead said it in: the requirement's Source"}
REQUIRED = ("capability", "name", "need", "capture")
EXAMPLE = {"capability": "CAP-004", "name": "Refund a canceled booking",
           "need": "A guest who cancels in time gets their money back.", "capture": "^c07",
           "criteria": ["A guest who cancels 48 hours ahead sees a pending refund at once."]}


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    page = textedit.find(vault, str(item["capability"]))
    if page is None or page[1] is not None:
        found.append(textedit.refusal("add-fr-capability", "I can't find that capability's page.",
                                      f"{item['capability']} is no capability page in this vault."))
    if (item.get("state") or "assumption") not in STATES:
        found.append(textedit.refusal("add-fr-state", "A requirements session writes a requirement as assumed at most.",
                                      "state is inkling or assumption; it's settled with vela decide.",
                                      override="none: write it at assumption, then vela decide"))
    if len(item.get("traces") or []) > len(item.get("criteria") or []):
        found.append(textedit.refusal("add-fr-traces", "There are more trace lines than criteria.",
                                      "Give one traces entry per criterion, in order."))
    refusal = textedit.heading_refusal(item["name"])
    return found + ([refusal] if refusal else [])


def highest(capability, texts):
    pattern = re.compile(rf"\b{re.escape(capability)}\.FR(\d+)\b")
    return max((int(n) for text in texts for n in pattern.findall(text)), default=0)


def apply(item, vault, record):
    capability = str(item["capability"])
    path = textedit.find(vault, capability)[0]
    number = highest(capability, list(textedit.texts(vault).values()) + list(vault.branch_texts or ())) + 1
    ident = f"{capability}.FR{number}"
    state = item.get("state") or "assumption"
    lines = [f"### {ident} {item['name'].strip()}", "", textedit.inline(item["need"]), "", f"- **State:** {state}",
             f"- **Source:** {textedit.capture_ref(record, item['capture'])}"]
    traces = list(item.get("traces") or [])
    if item.get("criteria"):
        lines.append("")
    for index, criterion in enumerate(item.get("criteria") or []):
        lines.append(f"- {textedit.inline(criterion)}")
        cited = traces[index] if index < len(traces) else []
        if cited:
            lines.append("  - Trace: " + ", ".join(map(str, cited)))
    page = textedit.insert_block(vault.text(path), SECTION, lines, before=("History",))
    heading = f"{ident} {item['name'].strip()}"
    rec = textedit.add_change(textedit.record_text(record, vault), ident, "-", state,
                              textedit.capture_link(record.id, item["capture"]))
    rec = textedit.mark_if_unmarked(rec, item["capture"], textedit.keep_mark(textedit.basename(path), heading, ident,
                                                                             state))
    return [Write(path, page)] + textedit.record_writes(record, vault, rec)
