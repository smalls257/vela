---
name: open
description: "Open a published plan, or a newer one, as a private reader workspace for someone with no git; never writes to the folder you opened it from. Offer it when someone sends a published folder, a zip or a GitHub link; start it only on a yes."
argument-hint: "<published folder, .zip or GitHub link>"
allowed-tools: Read Bash(sh *scripts/run-vela *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Open a published copy

A sponsor or architect receives a folder, a zip or a GitHub link an owner published. This skill makes a private copy to read and draft in. The source is never written, because it is usually a shared OneDrive or SharePoint folder where the last save wins.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). There is no plan folder yet, so no vendored copy and no `.vela/workspace.json`: when you can't find the program, stop with the message in that order. When a command can't express what the user wants, say so and stop.

Before your first question, read how to talk: `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, as `START.md` step 0 says. There's no copy yet, so there's no `voice/VOICE.md` to read first. Don't tell the user you read it.

## Opening

$ARGUMENTS

## Steps

1. If no folder, zip or GitHub link was given, ask for it. Do not search the disk for one.
2. Ask for the name the drafts go under, unless they gave it. Not the machine's user name; offer `git config user.name` if it is set.
3. Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela open "<source>" --author "<name>"` (the same command for a GitHub link, which is read as committed there), with `--into <folder>` when the user names one. The default is `~/VelaWorkspaces/<initiative-slug>/` (or `$VELA_WORKSPACES/<initiative-slug>/`). In Claude Cowork use `--into vela-workspaces/<initiative-slug>`, because only the working folder is kept.
4. Say what it printed in your own words: which initiative, who published it and when, the checks at publish time, where the private copy is, and whether a newer copy exists. It also builds the dashboard, so end with: "The dashboard is up to date: dashboard.html — open it, or run /vela:explore to ask Claude from it". If it said the dashboard couldn't be built, say so plainly; the workspace was still written.
5. If it stops, say why in one sentence and offer the fix. When it can't fetch the plan from GitHub, say its message as written and never offer an older copy instead. Otherwise the fixes are: `--into` a folder that isn't synced (for OneDrive or SharePoint), a fresh copy from the owner (changed after publishing), or the newest copy (older than the workspace's). Never delete or empty a folder to make room.
6. A newer copy for an existing workspace is a re-open: the same command with `--into <that workspace>` (for a GitHub link, "get the newer plan" is the same command with the same link).  It replays the drafts onto the new pages and reports page by page. Relay it, conflicts first: the page holds the owner's version, "Your version is kept next to it in a file ending .mine.md", and nothing of theirs was overwritten. Offer to go through each pair, copy over the lines they want, and delete the `.mine.md` file once settled; they can't propose until then. Merged pages are worth one read. A stale proposal was written against the old copy: offer `/vela:propose` again after the conflicts.
7. Tell them to work from the workspace folder (`cd` there and start Claude Code in it). There they read with `/vela:explore`, ask with `/vela:ask` and `/vela:find`, and see the plan beside the chat with the companion. With the full vela plugin they can also draft changes in the planning sessions (`/vela:dump`, `/vela:shape` and so on); the reader plugin has no planning sessions, so don't offer them there. Nothing there uses git, and any decision they make waits for the owner's approval.
8. Offer to open `dashboard.html` in the workspace.

Never run `git init` in the workspace. Never edit anything under `~/.claude`.
