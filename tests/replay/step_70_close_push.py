"""Close section 7, after the close commit: `vela close push --consent ^cN` checks the yes came after the notice, runs
the gate, and pushes `session/<id>` to the bare local origin."""


def run(ctx):
    code, out = ctx.vela("close", "push", "--consent", ctx.outputs["push yes"], "--today", ctx.today, "--for-lead")
    remote = ctx.git("ls-remote", "--heads", "origin", f"session/{ctx.record_id}").split()
    assert remote and remote[0] == ctx.git("rev-parse", "HEAD").strip(), out
    ctx.outputs["close push --for-lead"] = out
