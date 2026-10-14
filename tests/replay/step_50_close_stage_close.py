"""Close section 7: the record says `status: closed` with its summary, and `vela close stage --close` commits
`Close session <id>` from the allow-list."""


def run(ctx):
    record = ctx.outputs["record"]
    text = record.read_text(encoding="utf-8")
    text = text.replace("status: open", "status: closed", 1)
    text = text.replace("summary: In progress.", "summary: Heron reads only the folder the person points it at.", 1)
    record.write_text(text, encoding="utf-8")
    code, out = ctx.vela("close", "stage", "--close", "--session", ctx.record_id)
    assert ctx.git("log", "-1", "--format=%s").strip() == f"Close session {ctx.record_id}", out
    left = ctx.git("status", "--porcelain").strip()
    assert not left, f"the close commit left the session's files out (what render rewrote included):\n{left}"
    ctx.outputs["close stage --close"] = out
