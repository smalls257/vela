---
name: open
description: Open a published copy of an initiative vault as a private reader workspace, for people who have no git. Copies the folder or zip into a safe place on this machine, keeps a pristine baseline, builds the explorer page and says whether a newer copy exists. Never writes to the folder you opened it from. Use when someone sends you a published vault folder or zip.
argument-hint: "<published folder or .zip>"
disable-model-invocation: true
allowed-tools: Read Bash(python3 *scripts/planner *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Open a published copy

A sponsor or architect receives a folder or zip that an owner published. This skill makes a private copy to read and draft in. The source is never written, because it is usually a shared OneDrive or SharePoint folder where the last save wins.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). There is no vault yet, so there is no vendored copy and no `.planner/workspace.json`: when you cannot find the program, stop with the message in that order.

## Opening

$ARGUMENTS

## Steps

1. If no folder or zip was given, ask for it. Do not search the disk for one.
2. Ask for the name the drafts go under, unless the user already gave it. Do not use the machine's user name. If `git config user.name` is set, offer it.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner open "<source>" --author "<name>"`. Add `--into <folder>` when the user names one. In Claude Cowork, where the working folder is the only place that is kept, add `--into planner-workspaces/<initiative-slug>` inside the working folder. The default is `~/PlannerWorkspaces/<initiative-slug>/`, or `$PLANNER_WORKSPACES/<initiative-slug>/` when that is set.
4. Tell the user what it printed, in its own words: which initiative, which commit, who published it, the checks at publish time, where the private copy is, and whether a newer copy exists.
5. If it stops, say why in one sentence and offer the fix. A location inside OneDrive or SharePoint: offer `--into` with a folder that is not synced. A copy changed after it was published: ask the owner for a fresh one. A workspace that is already open: say what the tool said. Opening a newer copy onto it, keeping their drafts, is not built yet, so the choices are to carry on in the open workspace or to open the newer copy into a different folder. Never delete or empty a folder to make room.
6. Tell the user to work from the workspace folder (`cd` there, and start Claude Code in it). From there every skill runs as a reader: `/planner:explore` to look around, `/planner:ask` and `/planner:find` to ask questions, and the mode skills to draft. Nothing there uses git, and any decision they make is marked pending approval until the owner sees it.
7. Offer to open the page: `.planner/explorer.html` in the workspace.

Never run `git init` in the workspace. Never edit anything under `~/.claude`.
