"""Close section 7 and 8: `vela close gate --for-lead` says the session is ready (exit 0: main brought in, every
decision quoted, every capture marked, no error, no removed row or override, no stray file, render current), and
`--consent-block` quotes the lead's own words behind the decision, for the PR body. The hooks line is the model's
note, never a reason to block and never news to the lead: the replay runs no SessionStart hook, so the default output
says it and the lead's doesn't."""


def run(ctx):
    ctx.vela("close", "readback", "--done")  # the lead keeps every line as written (Task 10)
    code, out = ctx.vela("close", "gate", "--for-lead", "--today", ctx.today, check=False)
    assert code == 0 and out.startswith("The session is ready to finish."), f"close gate exit {code}:\n{out}"
    assert "Hooks did not run" not in out, out
    code, default = ctx.vela("close", "gate", "--today", ctx.today, check=False)
    assert "Hooks did not run in this session" in default, default
    ctx.outputs["close gate --for-lead"] = out
    code, block = ctx.vela("close", "gate", "--consent-block", "--today", ctx.today)
    assert ctx.outputs["quote"] in block, block
    ctx.outputs["close gate --consent-block"] = block
