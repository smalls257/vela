"""REVIEW section 5: `vela questions --digest --session` gives the lead the next three lines and writes what it showed
under the record's `## Reviews`, so the second call never repeats one. The draft commit (step 15) carries the line."""
import json


def run(ctx):
    record = ctx.outputs["record"]
    code, first = ctx.vela("questions", "--digest", "--session", ctx.record_id, "--json")
    code, second = ctx.vela("questions", "--digest", "--session", ctx.record_id, "--json")
    shown, again = json.loads(first)["shown"], json.loads(second)["shown"]
    assert shown and not set(shown) & set(again), (first, second)
    assert f"Digest shown: {', '.join(shown + again)}\n" in record.read_text(encoding="utf-8")
    ctx.outputs["questions --digest --session"] = second
