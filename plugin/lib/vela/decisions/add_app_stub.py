"""`add app-stub`: a stub page for an app of the picked cut, `05-building-blocks/<slug>-building-blocks.md` (boundary
section 2).

- **Every later link has a page to point at.** A stub is written for each `new` or `changed` app of the cut before any
  sheet is read back, so a link to it never dangles and an app the session doesn't reach is never lost: `vela next`
  sends a stub (a page with `schema.BOUNDARY_STUB_LINE` and no containers table) back to Boundary.
- **The exact stub line** under the title, `schema.BOUNDARY_STUB_LINE`, which boundary section 4 replaces. Exact,
  because `vela next` matches it to find the stubs.
- **Frontmatter** as CONVENTIONS "Frontmatter" requires for `app-building-blocks`, at `state: inkling` and
  `stage: boundaries` (a new or changed app needs a stage), with `domain` when the lead named one.
- **An `unexamined` row on each concern page**: nobody has looked yet, and saying so is what makes the gap visible
  (an app with no row only counts as unexamined by default).
- **A `## Changes` row** `| APP-<slug> | - | inkling | ... |` citing the capture of the picked cut.
"""
import re

from vela import parse, schema as vault_schema
from vela.decisions import add_unknown, textedit
from vela.decisions.schema import Write

FOLDER = "05-building-blocks"
CHANGES = ("new", "changed")
SLUG = re.compile(r"^[a-z][a-z0-9-]*$")

FIELDS = {"slug": "the app's lower-case slug: its ID is APP-<slug>, its page <slug>-building-blocks.md",
          "name": "the app's plain name, its page title",
          "change": "new or changed (only these get a stub)",
          "owner": "the handle of the team that will own it, or the lead's until one is named",
          "domain": "the business area the lead named for it (optional)",
          "capture": "the capture of the picked cut"}
REQUIRED = ("slug", "name", "change", "owner")
EXAMPLE = {"slug": "desk", "name": "Desk", "change": "new", "owner": "@desk-team", "capture": "^c12"}


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if not SLUG.match(str(item["slug"])):
        found.append(textedit.refusal("add-stub-slug", "That app's short name won't work as a page name.",
                                      f"slug {item['slug']!r} must be lower-case letters, digits and dashes."))
    elif textedit.find(vault, f"APP-{item['slug']}") or textedit.page_path(vault, f"{item['slug']}-building-blocks"):
        found.append(textedit.refusal("add-stub-exists", "That app already has a page, so I left it as it is.",
                                      f"APP-{item['slug']} exists; read its sheet back instead of writing a stub.",
                                      override="none: a page is never replaced by a stub"))
    if item["change"] not in CHANGES:
        found.append(textedit.refusal("add-stub-change", "Only a new or changed app gets a stub.",
                                      f"change {item['change']!r}: an integrated or unchanged app gets its slim page "
                                      "instead."))
    if not add_unknown.HANDLE.match(str(item["owner"])):
        found.append(textedit.refusal("add-owner", "I need a handle for whoever owns that app.",
                                      f"owner {item['owner']!r} is not a handle."))
    return found


def page_text(item, vault):
    config = vault.model.config or {}
    lines = ["---", f"id: APP-{item['slug']}", "type: app-building-blocks", f"title: {textedit.yaml_value(item['name'])}"]
    if config.get("initiative"):
        lines.append(f"initiative: {config['initiative']}")
    lines += ["state: inkling", f"change: {item['change']}", "stage: boundaries", f'owner: "{item["owner"]}"',
              "authored: authored"]
    if item.get("domain"):
        lines.append(f"domain: {textedit.yaml_value(item['domain'])}")
    return "\n".join(lines + ["---", "", f"# {item['name']}", "", vault_schema.BOUNDARY_STUB_LINE]) + "\n"


def apply(item, vault, record):
    name = f"{item['slug']}-building-blocks"
    writes = [Write(f"{FOLDER}/{name}.md", page_text(item, vault))]
    for concern in sorted(vault.model.of_type("concern"), key=lambda p: p.path):
        text = vault.text(concern.path)
        lines = text.split("\n")
        header = textedit.find_table(lines, ("App", "State"))
        if header is None:
            continue
        width = len(parse.split_row(lines[header]))
        cells = [f"[[{name}\\|{item['name']}]]", "unexamined"] + [""] * max(0, width - 2)
        writes.append(Write(concern.path, textedit.add_row(text, ("App", "State"), textedit.row(*cells))))
    rec = textedit.record_text(record, vault)
    if item.get("capture"):
        rec = textedit.add_change(rec, f"APP-{item['slug']}", "-", "inkling",
                                  textedit.capture_link(record.id, item["capture"]))
    return writes + textedit.record_writes(record, vault, rec)

