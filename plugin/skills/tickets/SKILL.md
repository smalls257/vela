---
name: tickets
description: "Turn a finished build plan into tickets: a Markdown list, a CSV for Jira import, or Jira tools you already have. Offer it when someone asks for tickets; start it only on a yes. Nothing is created outside the system they chose."
argument-hint: "[app slug or APP-id]"
---

# Tickets

The plan is the source of truth and the tickets are copies of it. This session holds the plan against the vault once more, so the people downstream get tickets that still say what the vault says, then writes the copy the person chose.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The converter is part of it as `vela tickets`, so this works from an installed plugin with no copy of the repo. The vault is the folder this runs in.

## 1. Start

Before your first question, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`. From `${CLAUDE_PLUGIN_ROOT}/references/START.md` follow "Plain names and a page a person can hold" and "The user may override any rule". A team session writes no session record.

Find the plan: `docs/plan/<slug>-breakdown.md`, the one named, or the only one. Its status must be `complete` or `complete-with-gaps`. If not, say so in a sentence and offer `/vela:breakdown`; stop there, because a ticket list from a plan still moving is a list to redo.

## 2. Check the plan against the vault

Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela tickets check --vault .` (add the plan's path, or `--app APP-x`, when there is more than one). It writes nothing. It checks traces, coverage, the quoted criteria, blockers, the tracer's place, `Slice:` lines and release fit. Exit 1 means it flagged something, which is a result and not a failure. Exit 2 means it couldn't run: say in one plain sentence that you couldn't check the plan, and why in your words.

Say what it found in your words, grouped by story, not as the tool printed it: "The withdraw story quotes five of its six criteria; the sixth is missing." Keep it to what the person has to decide, about four at a time. For each flag offer the same two ways out, with your recommendation: fix the plan now (in `/vela:breakdown`, or by a small edit the person agrees to), or go on and mention the flag in the ticket list. If they go on, say so in the summary at the end. Don't change the plan yourself, and never reword a criterion to make the check pass; the vault's words win, and a vault sentence that is wrong goes back as `/vela:challenge`.

## 3. Ask which output

Ask once, with your recommendation and why:

1. **A Markdown ticket list**, recommended: one file, one section per story with its criteria written out, size, components, what it waits on and its release fit, and its tasks as a checklist. Tracer stories come first, then the rest grouped by the slice each names. It needs no account or project key, and a team can paste from it anywhere.
2. **A CSV for Jira import**: one row per story and per task. Task sizes become story points by a fixed mapping (S 2, M 5, L 8) that the README beside the file explains; say so, and that the points are ordering aids, not estimates.
3. **Jira tools the person already has.** Ask: "Do you already have Jira connected to Claude, or a Jira command-line tool?" Look at what is actually available; don't assume one, and never guess a project key or a repository. If they name none, offer 1 or 2.

## 4. Write it

- Markdown: `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela tickets write --vault . --format markdown` writes `docs/work/tickets.md`.
- CSV: the same with `--format csv` writes `docs/work/tickets.csv` and a `README.md` with the column mapping and Jira's import steps. Check the target tool's import page for its column names before telling the person which columns to map.
- Jira tools: read the plan's "Ticket waves" and propose the first wave only. Choosing Jira tools is the yes for the first wave: show the first ticket exactly as it would be created (project, type, summary, description with its criteria, links), then create the wave's tickets without a yes per ticket. Ask once before each later wave. Write no script to create tickets; call the tool, or write the file.

Nothing is created in an outside system the person didn't choose in step 3. A plan edit is not a reason to create or update tickets; tell the person the tickets are now out of date and let them decide.

## 5. Stop

After the file is written, stop with one short summary and the path, for example "9 stories, 42 tasks, 3 flagged. Written to docs/work/tickets.md." Name the stories that have no ticket because the plan defers or merges them. Don't offer more work. If the person wants the flags fixed, the next step is `/vela:breakdown`.
