"""Close section 4 and house-voice: `vela voice examples --page` names the examples a draft reads in their fixed order,
and `vela voice harvest list` says plainly when there is nothing to harvest (the snapshot has only the public seed)."""


def run(ctx):
    code, out = ctx.vela("voice", "examples", "--page", "04-solution-strategy.md", "--json")
    assert '"voice_type": "decision"' in out and "voice/examples/decision/VX-decision-001.md" in out, out
    code, out = ctx.vela("voice", "harvest", "list", "--for-lead")
    assert "No owner examples yet, so nothing to harvest." in out, out
    ctx.outputs["voice harvest list --for-lead"] = out
