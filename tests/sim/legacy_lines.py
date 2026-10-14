"""Lines from a run recorded before the rename, for the comparison's tests: LEGACY_NAMES must read them as today's.

Each OLD line is copied word for word from an assistant turn of results/2026-10-12-093846-heron-desk (its arm
folder, OLD_ARM, is ignored by git, so the lines live here). Each TWIN is the same line as vela would say it today,
renamed by hand. Every line holding an old name ends with the marker the residual scan allows.
"""
OLD_ARM = "planner"  # legacy-name

# (turn, old line, its hand-renamed twin)
LINES = [
    (18,
     "Run `/planner:close` to mark each capture and open the PR. I haven't run it.",  # legacy-name
     "Run `/vela:close` to mark each capture and open the PR. I haven't run it."),
    (30,
     "- **Overdue unknowns:** `planner check` shows none.",  # legacy-name
     "- **Overdue unknowns:** `vela check` shows none."),
    (56,
     "The rest are in the digest. Run `python3 /Users/jasonsmith/Code/proj-planner/plugin/scripts/planner "  # legacy-name
     "questions --open --digest` to see them. `--all` prints every line.",
     "The rest are in the digest. Run `python3 /Users/jasonsmith/Code/proj-planner/plugin/scripts/vela "
     "questions --open --digest` to see them. `--all` prints every line."),
    (64,
     "- `main` had moved, so I merged it with no conflicts. `planner check` reports 0 errors. "  # legacy-name
     "Its one warning is W362 on `README.md`, which this session didn't touch.",
     "- `main` had moved, so I merged it with no conflicts. `vela check` reports 0 errors. "
     "Its one warning is W362 on `README.md`, which this session didn't touch."),
    (46,
     "I captured all of that in the session record and committed it. `planner check` shows 0 errors. "  # legacy-name
     "`git status` shows only the unstaged `.planner/` output, and nothing from `.inbox/` is staged.",  # legacy-name
     "I captured all of that in the session record and committed it. `vela check` shows 0 errors. "
     "`git status` shows only the unstaged `.vela/` output, and nothing from `.inbox/` is staged."),
]
