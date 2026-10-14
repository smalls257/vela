"""Close section 1: `vela session open --switch` finds the one open record and stays on its branch."""


def run(ctx):
    code, out = ctx.vela("session", "open", "--switch")
    assert ctx.record_id in out or "calendar" in out, out
    assert ctx.git("rev-parse", "--abbrev-ref", "HEAD").strip() == f"session/{ctx.record_id}"
    ctx.outputs["session open"] = out
