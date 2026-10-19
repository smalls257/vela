---
name: import
description: Turn material that already exists (documents, decks, spreadsheets, code, wiki spaces, tickets, emails) into cited plan pages, with an import map shown first. Use when an initiative is under way and the plan is empty or thin.
argument-hint: "[where the material lives, or none to resume]"
disable-model-invocation: true
---

# Import

Turn a pile of existing material into a plan without inventing anything: read the sources, show the import map, then work the queue with the lead about four things at a time.

Every `vela` below is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela`. Relay its `--for-lead` lines. When a command can't express what the lead wants, say so and stop. Name sources by title when you talk and things by name.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `discover`. Only the owner writes plan pages; on a reader copy everything written is a draft for the owner. If an earlier record has an `## Import ledger`, resume from what it lists as pending.

## 1. Read the sources

Use the access the user already has: local files, a clone, an export, a tool in their session. Never ask for or store a credential, never upload material, and keep raw copies only in `.inbox/`, which is never committed. Say what you can't reach.

Propose each source's Kind (`exists`, `intends` or `repo`, as `vela conventions "Certainty and sources"` defines), let the user confirm it, and register it: `vela add source --title "<title>" --owner <handle> --date <YYYY-MM-DD> --kind <kind> --location "<where>" --for-lead`. Location must find it again: a path, a URL, `<url>@<sha>` for a repo (the command takes out any credential and says so), or `export of <space> on <date>`. A skipped source is listed, with why.

As you read, queue what only the lead can settle, with the answer you'd give: `vela import add --type decision "<what a source says was decided, by whom, when>" --source <SRC> --propose "<answer>" --why "<why>"`. Use `--type clash` with both `--source`s for two sources that disagree, proposing which wins and why, and `--type stale` for a fact that may be out of date.

## 2. Show the import map

One block per plan section with something in it (goals, constraints, context and scope, strategy, capabilities, apps, contracts, flows, concerns, decisions, requirements, releases, epics, unknowns and risks, glossary): what was found, from which source, what clashes, in about five lines.

> **Contracts.** The partner guide describes the nightly booking file; the ops runbook says hourly, so I'll ask you which wins. The roadmap deck's live feed by Q4 stays a plan.

End the map with the voice question, once: "I'd keep the documents' exact words, quoted and cited, for requirements, contract and legal terms, numbers and direct quotes, and write each page's explaining sentences in the plan's voice. That way, keep everything as written, or voice it all?" Capture the answer, then `vela import wording --as split --yes <capture>` (or `keep`, or `voice`; add `--source <SRC>` when they answer per source). Until they answer, keep every word as written.

The user corrects the map. Write nothing until they have.

## 3. Work the queue

`vela import next --for-lead` gives the next batch, about four, each with your proposal. Ask them in one turn. Capture the answer, settle each by its number (`vela import close 1 --as decided --how "<a line>"`, or the outcome the lead chose), and only then ask for the next batch.

- **A stated decision the lead says yes to** is decided, citing the document: `vela decide <ID> --readback <capture> --yes <capture> --stated-in <SRC>`. One they aren't sure of stays an `assumption`, the document noted. Never write `decided` any other way.
- **A clash** goes the way the lead picks. If they don't know, both sides become one open question naming both sources: `vela add unknown --name "<name>" --owner <handle> --for-lead`, with an ask-by date.
- **A stale fact** is kept, replaced or opened the same way.

Write pages in the format `vela conventions "<section>"` gives, committing after each batch with `vela close stage --checkpoint --for-lead` (in a reader copy, which has no git, write the batch and skip the commit). Stamp each page with the wording the lead chose: `vela import page <path> --source <SRC>`, one `--source` per document it draws on.

- Every line cites its source. `exists` or `repo` gives a `fact`, `intends` an `assumption` (an `inkling` if vague), and anything about the future is an `assumption`.
- A requirement, a contract or legal term, a number or a direct quote keeps the source's words, as `> "<their words>"` with the source linked. Explaining sentences follow `house-voice` on a page the lead agreed to voice.
- Don't build case tables, strict diagrams or slices from imported material unless the source states them; leave those for boundary and grill, and let the warnings show.
- A gap stays a gap. General knowledge is never a source.

Keep an `## Import ledger` in the session record, one line per source, `processed` or `pending`, so a later import resumes.

## Done only when

- [ ] Every source used is in `sources.md` with a confirmed Kind and a findable Location; skipped ones are listed.
- [ ] The user corrected the map and answered the voice question (or the words stayed as written) before any page was written.
- [ ] `vela import show --for-lead` shows nothing asked and unsettled.
- [ ] Every written line cites a source, and every written page is stamped.
- [ ] `vela check` has run (errors fixed, warnings listed), then `vela capture` and `vela next`.
- [ ] The record holds the ledger and an `## Import report`: coverage per section (rich, thin or empty), skipped sources, open clashes, the next session.

## Ends when

The checklist holds, or the user stops; write the ledger and report for what was done. In an owner's vault, run `git status` and confirm nothing under `.inbox/` is staged. Rebuild the dashboard with `vela explore` (no `--serve`). If it exits 0, say: "The dashboard is up to date: dashboard.html — open it, or run /vela:explore to ask Claude from it". If it fails, say "The dashboard could not be built: <message>." and go on; a failed build never ends the import. Then say: "Run `/vela:close` to finish the session and open the PR."
