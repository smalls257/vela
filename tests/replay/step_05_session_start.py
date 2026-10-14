"""START steps 1, 2 and 5 through `vela session start` (Task 6b): the snapshot's initiative still has the template's
name, so the first call stops with the one naming question and changes nothing; the lead declines, and the second call
pulls main, opens `session/<id>` and the record, and commits `Open session <id>`."""


def run(ctx):
    asked = ("session", "start", "--mode", "grill", "--topic", "desk agent calendar", "--today", ctx.today)
    head = ctx.git("rev-parse", "HEAD")
    code, out = ctx.vela(*asked, "--for-lead", check=False)
    assert code == 3, out
    assert "What short name should this initiative go by?" in out, out
    assert ctx.git("rev-parse", "HEAD") == head, "an exit 3 changed the repo"
    code, out = ctx.vela(*asked, "--unnamed", "--for-lead")
    assert ctx.git("rev-parse", "--abbrev-ref", "HEAD").strip() == f"session/{ctx.record_id}", out
    assert f"Calling this one {ctx.record_id}." in out, out
    ctx.outputs["record"] = ctx.vault / "sessions" / f"{ctx.record_id}.md"
    ctx.outputs["session start"] = out
