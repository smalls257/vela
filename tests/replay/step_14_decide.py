"""Grill section 4: `vela decide` (Task 16). The read-back, the lead's yes and their reason go in the record with `record
add`; `decide` runs the grill gate on Heron's runtime page (ready), writes `state: decided`, the Decision and the Why
word for word under the page's `## History`, the `## Changes` row citing the yes and a keep mark on each capture it
filed, and commits `grill: <ID> decided`. Its `--for-lead` line names the page, never its ID. `close gate` (step 40)
then reads this Changes row like any other.

The replay's commit grammar (`COMMIT_GRAMMAR` in `test_session_replay.py`) is built from the messages START and close
write and doesn't list `decide`'s yet, and a step never edits the test. So this step checks decide's commit against
`commands.decide.MESSAGES` itself, then undoes the commit and keeps its changes in the working tree, where the close
checkpoint (step 15) commits them with the rest. Once the grammar reads `decide.MESSAGES`, the reset goes."""
import json

from vela.commands import decide

PAGE = "06-runtime/apps/heron-runtime.md"
ID = "RUN-heron"
WHY = '"Heron runs on the laptop because the pilot team won\'t send client files to a cloud service."'


def run(ctx):
    numbers = []
    for origin, tag, words in (("claude", "thought", "Read back: Heron's runtime runs on the pilot user's laptop, "
                                                     "reading only the folder they choose"),
                               ("@replay-lead", "thought", '"Yes, that is how Heron runs."'),
                               ("@replay-lead", "thought", WHY)):
        if origin != "claude":
            ctx.typed(words)
        code, out = ctx.vela("record", "add", "--origin", origin, "--tag", tag, words, "--json")
        numbers.append(json.loads(out)["number"])
    readback, yes, why = numbers
    head = ctx.git("rev-parse", "HEAD").strip()
    code, said = ctx.vela("decide", ID, "--readback", readback, "--yes", yes, "--why", why, "--today", ctx.today,
                          "--for-lead")
    assert "Heron" in said and "decided" in said, said
    ctx.outputs["decide --for-lead"] = said
    subject = ctx.git("log", "-1", "--format=%s").strip()
    assert subject == decide.MESSAGES["decided"].format(id=ID), subject
    shown = ctx.git("show", "--name-only", "--format=", "HEAD").split()
    assert sorted(shown) == [PAGE], shown  # the notes are never committed
    page = (ctx.vault / PAGE).read_text(encoding="utf-8")
    assert "\nstate: decided\n" in page and f"- **Decision:** [[{ctx.record_id}]]" in page, page[-800:]
    assert "- **Why:** Heron runs on the laptop because the pilot team won't send client files to a cloud service." \
        in page, page[-800:]
    record = ctx.outputs["record"].read_text(encoding="utf-8")
    assert f"| {ID} | assumption | decided | [[{ctx.record_id}#{yes}]] |" in record, record
    for number in numbers:
        line = next(l for l in record.split("\n") if l.rstrip().endswith(f" {number}"))
        assert f"|{ID}]] (decided) {number}" in line, line
    ctx.git("reset", "-q", head)
