"""REVIEW sections 1 and 2: `vela reviewers prepare` numbers the checkpoint from the record, commits what is not yet
committed, and writes one packet per area; the lead hears one plain sentence while the reviewers run."""
import json


def run(ctx):
    code, out = ctx.vela("reviewers", "prepare", "--checkpoint", "after the read-back", "--focus", "01-goals.md",
                         "--today", ctx.today, "--json")
    answer = json.loads(out)
    assert answer["checkpoint"] >= 1 and answer["packets"], out
    for packet in answer["packets"]:
        assert (ctx.vault / packet["packet"]).is_file() and (ctx.vault / packet["questions_file"]).is_file(), packet
    assert ctx.git("status", "--porcelain", "--", f"sessions/{ctx.record_id}.md").strip() == "", "the record is committed"
    code, said = ctx.vela("reviewers", "prepare", "--checkpoint", "after the read-back", "--focus", "01-goals.md",
                          "--today", ctx.today, "--for-lead")
    ctx.outputs["reviewers prepare --for-lead"] = said
