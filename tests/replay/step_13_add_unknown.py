"""Grill section 5, a new unknown mid-grill: `vela add unknown` (Task 15). The lead's question goes in the record with
`record add`; `add unknown` numbers it past every branch (main here), writes it on the unknowns page with its owner,
ask-by date and what it blocks, adds the `## Changes` row and marks the capture, so close finds it already filed. Its
`--for-lead` lines say what was written by name, never by ID."""
import json

QUESTION = '"Who signs off the pilot laptops before the calls start?"'
ID = "UNK-029"  # the snapshot's highest is UNK-028, on main


def run(ctx):
    ctx.typed(QUESTION)
    code, out = ctx.vela("record", "add", "--origin", "@sim-lead", "--tag", "unknown", QUESTION, "--json")
    number = json.loads(out)["number"]
    code, said = ctx.vela("add", "unknown", "--today", ctx.today, "--name", "Pilot laptop sign-off",
                          "--capture", number, "--owner", "@sim-lead", "--blocks", "CON-003", "--for-lead")
    assert "Pilot laptop sign-off" in said, said
    ctx.outputs["add unknown --for-lead"] = said
    page = (ctx.vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    assert f"### {ID} Pilot laptop sign-off" in page, page[-2000:]
    record = ctx.outputs["record"].read_text(encoding="utf-8")
    assert f"| {ID} | - | open | [[{ctx.record_id}#{number}]] |" in record, record
    assert f"|{ID}]] (open) {number}" in record, record
