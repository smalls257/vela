---
name: tickets
description: Turn a finished build plan into tickets a team can work from. Checks the plan against the vault first (every story traces to a criterion or requirement, every requirement of the app has a story, criteria match the vault word for word, blockers are real, the tracer comes first, release dates line up), then writes a Markdown ticket list or a CSV for Jira import, or uses Jira tools the person already has. Use after /planner:breakdown, when someone says "make the tickets", "export to Jira" or "turn the plan into tickets". Creates nothing in any outside system without an explicit yes.
argument-hint: "[app slug or APP-id]"
disable-model-invocation: true
---

# Tickets

The plan is the source of truth and the tickets are copies of it. This session holds the plan against the vault once more, so the people downstream get tickets that still say what the vault says, then writes the copy the person chose.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The converter is part of it as `planner tickets`, so this works from an installed plugin with no copy of the repo. The vault is the folder this runs in.

## 1. Start

Read `${CLAUDE_PLUGIN_ROOT}/references/START.md` for "Plain names and a page a person can hold" and "The user may override any rule", then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, and `voice/VOICE.md` in the vault when it exists. A team session writes no session record.

Find the plan: `docs/plan/<slug>-breakdown.md`, the one named, or the only one. Its status must be `complete` or `complete-with-gaps`. If not, say so in a sentence and offer `/planner:breakdown`; stop there, because a ticket list from a plan still moving is a list to redo.

## 2. Check the plan against the vault

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner tickets check --vault .` (add the plan's path, or `--app APP-x`, when there is more than one). It writes nothing. Exit 1 means it flagged something, which is a result and not a failure; exit 2 means it could not run, and the message says why.

It looks for:

- a story that traces to no epic criterion and no allocated requirement, or to an ID the vault does not hold;
- a requirement, contract or criterion of the app that no story covers (a plan gap that accepts it is a note, not a flag);
- a story whose criteria are not the vault's words: reworded, or missing;
- a blocker that is not a story of the plan, or a vault question that does not exist;
- a missing or wrong tracer: no tracer story, or one that the build order puts behind another story;
- a layer story, or one with no `Slice:` line;
- a `Release fit:` line missing, or starting from a date other than the release that delivers what the story traces to.

Say what it found in plain words, grouped by story, not as the tool printed it: "The withdraw story quotes five of its six criteria; the sixth is missing." Keep it to what the person has to decide. For each flag offer the same two ways out: fix the plan now (in `/planner:breakdown`, or by a small edit the person agrees to), or go on and mention the flag in the ticket list. If they go on, say so in the summary at the end. Do not change the plan yourself, and never reword a criterion to make the check pass; the vault's words win, and a vault sentence that is wrong goes back as `/planner:challenge`.

## 3. Ask which output

Ask once, with your recommendation and why:

1. **A Markdown ticket list**, recommended: one file, one section per story with its criteria written out, size, components, what it waits on and its release fit, and its tasks as a checklist. Tracer stories come first. It needs no account or project key, and a team can paste from it anywhere.
2. **A CSV for Jira import**: one row per story and per task. Task sizes become story points by a fixed mapping (S 2, M 5, L 8) that the README beside the file explains; say so, and that the points are ordering aids, not estimates.
3. **Jira tools the person already has.** Ask whether their setup has an MCP server or a command-line tool for Jira, and which. Look at what is actually available; do not assume one, and never guess a project key or a repository. If they name none, offer 1 or 2.

## 4. Write it

- Markdown: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner tickets write --vault . --format markdown` writes `docs/work/tickets.md`.
- CSV: the same with `--format csv` writes `docs/work/tickets.csv` and a `README.md` with the column mapping and Jira's import steps. Check the target tool's import page for its column names before telling the person which columns to map.
- Jira tools: read the plan's "Ticket waves" and propose the first wave only. Show the first ticket exactly as it would be created (project, type, summary, description with its criteria, links) and wait for a yes. A yes covers that ticket; ask again before creating the rest, and again before any later wave. Write no script to create tickets; call the tool, or write the file.

Nothing is created in any outside system without an explicit yes in this session. A plan edit is not a reason to create or update tickets; tell the person the tickets are now out of date and let them decide.

## 5. Stop

After the file is written, stop with one short summary and the path, for example "9 stories, 42 tasks, 3 flagged. Written to docs/work/tickets.md." Name the stories that have no ticket because the plan defers or merges them. Do not offer more work. If the person wants the flags fixed, the next step is `/planner:breakdown`.
