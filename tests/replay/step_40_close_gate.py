"""Close section 7 and 8: `vela close gate --for-lead` says the session is ready, and `--consent-block` quotes the
lead's own words behind the decision, for the PR body."""


def run(ctx):
    code, out = ctx.vela("close", "gate", "--for-lead")
    assert "ready" in out, out
    ctx.outputs["close gate --for-lead"] = out
    code, block = ctx.vela("close", "gate", "--consent-block")
    assert ctx.outputs["quote"] in block, block
    ctx.outputs["close gate --consent-block"] = block
