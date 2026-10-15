"""Close section 8: `vela close pr` opens the pull request through the sim's gh stub, which records it in origin and
prints its URL; the lead hears the URL, and the PR's title uses the plain mode name."""
import json


def run(ctx):
    code, out = ctx.vela("close", "pr", "--today", ctx.today, "--for-lead")
    assert "https://github.invalid/sim/heron/pull/1" in out, out
    log = ctx.origin / "sim-prs.jsonl"
    (row,) = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    assert row["head"] == f"session/{ctx.record_id}" and row["title"].startswith(f"{ctx.today} Decisions: "), row
    ctx.outputs["close pr --for-lead"] = out
