"""`add slice`: a slice page, `slices/SLC-nnn-<slug>.md` (releases section 3; CONVENTIONS "Slices").

- Numbered `SLC-nnn` past every open branch; the tracer is the one slice with no `**After:**`.
- The facts are bullets under the title in the order CONVENTIONS gives (`**Flows:**`, `**After:**`, `**Ships switched
  off:**`, `**Done when:**`, `**Owner:**`, `**Milestone:**`), then `## Not in this slice` and `## History` with a dated
  line saying what it was written from.
- **No `**Status:**`**: a grill sets `planned`, and the later statuses are the teams' to set; a slice page written
  with a status would claim a step nobody took.
- **No joins**: they are read from the flows' steps, so a join missing from a slice means a step missing from a flow,
  and boundary is where it gets drawn.
- Each flow named must be a flow page in the vault, linked by its ID, and each `after` a slice that exists.
- The capture, when given, gets the `## Changes` row (`- -> new`) and its keep mark.
"""
from vela.decisions import textedit
from vela.decisions.schema import Write

FOLDER = "slices"
BULLETS = (("flows", "Flows"), ("after", "After"), ("ships_switched_off", "Ships switched off"),
           ("done_when", "Done when"), ("owner", "Owner"), ("milestone", "Milestone"))

FIELDS = {"title": "the journey, in the lead's words",
          "flows": "the FLO- IDs the journey runs through",
          "after": "the SLC- IDs it comes after (none for the tracer)",
          "ships_switched_off": "how it ships switched off, and who holds the switch",
          "done_when": "the journey that has to pass, and where",
          "owner": "the slice owner's handle",
          "milestone": "the release that lists it, if one does",
          "capture": "the capture it was written from",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("title", "flows")
EXAMPLE = {"title": "The digest reaches a pilot user", "flows": ["FLO-002"], "after": ["SLC-001"],
           "ships_switched_off": "a per-user flag", "done_when": "the digest journey passes", "owner": "@lead",
           "capture": "^c12"}


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    for field, prefix in (("flows", "FLO"), ("after", "SLC")):
        missing = [i for i in item.get(field) or [] if textedit.find(vault, str(i)) is None]
        if missing:
            found.append(textedit.refusal("add-slice-link", "A slice names something the vault doesn't hold, so I "
                                                            "filed nothing.",
                                          f"{field} names {', '.join(map(str, missing))}; use {prefix}- IDs that exist."))
    if item.get("id"):
        refusal = textedit.id_refusal(vault, item["id"], "SLC")
        if refusal is not None:
            found.append(refusal)
    return found


def value(field, item, vault):
    if field in ("flows", "after"):
        return ", ".join(textedit.link(vault, str(i)) for i in item[field])
    return textedit.inline(item[field])


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "SLC")
    title = str(item["title"]).strip()
    name = f"{ident}-{textedit.slug(title)}"
    lines = ["---", f"id: {ident}", "type: slice", f"title: {textedit.yaml_value(title)}", "authored: authored", "---",
             "", f"# {title}", ""]
    lines += [f"- **{label}:** {value(field, item, vault)}" for field, label in BULLETS if item.get(field)]
    source = f", from [[{record.id}#^c{str(item['capture']).lstrip('^c')}]]" if item.get("capture") else ""
    lines += ["", "## Not in this slice", "", "## History", "",
              f"- {textedit.today(vault)}: written in [[{record.id}]]{source}"]
    rec = textedit.record_text(record, vault)
    if item.get("capture"):
        rec = textedit.add_change(rec, ident, "-", "new", textedit.capture_link(record.id, item["capture"]))
        rec = textedit.mark_if_unmarked(rec, item["capture"], textedit.keep_mark(name, title, ident, "new"))
    return [Write(f"{FOLDER}/{name}.md", "\n".join(lines) + "\n")] + textedit.record_writes(record, vault, rec)
