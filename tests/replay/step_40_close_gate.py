"""Close section 7 and 8: `vela close gate --for-lead` says the session is ready (exit 0: main brought in, every
decision quoted, every capture marked, no error, no removed row or override, no stray file, render current), and
`--consent-block` quotes the lead's own words behind the decision, for the PR body. The hooks line is said, never a
reason to block: the replay runs no SessionStart hook."""


def run(ctx):
    code, out = ctx.vela("close", "gate", "--for-lead", "--today", ctx.today, check=False)
    assert code == 0 and out.startswith("The session is ready to finish."), f"close gate exit {code}:\n{out}"
    assert "Hooks did not run in this session" in out, out
    ctx.outputs["close gate --for-lead"] = out
    code, block = ctx.vela("close", "gate", "--consent-block", "--today", ctx.today)
    assert ctx.outputs["quote"] in block, block
    ctx.outputs["close gate --consent-block"] = block
