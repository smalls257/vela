"""The session's own work, as a Grill writes it by hand today: the lead says yes in their own words, the contract is
decided with its Decision, Why and Tested by bullets, and the record holds the capture (marked at once, the Grill's
exception) and its `## Changes` row.

When a capture or decide command lands, its task replaces these hand edits with a step that runs it."""

PAGE = "05-building-blocks/heron-building-blocks.md"
BEFORE = "- **Change:** new\n- **State:** assumption\n\n### CON-003 Call tool records"
AFTER = ("- **Change:** new\n- **State:** decided\n"
         "- **Decision:** [[{id}]]\n"
         "- **Why:** the person picks the folder, so Heron reads only what they chose to share.\n"
         "- **Tested by:** the pilot user points Heron at a test folder and checks the note uses only its files\n\n"
         "### CON-003 Call tool records")
CAPTURE = ("- [thought] (claude) Read back: Heron reads only the folder the person points it at "
           "→ keep: [[heron-building-blocks#CON-002 Chosen folder|CON-002]] (decided) ^c01\n"
           '- [decision] (@replay-lead) "Yes, Heron reads only the folder I point it at, as read back." '
           "→ keep: [[heron-building-blocks#CON-002 Chosen folder|CON-002]] (decided) ^c02\n")
QUOTE = "Heron reads only the folder I point it at"


def run(ctx):
    page = ctx.vault / PAGE
    text = page.read_text(encoding="utf-8")
    assert text.count(BEFORE) == 1, "the snapshot's CON-002 no longer reads as this step expects"
    page.write_text(text.replace(BEFORE, AFTER.format(id=ctx.record_id)), encoding="utf-8")
    record = ctx.outputs["record"]
    body = record.read_text(encoding="utf-8")
    body = body.replace("## Captures\n\n", "## Captures\n\n" + CAPTURE + "\n", 1)
    body = body.rstrip("\n") + f"\n| CON-002 | assumption | decided | [[{ctx.record_id}#^c02]] |\n"
    record.write_text(body, encoding="utf-8")
    ctx.outputs["quote"] = QUOTE
