"""Close section 2: `vela marks plan` (Task 14). The session's one capture was marked by the grill that decided it, so
the defaults leave it alone and there is nothing for the lead (exit 0); every mark in the record reads in the grammar
`markrules.parse_mark` holds, the same parser the defaults use."""
import json

from vela import closegate, markrules


def run(ctx):
    code, out = ctx.vela("marks", "plan", "--today", ctx.today, "--json")
    data = json.loads(out)
    assert code == 0 and not data["needs_lead"], out
    assert [a["capture"] for a in data["left_alone"]] == ["^c01"], out
    code, said = ctx.vela("marks", "plan", "--today", ctx.today, "--for-lead")
    assert "already has its place" in said, said
    ctx.outputs["marks plan --for-lead"] = said
    text = ctx.outputs["record"].read_text(encoding="utf-8")
    for line in text.split("\n"):
        match = closegate.CAPTURE_RE.match(line.strip())
        if match and match["mark"] is not None:
            assert markrules.parse_mark(match["mark"]) is not None, line
