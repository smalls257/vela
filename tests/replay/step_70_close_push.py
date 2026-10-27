"""Close section 4, after the close commit: `vela close push` runs the gate and pushes `session/<id>` to the bare local
origin, with no notice and no yes (the lead's word to close is the yes)."""


def run(ctx):
    code, out = ctx.vela("close", "push", "--today", ctx.today, "--for-lead")
    remote = ctx.git("ls-remote", "--heads", "origin", f"session/{ctx.record_id}").split()
    assert remote and remote[0] == ctx.git("rev-parse", "HEAD").strip(), out
    ctx.outputs["close push --for-lead"] = out
