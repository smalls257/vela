---
id: readme
type: index
title: Initiative vault
authored: authored
---

# Initiative vault

This vault holds one initiative. Start at [[01-goals|Goals]]. The format is in `CONVENTIONS.md`.

Prerequisites: Python 3.11 or later, and PyYAML (`python3 -m pip install pyyaml`).

## Setup checklist

1. Copy this folder to a new GitHub repository.
2. Copy the vela plugin in: `mkdir -p .claude/skills && cp -r <toolkit>/plugin .claude/skills/vela`.
3. In `.vela.yaml`, set `initiative` to the next free `INI-nnn` and `title` to the initiative's name.
4. List the files that hold `@solution-lead` with `grep -rl --exclude=README.md --exclude-dir=.git '@solution-lead' .`, then edit each file to put in your handle.
5. Rewrite `CLAUDE.md` in your own words and delete its first line.
6. Run `python3 .claude/skills/vela/bin/vela check`. It should report 0 errors.
7. Start every Claude Code session with `bin/claude-vela` (or `sh bin/claude-vela`). The copied plugin only loads through its `--plugin-dir` flag, so a plain `claude` will not find `/vela:dump` or `/vela:close`.
8. To read the vault without Obsidian, build the offline viewer to a path outside the vault: `python3 .claude/skills/vela/bin/vela view --out ~/Desktop/<name>.html`. It is one HTML file. Its header shows the commit, whether the vault had uncommitted changes, and the error and warning counts from `vela check` at build time.
9. Open the folder in Obsidian if you use it. `.obsidian/app.json` is committed; workspace files are ignored.

## How the vault is laid out

- Root pages: [[01-goals|Goals]], [[02-constraints|Constraints]], [[03-context-and-scope|Context and scope]], [[04-solution-strategy|Solution strategy]], [[04a-capability-delta|Capability delta]], [[11-unknowns-and-risks|Unknowns and risks]], [[12-glossary|Glossary]] and [[sources|Sources]].
- [[05-building-blocks|Building blocks]]: one page per app, with its contracts.
- [[06-flows|Flows]]: flows across apps, and one runtime page per app.
- [[08-concerns|Concerns]], [[09-decisions|Decisions]] and [[13-epics|Epics]]: an index page and one page per item.
- `capabilities/`: one page per capability touched. `sessions/`: one record per session.

## Reading paths

| Reader | Pages, in order |
|---|---|
| CIO / CTO | [[01-goals\|Goals]] → [[03-context-and-scope\|Context and scope]] → [[11-unknowns-and-risks\|Unknowns and risks]] |
| Product | [[01-goals\|Goals]] → [[04a-capability-delta\|Capability delta]] → [[06-flows\|Flows]] |
| Architects | [[03-context-and-scope\|Context and scope]] → [[04-solution-strategy\|Solution strategy]] → [[05-building-blocks\|Building blocks]] → [[09-decisions\|Decisions]] |
| Team seniors | Your app's building-blocks page → its runtime page → [[13-epics\|Epics]] |
| QA | [[concern-testing\|Testing]] → [[06-flows\|Flows]] → [[13-epics\|Epics]] |
