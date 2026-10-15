"""Close section 6, after render: `vela check --fix W326 --for-lead` sets each page's state as W326 says (overhaul Task
21b). Nothing to set is exit 0 too; 1 means the new state left an error, which the replay's own end check would see."""


def run(ctx):
    code, out = ctx.vela("check", "--fix", "W326", "--for-lead", "--today", ctx.today, check=False)
    assert code in (0, 1), f"check --fix W326 failed as a tool (exit {code}):\n{out}"
    ctx.outputs["check --fix W326 --for-lead"] = out
