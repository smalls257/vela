---
name: dump
description: Capture a hunch, a one-liner or a pile of ideas, build on them, and run a pre-mortem and a review checkpoint; nothing reaches the plan pages until close. Use when the user has an idea and no documents yet.
argument-hint: "[what is on your mind]"
disable-model-invocation: true
---

# Dump & Diverge

The user has a hunch, a one-liner or nothing yet. Collect everything as captures. Push back on nothing. The plan pages change only at `/vela:close`.

## Steps

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `dump`, including its step that asks once for the initiative's short name. Read the Dump & Diverge row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.
2. Read `01-goals.md`, `11-unknowns-and-risks.md` and the parked captures in earlier session records (`→ park`), to build on what is there. Do not repeat a parked idea as new.
3. Let the user talk. Capture each point as its own line, in their words, with their name or role as the origin and a tag of `idea`, `thought`, `unknown`, `worry` or `wild`: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela record add --origin "<name>" --tag idea "<their words>"`. It numbers the line; never number one yourself. If it stops, say why in plain words and stop.
   Keep the running map as `MODES.md` says under "The running map", silently: put each group the lead names on it, and never interrupt the lead to ask. Once the first account is out, by about the third turn, ask who has to say yes to this and who would push back; then ask one group a turn where it stands, and put two that pull apart side by side.
4. Build on what they say. For each idea, offer one "what if" that removes a constraint, borrows from another domain, or turns it around. Capture each with origin `claude`; tag the far-fetched ones `wild`. Never judge an idea, and never say one will not work.
5. Capture questions as `unknown`, unanswered for now.
6. When the user slows down, run the pre-mortem: ask them to imagine it is six months on and the initiative has failed, and ask what went wrong. It makes people say the risks they were too polite to raise. Put it in your own words, and capture every answer as a `worry`.
7. After the pre-mortem, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pre-mortem" and the captures as its focus. The session record is the written plan here, so the reviewers read it with the plan's pages. Show the digest as REVIEW says, without comment on the ideas: it lists questions nobody has answered and is not a verdict on any idea. Capture what the lead takes, and keep building on what they say.
8. When an answer names a contract, an agreement or a figure, ask who holds it, and capture it as an `unknown` with "to fetch:", the document and who holds it, so a later Discover can fetch it. Do the same for any contract or document the captures themselves name.
9. On a yes to an existence question (stored value, an outside party), capture one `thought` that starts with the copy ID and ends with the subject note: `- [thought] (<name>) Q-FIN-01@INI-001: yes, <what>. type at close: SV`. Use `type at close: PTY` for an outside party. Dump writes no pages, so close types the subject and writes the copy's ledger row. To the lead, say it plainly: "Noted: the plan holds money or points on customers' behalf."
10. After about every ten captures, commit a checkpoint with `vela close stage --checkpoint --for-lead`.

11. Before the session ends, run the map's read-back (`vela map show --for-lead`): every waiting item settled, captured as an `unknown`, or set aside.

## Ends when

The user stops, or the pre-mortem and its review checkpoint are done. Commit with `vela close stage --checkpoint --for-lead`. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session": it files each capture and opens the PR.

## Never

- Never edit a page outside `sessions/` during a dump.
- Never write `decided` or `fact`, and never mark captures (no `--mark`). Marks are close's job.
- Never present the checkpoint's digest as a verdict on an idea.
- Never drop a wild idea. Close parks it or keeps it.
