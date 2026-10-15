"""Close section 9 once the record is closed: `vela close dashboard --for-lead` rebuilds the page and, with no session
open, commits nothing anywhere: it offers a `dashboard/<date>` branch (exit 3), or says the page was already current."""
from vela import closefinish


def run(ctx):
    head = ctx.git("rev-parse", "HEAD").strip()
    code, out = ctx.vela("close", "dashboard", "--for-lead", "--today", ctx.today, check=False)
    assert code in (0, 3), f"close dashboard exited {code}:\n{out}"
    said = closefinish.NO_SESSION_DASHBOARD if code == 3 else closefinish.DASHBOARD_DONE
    assert said in out, out
    assert ctx.git("rev-parse", "HEAD").strip() == head, "close dashboard committed with no session open"
    assert (ctx.vault / closefinish.DASHBOARD).is_file()
    ctx.outputs["close dashboard"] = out
