# ruleid: planner-core-no-io-imports
import subprocess  # noqa: F401 - semgrep rule example
# ruleid: planner-core-no-io-imports
from pathlib import Path  # noqa: F401 - semgrep rule example
# ok: planner-core-no-io-imports
import urllib.parse  # noqa: F401 - semgrep rule example
# ok: planner-core-no-io-imports
import datetime

def overdue(due, today):
    # ok: planner-core-no-clock
    return datetime.date.fromisoformat(due) < datetime.date.fromisoformat(today)

def bad():
    # ruleid: planner-core-no-clock
    return datetime.date.today()

def render(page):
    # ruleid: planner-core-no-file-or-stdout
    print(page)
    # ruleid: planner-core-no-file-or-stdout
    return page.path.read_text(encoding="utf-8")
