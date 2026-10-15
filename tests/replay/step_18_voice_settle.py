"""Close section 4's voice review: `vela voice settle --checkpoint` before the rewrite, then `--rewrites` after it. A
rewrite that adds a number fails voicecheck, so the page is put back to its checkpoint and nothing is committed."""

PAGE = "04-solution-strategy.md"


def run(ctx):
    ctx.vela("voice", "settle", "--checkpoint", PAGE, "--session", ctx.record_id)
    path = ctx.vault / PAGE
    before = path.read_text(encoding="utf-8")
    path.write_text(before + "\nThe desk answers in 42 seconds.\n", encoding="utf-8")
    code, out = ctx.vela("voice", "settle", "--rewrites", PAGE, "--session", ctx.record_id, "--for-lead", check=False)
    assert code == 1 and "I put back the earlier draft of" in out, out
    assert path.read_text(encoding="utf-8") == before, out
    ctx.outputs["voice settle --rewrites --for-lead"] = out
