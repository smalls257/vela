---
name: import
description: Import session for an initiative vault. Turns material that already exists (folders of documents, decks, spreadsheets, code, wiki spaces, tickets, emails) into plan pages. The session works out with the user how to reach each source, registers every one in sources.md with a confirmed Kind, shows an import map before writing, then writes cited pages and one unknown per clash. Use when an initiative is already under way and the vault is empty or thin.
argument-hint: "[where the material lives, or none to resume]"
disable-model-invocation: true
---

# Import

The initiative already exists as a pile of material. Turn it into a vault without inventing anything. This skill fixes the output, not the route: the session works out with the user how to reach each source.

## Reaching the material

Use whatever access the user already has: local files, a clone, an export they make, a tool already in their session. Ask when you are unsure how to get at a source. Never ask for or store a credential, never upload material anywhere, and keep raw copies only in `.inbox/`, which is never committed. Read what you can reach, say what you cannot, and do not guess at the rest.

## Steps

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `discover` (an import is a Discover that arrives in bulk; there is no `import` mode in the record). Read the Discover row of `.claude/skills/planner/references/MODES.md`. Only the owner writes plan pages. On a reader copy the import is allowed, and everything it writes is a draft for the owner.
2. Read the `## Import ledger` in earlier session records. If one exists, this is a resume: list what is pending and carry on from it. Otherwise ask where the material lives, and agree with the user how each place is reached.
3. Register before reading. Add a `sources.md` row for every source you will use: `ID | Title | Owner | Date | Kind | Location`. Kind is `exists`, `intends` or `repo`, as `CONVENTIONS.md` defines. Propose a Kind for each and have the user confirm it, or override as `START.md` says. Location must let someone find it again: a path, a URL, `<url>@<sha>` for a repo, or `export of <space> on <date>`. A source you do not read is still listed, as skipped, with why.
4. Show the import map before writing a single plan page. One block per vault section: goals, constraints, context and scope, strategy, capabilities, apps and building blocks, contracts, flows, concerns, decisions, requirements, releases, epics, unknowns and risks, glossary. Under each say what was found, from which `SRC-nn`, what is duplicated, and what clashes. The user corrects the map. Write nothing until they have.
5. Write the pages in `CONVENTIONS.md` format, in batches, committing a checkpoint after each. Every line cites its source, and its state follows where it came from:
   - `exists` or `repo` gives a `fact`.
   - `intends` gives an `assumption`, or an `inkling` if it is vague. Anything about the future is an `assumption` whatever the Kind.
   - A decision is `decided` only when the source names who decided it and when. Otherwise it is an `assumption` plus an unknown asking the owner to confirm it. When `CONVENTIONS.md` has the `**Pending approval:**` rule and this is a reader copy, decisions carry it. If that rule is not there yet, note that in the report as coming.
   - A gap stays a gap. Say it in your own words, never copy document text, and never use general knowledge as a source.
6. Every clash between sources becomes one unknown naming both `SRC-nn`, with an owner handle and an ask-by date, as `MODES.md` says under "Unknowns". Never pick a side.
7. Large piles go in batches across sessions. Keep an `## Import ledger` in the session record: one line per source, `processed` or `pending`, so a later `/planner:import` resumes where this one stopped.

## Done only when

Do not say the import is done until each of these holds:

- [ ] Every source used has a row in `sources.md` with a user-confirmed Kind and a findable Location. Sources not read are listed as skipped, with why.
- [ ] The user saw the import map before any plan page was written, and corrected it.
- [ ] Every written line cites a `SRC-nn`, and its state follows step 5. Nothing is invented.
- [ ] Every clash is one unknown naming both sources, with an owner and an ask-by date.
- [ ] The import ledger in the session record lists processed and pending sources.
- [ ] `python3 .claude/skills/planner/scripts/planner check` has run. Errors are fixed and warnings are listed.
- [ ] `planner capture` and `planner next` have run.
- [ ] The session record holds an `## Import report`: coverage per section (rich, thin or empty), skipped sources, open clashes, and the next recommended session.

## Ends when

The checklist holds, or the user stops. If they stop early, write the ledger and the report for what was done. Run `git status` and confirm nothing under `.inbox/` is staged. Offer `/planner:explore` to see the map. Then tell the user: "Run `/planner:close` to finish the session and open the PR."

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded. Its hard stops still hold.

- Never ask for, keep or write a credential, and never upload material.
- Never commit anything from `.inbox/`.
- Never write a `fact` from an `intends` source, or `decided` without a named decider and date.
