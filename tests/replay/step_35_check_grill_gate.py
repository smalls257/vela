"""Grill section 2: `vela check --gate grill --item CON-001 --for-lead` says, in names, whether the item can go on the
agenda and the one thing that would make it ready (overhaul Task 13). "Not ready" is exit 1, not a failure; only a tool
failure (2) stops. The replay's own check asserts no code or ID reaches the lead."""


def run(ctx):
    code, out = ctx.vela("check", "--gate", "grill", "--item", "CON-001", "--for-lead", "--today", ctx.today, check=False)
    assert code in (0, 1), f"check --gate grill --for-lead failed as a tool (exit {code}):\n{out}"
    assert "ready" in out.lower(), out
    ctx.outputs["check --gate grill --for-lead"] = out
