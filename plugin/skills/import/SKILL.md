---
name: import
description: Turn material that already exists (documents, decks, spreadsheets, code, wiki spaces, tickets, emails) into cited plan pages, with an import map shown first. Use when an initiative is under way and the plan is empty or thin.
argument-hint: "[where the material lives, or none to resume]"
disable-model-invocation: true
---

# Import

The initiative already exists as a pile of material. Turn it into a plan without inventing anything. This skill fixes the output, not the route: work out with the user how to reach each source.

Every `vela` below is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela`. Relay its `--for-lead` lines. When a command can't express what the lead wants, say so and stop. Name sources by title when you talk and things by name; an ID only where the lead must act on one.

## Reaching the material

Use whatever access the user already has: local files, a clone, an export, a tool already in their session. Ask when unsure how to reach a source. Never ask for or store a credential, never upload material anywhere, and keep raw copies only in `.inbox/`, which is never committed. Read what you can reach, say what you cannot, and do not guess at the rest.

## Steps

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `discover` (an import is a Discover that arrives in bulk; there is no `import` mode in the record). Read the Discover row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. Only the owner writes plan pages. On a reader copy the import is allowed, and everything it writes is a draft for the owner.
2. Read the `## Import ledger` in earlier session records. If one exists, resume: list what is pending and carry on. Otherwise ask where the material lives, and agree with the user how each place is reached.
3. Register before reading. Propose a Kind for each source (`exists`, `intends` or `repo`, as `vela conventions "Certainty and sources"` defines), have the user confirm it or override as `START.md` says, and register it with `vela add source --title "<title>" --owner <handle> --date <YYYY-MM-DD> --kind <kind> --location "<where>" --for-lead`. Location must let someone find it again: a path, a URL, `<url>@<sha>` for a repo (pass the URL as git prints it; the command takes out any credential and says so), or `export of <space> on <date>`. A source you do not read is still listed, as skipped, with why.
4. Show the import map first, one block per plan section: goals, constraints, context and scope, strategy, capabilities, apps and building blocks, contracts, flows, concerns, decisions, requirements, releases, epics, unknowns and risks, glossary. Under each say what was found, from which source, what is duplicated, and what clashes, in about five lines; count the rest. The user corrects the map. Write nothing until they have.

   > **Contracts.** The partner guide describes the nightly booking file; the ops runbook says hourly, so that's one open question. The roadmap deck's live feed by Q4 stays not decided yet.

5. Write the pages in the format `vela conventions "<section>"` gives for each, in batches, committing a checkpoint after each (in a reader copy, which has no git, write the batch and skip the commit). Every line cites its source, and its state follows where it came from:
   - `exists` or `repo` gives a `fact`.
   - `intends` gives an `assumption`, or an `inkling` if it is vague. Anything about the future is an `assumption` whatever the Kind.
   - A decision a source names is an `assumption` here, never `decided`: only a grill decides, and the check flags `decided` with no grill behind it. When the source names who decided it and when, note both on the item, so the grill has them ("Decided by the CTO on 3 March, per the architecture decision record; grill to confirm"). When it names neither, add an unknown asking the owner to confirm it. In a reader copy, decisions carry `**Pending approval:**` as `vela conventions "Pending approval"` says.
   - Don't build case tables, strict diagrams or slices from imported material unless the source states them; leave those for boundary and grill, and let the warnings show.
   - A gap stays a gap. Write in the house voice (`house-voice`), your own words and plain names, the source linked on the words that rely on it, no bare ID in the sentence. Never copy document text or use general knowledge as a source.
6. Every clash between sources becomes one unknown naming both sources, with an owner handle and an ask-by date: `vela add unknown --name "<name>" --owner <handle> --for-lead`. Never pick a side.
7. Large piles go in batches across sessions. Keep an `## Import ledger` in the session record: one line per source, `processed` or `pending`, so a later `/vela:import` resumes where this one stopped.

## Done only when

The import is done only when each of these holds:

- [ ] Every source used has a row in `sources.md` with a user-confirmed Kind and a findable Location; unread ones are listed as skipped.
- [ ] The user corrected the import map before any plan page was written.
- [ ] Every written line cites a source, with the state step 5 gives.
- [ ] Every clash is one unknown with an owner and an ask-by date.
- [ ] The import ledger lists processed and pending sources.
- [ ] `vela check` has run: errors fixed, warnings listed.
- [ ] `vela capture` and `vela next` have run.
- [ ] The record holds an `## Import report`: coverage per section (rich, thin or empty), skipped sources, open clashes, the next recommended session.

## Ends when

The checklist holds, or the user stops. If they stop early, write the ledger and the report for what was done. In an owner's vault, run `git status` and confirm nothing under `.inbox/` is staged (a reader copy has no git: skip it). Rebuild the dashboard with `vela explore` (no `--serve`). If it exits 0, say: "The dashboard is up to date: dashboard.html — open it, or run /vela:explore to ask Claude from it". If it fails, say "The dashboard could not be built: <message>." and go on; a failed build never ends the import. Then tell the user: "Run `/vela:close` to finish the session and open the PR."

## Never

- Never write a `fact` from an `intends` source, or `decided` at all: a decision a source names is an `assumption` with its decider and date in a note, until a grill.
