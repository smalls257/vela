---
name: dump
description: Dump & Diverge session for an initiative vault. Captures a hunch, a one-liner or a pile of ideas as session capture lines, builds on them, runs a pre-mortem and a review checkpoint for the questions owed, and writes nothing to the plan pages until close. Use when the user has an idea and no documents yet.
argument-hint: "[what is on your mind]"
disable-model-invocation: true
---

# Dump & Diverge

The user has a hunch, a one-liner or nothing yet. Collect everything as captures. Push back on nothing. The plan pages change only at `/planner:close`.

Shared files live in `.claude/skills/planner/references/`. Read them when a step names them.

## Steps

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `dump`. Read the Dump & Diverge row of `.claude/skills/planner/references/MODES.md`.
2. Read `01-goals.md`, `11-unknowns-and-risks.md` and any parked captures in earlier session records (`→ park`), so you can build on what is already there. Do not repeat a parked idea as new.
3. Let the user talk. Capture each point as its own line, in their words, with their name or role as the origin. Tag it `idea`, `thought`, `unknown`, `worry` or `wild`.
4. Build on what they say. For each idea, offer one "what if" that removes a constraint, borrows from another domain, or turns the idea around. Write each as a capture with origin `(claude)`. Tag the far-fetched ones `[wild]`. Never judge an idea, and never say one will not work.
5. Collect questions as `[unknown]` captures. Do not try to answer them now.
6. When the user slows down, run the pre-mortem. Say: "It is six months from now and this initiative has failed. What went wrong?" Capture every answer as a `[worry]`.
7. After the pre-mortem, run the review checkpoint in `.claude/skills/planner/references/REVIEW.md`, with the checkpoint "after the pre-mortem" and the captures as its focus. The session record is the written plan here, so the reviewers read it with the vault's pages. Add to that focus: for each reading of the ask the user has given, who gains and who loses under it. Show the lead the digest it ends with, and capture what they take.

   When an answer names a contract, an agreement or a figure, ask who holds it, and capture it as `[unknown]` with "to fetch:", the document and who holds it, so a later Discover can ask for it and read it.
8. Commit a checkpoint after about every ten captures.

## Ends when

The user stops, or the pre-mortem and its review checkpoint are done. Commit, then tell the user: "Run `/planner:close` to mark each capture and open the PR." Do not run close yourself.

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded. Its hard stops still hold.

- Never edit a page outside `sessions/` during a dump.
- Never write `decided` or `fact`, and never mark captures. Marks are close's job.
- Never drop a wild idea. Close parks it or keeps it.
