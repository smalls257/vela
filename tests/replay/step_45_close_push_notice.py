"""Close section 7, before the close commit: `vela close push` without `--consent` prints the send notice and exits 3
(nothing sent), and the lead's yes to it is captured with `vela record add` while the record is still open, so the close
commit carries it. The lead's handle comes first (`vela whoami --set`): the sim's gh stub can't say who they are."""


def run(ctx):
    ctx.vela("whoami", "--set", "replay-lead")
    head = ctx.git("rev-parse", "HEAD")
    code, out = ctx.vela("close", "push", "--today", ctx.today, "--for-lead", check=False)
    assert code == 3 and out.strip().startswith("I'll send this for review") and out.strip().endswith("OK?"), out
    assert ctx.git("rev-parse", "HEAD") == head, "the send notice changed the repo"
    assert not ctx.git("ls-remote", "--heads", "origin", f"session/{ctx.record_id}").strip(), "sent before a yes"
    ctx.outputs["close push --for-lead (notice)"] = out
    code, number = ctx.vela("record", "add", "--origin", "@replay-lead", "--tag", "decision", "--mark",
                            "drop: the yes to send this for review", "Yes, send it for review.")
    ctx.outputs["push yes"] = number.strip()
