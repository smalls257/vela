"""What the lead hears from `vela check --for-lead` after the close: plain sentences, no codes (the test asserts that)."""


def run(ctx):
    code, out = ctx.vela("check", "--for-lead", "--today", ctx.today, check=False)
    assert code in (0, 1), f"check --for-lead failed as a tool (exit {code}):\n{out}"
    ctx.outputs["check --for-lead"] = out
