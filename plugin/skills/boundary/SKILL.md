---
name: boundary
description: Boundary session for an initiative vault. Turns a decided direction into apps. Offers 2 or 3 ways to cut it into apps, then reads back one boundary sheet per app (what it does and does not do, its containers, the contracts it provides and consumes, how it behaves on failure, its concern cells), writes the confirmed lines as app, contract and runtime pages at assumption, and runs a review checkpoint on the new apps and contracts. Use when the direction is decided and no app page says who builds what.
argument-hint: "[the decided item, or an app]"
disable-model-invocation: true
---

# Boundary

Turn a decided direction into apps a team senior can take. Until an app page exists, the catalogue's app and contract questions are owed by nothing, `planner status` has nothing to show, and epics and handoff have nothing to work on. Boundary never decides: every page it writes is an `assumption` until a Grill.

The planner is `python3 .claude/skills/planner/bin/planner`. The page formats are `CONVENTIONS.md`: "Frontmatter", "IDs", "Fact bullets" for contracts, "Fact tables" for containers, "Concern cells and waivers", and the ladder under "Areas and stages".

## 1. Start

Run the steps in `.claude/skills/planner/references/START.md` with mode `boundary`. Read the Boundary row of `.claude/skills/planner/references/MODES.md`.

Read the direction: `04-solution-strategy.md` and every page it links for the picked option, `03-context-and-scope.md` for the systems today and the apps in and out of scope, the existing building-blocks pages, `06-runtime/06-flows.md`, the concern pages, and the open unknowns and risks that block any of them. If the direction is not `decided`, say so and name what is still open: an app cut on an undecided direction may be cut again. Go on only if the user says to, and record that as an override as `START.md` says.

## 2. Offer the cuts

Offer 2 or 3 ways to cut the direction into apps, never one and never more than three. A cut names every app it touches, each with its `change` (`new`, `changed`, `integrated`, `unchanged` or `retired`), and says in a line or two:

- which app owns each job the direction needs, and which job no app owns yet;
- what it makes easy and what it makes hard: an extra service to run, a link held in two places, a team with no owner;
- which decided item, source or unknown each claim rests on.

Capture each cut as a `[thought] (claude)` line. Say which cut you prefer and why. Capture the user's reaction to each and the cut they pick. A rejected cut gets a capture with its reason. If they reject them all, capture why and offer new cuts.

Write the picked cut on `05-building-blocks/05-building-blocks.md` as a page-level `- **Options considered:** <picked cut> (picked); <cut>: rejected, <reason>; ...` bullet, at once, with its capture and a `## Changes` row.

## 3. Read back one boundary sheet per app

Take the apps of the picked cut whose `change` is `new` or `changed`, one at a time. An `integrated`, `unchanged` or `retired` app gets a page only for what crosses its boundary. For each, show its sheet as a numbered list:

1. **Does:** what the app decides or keeps, in the domain's words.
2. **Does not:** the jobs that stay elsewhere, each naming the app or party that keeps it.
3. **Containers:** each main part and its job.
4. **Provides:** each contract, as `CON-nnn <name>`, with what crosses the boundary in each direction and each consumer.
5. **Consumes:** each contract it relies on, provided by another app or an outside provider.
6. **On failure:** what the app and each consumer do when it, or something it consumes, is down or slow.
7. **Concerns:** one line per concern page: `unknown` with the unknown that must be answered first, `n/a` with why, or `unexamined`. Never `addressed`, because only a Grill decides one.

Label every line with what it rests on: a decided item, a `SRC-nn`, the user's own words, or `(claude)` for your proposal. A line with nothing under it is a proposal, and it says so. Write nothing until the user has given an explicit yes to that line. Silence, or "looks fine" with no yes per line, does not count: ask again. A correction replaces the line, and the corrected line needs its own yes. A line the user cannot answer becomes an unknown with an owner handle and an ask-by date, and the item it blocks lists it.

## 4. Write the confirmed lines

After each sheet, write what was confirmed and commit a checkpoint:

- **The app page:** `05-building-blocks/<app>-building-blocks.md`, `type: app-building-blocks`, `id: APP-<slug>`, `state: assumption`, the app's `change`, its `owner` handle, `authored: authored`, and the `sources` its lines rest on. "Does" and "does not" become its opening paragraphs. Set `stage` by the ladder in `CONVENTIONS.md`, never higher than its entry list allows: `target` once the page cites a source that is not a dump, `baseline` before that. An app that already has a page keeps it: change only the lines the user confirmed.
- **Containers:** the table `| Container | Job | Contracts served or used | Proposed by | State |`, every State `assumption`.
- **Contracts it provides:** under `## Contracts this app provides`, one `### CON-nnn <name>` each, with every required bullet: `**Crosses the boundary:**`, `**Consumers:**` linking each consumer's page, `**Change policy:**`, `**Change:**` and `**State:** assumption`. An outside provider's contract lives on the consumer's page with `**Provider:**`. New IDs take the next free number: grep the vault for the existing IDs of that kind, and read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`, because another open session may already hold the next one.
- **The runtime page:** `06-runtime/apps/<app>-runtime.md`, `type: app-runtime`, `id: RUN-<slug>`, `state: assumption`, with the confirmed failure line under `## On failure`.
- **Concern cells:** one row for the app on each concern page, as confirmed.
- **Scope:** the app in the apps-in-scope list on `03-context-and-scope.md`, linking its page.

Each line written also gets a capture line and a `## Changes` row. Mark that capture at once: `→ keep: [[<page>#<heading>|<ID>]] (assumption)`. This is an exception to leaving marks off until close, as Discover does for facts. Close leaves these alone.

Then run `python3 .claude/skills/planner/bin/planner render` and `python3 .claude/skills/planner/bin/planner check`, fix every error the new pages cause, and commit the checkpoint with every file render reported, by exact path.

## 5. Review the new apps and contracts

Once every sheet is written, run the review checkpoint in `.claude/skills/planner/references/REVIEW.md`, with the checkpoint "after the pages are written" and the new app, contract and runtime pages as its focus. Each new app and contract is a subject now, so the catalogue owes its app and contract questions: run `python3 .claude/skills/planner/bin/planner questions --subject <ID>` for each and show the copies it owes. Show the lead the digest as REVIEW section 5 says, and capture what they take.

## 6. Finish

Run `git status` and confirm nothing under `.inbox/` is staged. Tell the user: "Run `/planner:close` to finish the session and open the PR. Then run `/planner:grill <APP-id>` to decide each app's page and its contracts."
