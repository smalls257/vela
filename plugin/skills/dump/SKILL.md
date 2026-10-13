---
name: dump
description: Dump & Diverge session for an initiative vault. Captures a hunch, a one-liner or a pile of ideas as session capture lines, builds on them, runs a pre-mortem and a review checkpoint for the questions owed, and writes nothing to the plan pages until close. Use when the user has an idea and no documents yet.
argument-hint: "[what is on your mind]"
disable-model-invocation: true
---

# Dump & Diverge

The user has a hunch, a one-liner or nothing yet. Collect everything as captures. Push back on nothing. The plan pages change only at `/planner:close`.

Shared files live in `${CLAUDE_PLUGIN_ROOT}/references/`. Read them when a step names them.

## Steps

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `dump`, including its step that asks once for the initiative's short name. Read the Dump & Diverge row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.
2. Read `01-goals.md`, `11-unknowns-and-risks.md` and any parked captures in earlier session records (`→ park`), so you can build on what is already there. Do not repeat a parked idea as new.
3. Let the user talk. Capture each point as its own line, in their words, with their name or role as the origin. Tag it `idea`, `thought`, `unknown`, `worry` or `wild`.
4. Build on what they say. For each idea, offer one "what if" that removes a constraint, borrows from another domain, or turns the idea around. Write each as a capture with origin `(claude)`. Tag the far-fetched ones `[wild]`. Never judge an idea, and never say one will not work.
5. Collect questions as `[unknown]` captures. Do not try to answer them now.
6. When the user slows down, run the pre-mortem. Say: "It is six months from now and this initiative has failed. What went wrong?" Capture every answer as a `[worry]`.
7. After the pre-mortem, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pre-mortem" and the captures as its focus. The session record is the written plan here, so the reviewers read it with the vault's pages. Show the lead the digest it ends with, as REVIEW section 5 says: once, at the pause after the pre-mortem, at most three plain questions with a recommended answer each, and one line saying how many more are written down. Capture what they take. The digest lists questions nobody has answered. It is not a verdict on any idea. Show it without comment on the ideas, and keep building on what the lead says.

   When an answer names a contract, an agreement or a figure, ask who holds it, and capture it as `[unknown]` with "to fetch:", the document and who holds it, so a later Discover can ask for it and read it. Do the same for any contract or document the captures themselves name.

   When the lead answers yes to an existence question, such as stored value or an outside party, capture it as one `[thought]` that starts with the copy ID and ends with the subject note: `- [thought] (<name>) Q-FIN-01@INI-001: yes, <what>. type at close: SV`. Use `type at close: PTY` for an outside party. Dump writes no pages, so close types the subject and writes the copy's ledger row.
8. Commit a checkpoint after about every ten captures.

## Ends when

The user stops, or the pre-mortem and its review checkpoint are done. Commit. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session": it files each capture and opens the PR. If the conversation is cut off, the record holds the resume point.

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded. Its hard stops still hold.

- Never edit a page outside `sessions/` during a dump.
- Never write `decided` or `fact`, and never mark captures. Marks are close's job.
- Never present the checkpoint's digest as a verdict on an idea.
- Never drop a wild idea. Close parks it or keeps it.
