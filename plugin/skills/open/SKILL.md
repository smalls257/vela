---
name: open
description: Open a published copy of a plan, or a newer one, as a private reader workspace for someone with no git. Never writes to the folder you opened it from. Use when someone sends you a published folder or zip.
argument-hint: "<published folder or .zip>"
disable-model-invocation: true
allowed-tools: Read Bash(python3 *scripts/vela *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Open a published copy

A sponsor or architect receives a folder or zip an owner published. This skill makes a private copy to read and draft in. The source is never written, because it is usually a shared OneDrive or SharePoint folder where the last save wins.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). There is no plan folder yet, so no vendored copy and no `.vela/workspace.json`: when you can't find the program, stop with the message in that order. When a command can't express what the user wants, say so and stop.

## Opening

$ARGUMENTS

## Steps

1. If no folder or zip was given, ask for it. Do not search the disk for one.
2. Ask for the name the drafts go under, unless they gave it. Not the machine's user name; offer `git config user.name` if it is set.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela open "<source>" --author "<name>"`, with `--into <folder>` when the user names one. The default is `~/VelaWorkspaces/<initiative-slug>/` (or `$VELA_WORKSPACES/<initiative-slug>/`). In Claude Cowork use `--into vela-workspaces/<initiative-slug>`, because only the working folder is kept.
4. Relay what it printed, in its own words: which initiative, who published it and when, the checks at publish time, where the private copy is, and whether a newer copy exists. It also builds the dashboard, so end with: "The dashboard is up to date: dashboard.html — open it, or run /vela:explore to ask Claude from it". If it said the dashboard couldn't be built, say so plainly; the workspace was still written.
5. If it stops, say why in one sentence and offer the fix: `--into` a folder that isn't synced (for OneDrive or SharePoint), a fresh copy from the owner (changed after publishing), or the newest copy (older than the workspace's). Never delete or empty a folder to make room.
6. A newer copy for an existing workspace is a re-open: the same command with `--into <that workspace>`. It replays the drafts onto the new pages and reports page by page. Relay it, conflicts first: the page holds the owner's version, "Your version is kept next to it in a file ending .mine.md", and nothing of theirs was overwritten. Offer to go through each pair, copy over the lines they want, and delete the `.mine.md` file once settled; they can't propose until then. Merged pages are worth one read. A stale proposal was written against the old copy: offer `/vela:propose` again after the conflicts.
7. Tell them to work from the workspace folder (`cd` there and start Claude Code in it). There they read with `/vela:explore`, ask with `/vela:ask` and `/vela:find`, and draft changes in the planning sessions (`/vela:dump`, `/vela:shape` and so on). Nothing there uses git, and any decision they make waits for the owner's approval.
8. Offer to open `dashboard.html` in the workspace.

Never run `git init` in the workspace. Never edit anything under `~/.claude`.
