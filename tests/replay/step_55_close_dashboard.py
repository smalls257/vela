"""Close section 6 once the record is closed: `vela close dashboard --for-lead` rebuilds the page and, with no session
open, puts it on its own `dashboard/<date>` branch without asking, or says the page was already current. The replay
then goes back to the session's branch, which the push and the pull request that follow are on."""
from vela import closefinish


def run(ctx):
    branch = ctx.git("branch", "--show-current").strip()
    code, out = ctx.vela("close", "dashboard", "--for-lead", "--today", ctx.today, check=False)
    assert code == 0, f"close dashboard exited {code}:\n{out}"
    assert (ctx.vault / closefinish.DASHBOARD).is_file()
    ctx.git("switch", "-q", branch)
    ctx.outputs["close dashboard"] = out
