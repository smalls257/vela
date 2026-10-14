"""Close's draft commit: `vela close stage --draft` commits the session's pages whole, by exact path."""


def run(ctx):
    code, out = ctx.vela("close", "stage", "--draft", "--session", ctx.record_id)
    assert ctx.git("log", "-1", "--format=%s").strip() == f"draft: prose for {ctx.record_id}", out
    ctx.outputs["close stage --draft"] = out
