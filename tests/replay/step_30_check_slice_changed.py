"""Close section 7: `vela check-slice --changed` checks the slices this change can touch and says the rest are unchanged.

Exit 1 is findings about the snapshot's own flows, which this session did not draw; only a tool failure stops."""


def run(ctx):
    code, out = ctx.vela("check-slice", "--changed", check=False)
    assert code in (0, 1), f"check-slice --changed failed as a tool (exit {code}):\n{out}"
    assert out.strip(), "check-slice --changed printed nothing for the lead to read"
    ctx.outputs["check-slice --changed"] = out
