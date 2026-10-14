"""START step 5 by hand, as START does it today: branch, record, commit `Open session <id>`.

`vela session start` does not exist yet; Task 6b replaces this step with a step that runs it, and deletes this file."""

RECORD = """---
id: {id}
type: session
title: "Grill: desk agent calendar"
date: {today}
modes: [grill]
status: open
summary: In progress.
---

# {today} Grill: desk agent calendar

## Captures

## Changes

| ID | From | To | Source |
|---|---|---|---|
"""


def run(ctx):
    ctx.git("switch", "-q", "-c", f"session/{ctx.record_id}")
    path = ctx.vault / "sessions" / f"{ctx.record_id}.md"
    path.write_text(RECORD.format(id=ctx.record_id, today=ctx.today), encoding="utf-8")
    ctx.git("add", f"sessions/{ctx.record_id}.md")
    ctx.git("commit", "-q", "-m", f"Open session {ctx.record_id}")
    ctx.outputs["record"] = path
