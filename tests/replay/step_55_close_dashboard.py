"""Close section 6 once the record is closed: `vela close dashboard --for-lead` rebuilds the page in the working tree
and commits nothing, makes no branch, and says it goes in with the next session."""
from vela import closefinish


def run(ctx):
    head = ctx.git("rev-parse", "HEAD").strip()
    code, out = ctx.vela("close", "dashboard", "--for-lead", "--today", ctx.today)
    assert closefinish.NO_SESSION_DASHBOARD in out or closefinish.DASHBOARD_DONE in out, out
    assert ctx.git("rev-parse", "HEAD").strip() == head, "close dashboard committed with no session open"
    assert (ctx.vault / closefinish.DASHBOARD).is_file()
    ctx.outputs["close dashboard"] = out
