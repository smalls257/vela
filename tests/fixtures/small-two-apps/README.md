---
id: readme
type: index
title: Initiative vault
authored: authored
---

# Initiative vault

This vault holds one initiative. Start at [[01-goals|Goals]]. The format is in `CONVENTIONS.md`.

Prerequisites: Python 3.9 or later, which every Mac already has. Nothing to pip install: the plugin brings its own copy of PyYAML. `vela doctor` says what this machine has and what each missing optional piece would add.

## Setup checklist

`vela new` made this folder from the installed plugin, ran `vela check` with no errors and saved the first commit. There is no copy of the plugin to keep, and no special way to start Claude Code: the plugin you installed from the marketplace loads as usual. Three steps are left for a person.

1. Put the plan on GitHub. Make an empty repository there, then `git remote add origin <its URL>` and `git push -u origin main`.
2. Ask Claude to run `vela doctor` once in this folder. If the commit check that keeps the inbox and your private voice files out of a commit isn't switched on, it prints the one command that does it.
3. Rewrite `CLAUDE.md` in your own words and delete its first line. Open the folder in Obsidian if you use it; `.obsidian/app.json` is committed, and workspace files are ignored.

No checks run on GitHub for you. Before a pull request, run `vela check`; to see what has gone stale, run `vela health`.

To read the plan without Obsidian, ask Claude to run `vela view --out ~/Desktop/<name>.html` builds every page into one HTML file to send or print. Its header says when it was built, whether there were changes not yet committed, and how many problems `vela check` found. For a live call, open the dashboard instead (`vela explore`).

## How the vault is laid out

- Root pages: [[01-goals|Goals]], [[02-constraints|Constraints]], [[03-context-and-scope|Context and scope]], [[04-solution-strategy|Solution strategy]], [[04a-capability-delta|Capability delta]], [[11-unknowns-and-risks|Unknowns and risks]], [[12-glossary|Glossary]] and [[sources|Library]].
- [[05-building-blocks|Building blocks]]: one page per app, with its contracts.
- [[06-flows|Flows]]: flows across apps, and one runtime page per app.
- [[08-concerns|Concerns]], [[09-decisions|Decisions]] and [[13-epics|Epics]]: an index page and one page per item.
- `capabilities/`: one page per capability touched. `sessions/`: one header per session; the notes behind it stay on the lead's machine.

## Reading paths

| Reader | Pages, in order |
|---|---|
| CIO / CTO | [[01-goals\|Goals]] → [[03-context-and-scope\|Context and scope]] → [[11-unknowns-and-risks\|Unknowns and risks]] |
| Product | [[01-goals\|Goals]] → [[04a-capability-delta\|Capability delta]] → [[06-flows\|Flows]] |
| Architects | [[03-context-and-scope\|Context and scope]] → [[04-solution-strategy\|Solution strategy]] → [[05-building-blocks\|Building blocks]] → [[09-decisions\|Decisions]] |
| Team leads | Your app's page → how it behaves at run time and when things fail → [[13-epics\|Epics]] |
| QA | [[concern-testing\|Testing]] → [[06-flows\|Flows]] → [[13-epics\|Epics]] |
