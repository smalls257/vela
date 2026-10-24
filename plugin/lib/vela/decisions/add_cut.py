"""`add cut`: the picked cut, under `## <the picked cut>` on `05-building-blocks/05-building-blocks.md`, with the apps
it names and its `**Options considered:**` bullet (boundary section 2; plan 2.13).

- **The apps, each with its `change`** (`new`, `changed`, `integrated`, `unchanged` or `retired`), one line each, so
  the stubs that follow have a list to come from.
- **`- **Options considered:** <picked cut> (picked); <cut>: rejected, <reason>; ...`**, the page-level form
  CONVENTIONS gives: a cut is a choice between ways to split the direction, and the rejected ones keep their reasons so
  a later session can see what was weighed and why it lost. A pick with no rejected option is refused: a cut is
  chosen between ways, so the plan names the real alternative it set aside.
- **The capture of the pick** is marked at once, `→ keep: [[05-building-blocks#<cut>|cut]] (assumption)`: the cut is
  believed, not decided, until it's settled.
"""
from vela.decisions import options_line, textedit
from vela.decisions.schema import Write

PAGE = "05-building-blocks"
CHANGES = ("new", "changed", "integrated", "unchanged", "retired")

FIELDS = {"name": "the picked cut's name: its heading",
          "apps": "each app the cut names, as \"<app name>=<change>\"",
          "rejected": "each rejected cut, as \"<cut>: <the reason it lost>\"",
          "capture": "the capture where the lead picked it"}
REQUIRED = ("name", "apps", "rejected")
EXAMPLE = {"name": "Desk beside the till", "apps": ["Desk=new", "Till=changed"],
           "rejected": ["One till app: the desk team ships on its own schedule"], "capture": "^c12"}


def apps(item):
    """[(name, change)] from the "<name>=<change>" strings."""
    return [tuple(part.strip() for part in str(a).rsplit("=", 1)) for a in item.get("apps") or []]


def rejected(item):
    return [tuple(part.strip() for part in str(r).split(":", 1)) for r in item.get("rejected") or []]


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    bad = [a for a in apps(item) if len(a) != 2 or a[1] not in CHANGES or not a[0]]
    if bad:
        found.append(textedit.refusal("add-cut-apps", "I couldn't tell how each app in the cut changes.",
                                      f"Each app is \"<name>=<change>\", change one of {', '.join(CHANGES)}."))
    if any(len(r) != 2 or not all(r) for r in rejected(item)):
        found.append(textedit.refusal("add-cut-rejected", "I need the reason each other cut lost.",
                                      "Each rejected cut is \"<cut>: <reason>\"."))
    if textedit.page_path(vault, PAGE) is None:
        found.append(textedit.refusal("add-cut-page", "The building blocks page is missing.",
                                      "05-building-blocks/05-building-blocks.md holds the picked cut."))
    if any(c in str(item["name"]) for c in "#|^[]"):
        found.append(textedit.refusal("add-heading", "That name won't work as a heading.",
                                      "The cut's name holds none of # | ^ [ ]."))
    return found


def apply(item, vault, record):
    path = textedit.page_path(vault, PAGE)
    name = str(item["name"]).strip()
    lines = [f"- {textedit.inline(app)}: {change}" for app, change in apps(item)]
    lines.append(options_line.picked(textedit.inline(name), [(textedit.inline(cut), textedit.inline(reason))
                                                             for cut, reason in rejected(item)]))
    page = textedit.insert_block(vault.text(path), name, lines)
    rec = textedit.mark_if_unmarked(textedit.record_text(record, vault), item.get("capture"),
                                    textedit.keep_mark(PAGE, name, "cut", "assumption"))
    return [Write(path, page)] + textedit.record_writes(record, vault, rec)
