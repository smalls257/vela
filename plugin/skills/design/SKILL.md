---
name: design
description: Tech design for one app a solution lead has handed off from an initiative vault. Interviews the app's senior one question at a time, starting from the app's walking skeleton, and writes a summary-first design doc, its ADRs and CONTEXT.md in the vault's docs folder on a design branch, ending in a pull request. Use when a team is ready to settle how its handed-off app gets built.
argument-hint: "--app <APP-id> [slug]"
disable-model-invocation: true
---

# Design

The vault already says what the app must do: its pages, its share of each requirement, the contracts it provides and consumes, its epics and their criteria, its releases and its open questions. This session settles how the team builds it, and writes that where the team's review and the explorer find it. The vault is the folder this runs in; `--app APP-x` names the app.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner`. If the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, find it the way `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Where the planner runs from". Every file this skill names sits beside this one.

## 1. Start

A design opens no session record and touches no planner page, so START's numbered steps don't apply. Its shared rules do: read START.md and follow "Where the planner runs from", "Owner or reader", "Plain names and a page a person can hold", "Shell that runs on a Mac and on Linux" and "The user may override any rule", with its hard stops.

Then the two voices. For the conversation, read the conversation voice START.md points to (`references/CONVERSATION-VOICE.md` in the plugin root) and the vault's `voice/VOICE.md` when there is one; the vault owner's own rules there come first. For the pages, read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and the vault's `voice/examples/`. Read house-voice as a file: only a person can start it as a skill.

In conversation the senior hears names, not codes. Say "the calendar entries", "the consent check", "the question about mail"; the IDs go in the files, on Trace lines and in the pull request.

Then follow `${CLAUDE_PLUGIN_ROOT}/references/TECH-DESIGN-FROM-VAULT.md`. It checks the app is handed off, runs `planner handoff verify`, records the vault commit, opens the `design/<slug>` branch, and says what to read and in what order. It replaces a requirements doc: in a vault the app's allocated rows, its contracts and its epic criteria are what the design answers for.

If `docs/tech-design/<slug>.md` already exists, say in one line where it stands and offer the choices that fit:

- `in-progress`: carry on from the first unfinished section or the first open deferral or question;
- `complete-with-gaps`: reopen it to close the gaps (each closed gap leaves `gaps[]`), redo it, or start a new slug;
- `complete`: redo it, or start a new slug.

No vault in the folder: follow `STANDALONE.md` instead, which starts from a requirements doc.

## 2. Start from the walking skeleton

The tracer is a thin flow that runs end to end through every app, built first and kept. Before the first question, find this app's piece of it. In a vault with slice pages it is `slices/SLC-001-*.md`: its `**Flows:**` link one or more flows, and its `## Not in this slice` says what it leaves out and why; `planner handoff` lists every slice this app takes part in. A vault without slice pages names it on release one in `04b-releases.md`, on a `- **Tracer:**` bullet, as links to one or more flows and, after a comma, the thin version in plain words; a `- **Not in the tracer:**` bullet says what release one leaves out and why. The walking skeleton is the smallest path through this app's components that carries those flows, with the other apps' sides stubbed at their contracts until their pieces land.

Propose it in a sentence or two and ask whether it's right.

When neither names a tracer, ask one question first: which flow should release one prove end to end? Recommend one from the flows this app takes part in, with the reason ("the 7:30 digest, because it crosses all three apps"). A release that says `**Tracer:** none, <reason>` has no skeleton to serve: say so, and design in template order. Then design its components and contracts first, and widen from there to the rest of `TECH-DESIGN-FORMAT.md`. The skeleton changes the order of the interview, not its coverage: every trace target still needs an owner.

For Heron's Desktop agent it read: "At 7:30 the agent asks the consent check, reads the person's calendar entries, sends them to the Summarizer and shows the digest. Consent and identity and the Summarizer are stubbed at their contracts until those teams' pieces land."

If the vault has no releases page at all, propose a skeleton from the app's first epic and ask. If the senior says the skeleton isn't ready ("we don't know the Summarizer's shape yet"), say once what it protects (a team that can show the flow working early), record their words as an override, and carry on in template order.

## 3. Ask one question at a time

`GRILL-LOOP.md` holds the loop: one question, your recommended answer with a one-line reason, then wait; concrete edge cases over general ones; checks against this conversation, then the documents, then the code. Ask until the answer is specific enough to build from. When the code can answer, read the code.

## 4. Write as you go

Write each answer into `docs/tech-design/<slug>.md` as the section it belongs to settles, and commit it on the branch with a message naming the section. Batching loses work when a session is cut off, and the branch is the resume point.

- The doc follows `TECH-DESIGN-FORMAT.md`, its frontmatter `FRONTMATTER-FORMAT.md`. It opens with a summary a reader can take in at once: what the app does for people, the three to five decisions that shape it, the walking skeleton, and what is still open. Full detail follows below it, each topic under about 120 words with tables for facts, as house-voice says.
- An ADR only when a decision is hard to reverse, surprising without context and a real trade-off: `ADR-FORMAT.md`.
- The vault's glossary owns its terms. `CONTEXT.md` holds only terms the app adds: `CONTEXT-FORMAT.md`.
- A choice deliberately put off is a deferral (`D-XXX`); a question nobody can answer yet is an open question (`OQ-XXX`). `FRONTMATTER-FORMAT.md` says which is which.
- In a mermaid diagram a `;` ends the statement, so a message or label never holds one: `R->>S: stop; cancel` stopped Heron's withdrawal flow from drawing. Write a comma or "then".

## 5. When the vault is wrong or silent

The design settles how, and the vault settles what. When the work shows a missing requirement, a contract that can't carry what's asked of it, or a vault answer the senior disputes, write it as an open question with `**Challenges:**` naming the vault ID and the scenario that shows the problem. Tell the senior in plain words, and that `/planner:challenge <vault ID>` raises it with the solution lead. Then carry on with every branch it doesn't touch. The design never edits planner pages; its own files under `docs/` and `CONTEXT.md` are its to write.

If nothing is left that the gap doesn't touch, say so, leave the doc at `in-progress`, and say which challenge it waits on.

## 6. Review, then the self-audit

Once every section is written, run `REVIEW-CHECKPOINT.md`: five fresh reviewers, one area each, find what nobody in the room mentioned. Then run `NEG-AUDIT.md`.

Tell the senior what the audit found as plain findings, the thing that is wrong and what you'd do about it: "All seven components run as one process, so one bug in the core takes the agent down. I'd accept that and say how it fails closed, or split the readers out." Keep the checklist itself for the pull request body, which is where a team repo keeps session notes.

A gap the senior accepts goes into `gaps[]` in the same plain words, with the senior's handle in `acknowledged_by` (ask once if you don't know it). The status rules are in `FRONTMATTER-FORMAT.md`: `complete` needs a clean audit and no finding left open; anything accepted or left open makes it `complete-with-gaps`.

## 7. Finish

Before the pull request, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check-diagrams docs/tech-design/<slug>.md` with each ADR that has a diagram. Exit 1 names every diagram mermaid cannot draw, at its line: fix each and run it again. A W604 means Node.js is missing and nothing was checked; tell the senior so, and never call the diagrams checked.

Push the branch and open the pull request when the design is `complete` or `complete-with-gaps`, after saying what will be sent and getting a yes. Its body holds the summary, the audit checklist and the open questions that challenge the vault. Never say a push or a pull request exists unless the tool printed it.

When the design challenges vault items, offer a handover note for the senior at `docs/handover-<slug>-challenges.md`: one entry per challenge, most urgent first, each with the one `/planner:challenge <ID>` command that raises it and the open question's text as the design has it. Then say the next step in one line: `/planner:breakdown` plans the build from this design.

If the session runs out of room first, `TECH-DESIGN-FROM-VAULT.md` says how to leave it.
