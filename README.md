# proj-planner

A Claude Code toolkit for planning at the initiative level. It covers everything from a one-line ask to fully specified epics, written in Markdown that every reader can follow.

## Start here tomorrow

1. **Make a vault.** Copy `template/` into a new GitHub repo, then follow its `README.md` setup checklist, steps 1 to 8. Step 2 copies this repo's `plugin/` folder into the vault. You need Python 3.11+ and PyYAML: `python3 -m pip install pyyaml`. Your Mac's `python3` already has PyYAML 6.0.3. If pip refuses on another machine with "externally-managed-environment", install PyYAML into a venv (`python3 -m venv ~/.venvs/planner && ~/.venvs/planner/bin/pip install pyyaml`) and run planner with `~/.venvs/planner/bin/python3`.
2. **Start every session with `bin/claude-planner`**, from inside the vault. The skills only load through that launcher.
3. **Run your first session:**
   - `/planner:dump` gets everything out of your head. Ideas, worries, unknowns and wild ones all count. Claude doesn't push back.
   - `/planner:close` promotes what you keep, drafts the prose in the house voice, runs `check`, and opens the PR.
4. **Next sessions, in roughly this order:**
   - `/planner:discover` reads your sources and asks you to confirm what exists today.
   - `/planner:shape` offers 2–3 options to react to.
   - `/planner:grill` is the only thing that can mark an item `decided`, and only after your explicit yes.
   - `/planner:ask` answers questions from the vault. It is read-only, and anything the vault doesn't hold comes back as `Not recorded:`.
5. **Before each PR,** run `python3 .claude/skills/planner/bin/planner check`. CI runs it too. If you make it a required check, a broken vault can't merge.
6. **For the CIO,** run `python3 .claude/skills/planner/bin/planner view --out ~/Desktop/<name>.html` and email the file. It works offline and can't run page script or make network calls.

The kill rule you set: if it isn't faster than plain Markdown after five sessions, cut back to the conventions, `check` and the viewer.

## Later

- **When the first app nears handoff,** use `/planner:epics` and `planner check --gate epics`.
- **Vault mode for your own grills:** `integrations/requirements-grill/INSTALL.md` and `integrations/tech-design-grill/INSTALL.md`. Each one backs up first and dry-runs before applying. Nothing has been applied to `~/.claude` yet.
- **Optional Jira export:** `python3 .claude/skills/planner/bin/planner export jira-csv --out epics.csv` writes one row per epic (Summary, Description with the acceptance criteria, Epic Name, Owner team, Vault link) for Jira's CSV import. It is an export only: nothing is read back and no page carries a Jira field. Owner team drops the leading `@` of the handle, so `@org/team` becomes `org/team`. The link points at the repository and commit from `git`, or pass `--repo-url` and `--commit`.
- **Evals:** these are paid runs, and you run them by hand. See `tests/evals/README.md`. Start with the $1 smoke run it describes.

## What's where

| Path | What it is |
|---|---|
| `template/` | The vault you copy, including `CONVENTIONS.md`, the one written format |
| `plugin/` | The `planner` CLI (`check`, `render`, `view`, `status`, `next`, `query`, `health`, `handoff`, `export`) and the session skills |
| `examples/unified-booking/` | A complete made-up vault: a ferry operator's Unified Booking initiative |
| `integrations/` | Vault mode for `requirements-grill` and `tech-design-grill`, as patches |
| `docs/` | Spec, design-session logs, research, plans |
| `tests/` | `python3 -m pytest -q` |
