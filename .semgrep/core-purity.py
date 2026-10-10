# ruleid: planner-core-no-io-imports
import subprocess
# ruleid: planner-core-no-io-imports
from pathlib import Path
# ok: planner-core-no-io-imports
import urllib.parse
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
