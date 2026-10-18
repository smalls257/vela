---
name: design
description: Tech design for one app handed off from an initiative vault. Interviews the team lead one question at a time, from the app's walking skeleton, and writes a summary-first design, its ADRs and CONTEXT.md on a design branch, ending in a pull request.
argument-hint: "--app <APP-id> [slug]"
disable-model-invocation: true
---

# Design

The vault already says what the app must do. This session settles how the team builds it, and writes that where the team's review and the dashboard find it. The vault is the folder this runs in; `--app APP-x` names the app. Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`${CLAUDE_PLUGIN_ROOT}/references/START.md`, "Where vela runs from"). Every file this skill names sits beside this one.

## 1. Start

Before your first question, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`; write the design's prose through `house-voice` (`${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and the vault's `voice/examples/`, read as files: only a person can start house-voice).

First run `vela freshness --for-lead`. If it exits 3, this copy is behind the shared plan: stop, say what it printed in your words and offer to bring it up to date (`git switch main`, then `git pull --ff-only`), and go on once it is. When it says the copy is up to date, say nothing about it. A stale copy says an app isn't handed off when main says it is. If the command fails, say in one plain sentence that you couldn't check, then go on.

A design opens no session record, so START's numbered steps don't apply; its rules "Owner or reader", "Plain names and a page a person can hold", "Shell that runs on a Mac and on Linux" and "The user may override any rule" do, and so does "Relaying a command" for every `--for-lead` line. When the terms slice, tracer or grill first come up, define each once from `vela terms <word>`.

In conversation the team lead hears names, not codes. Say "the calendar entries", "the consent check", "the question about mail"; the IDs go in the files, on Trace lines and in the pull request.

Then follow `${CLAUDE_PLUGIN_ROOT}/references/TECH-DESIGN-FROM-VAULT.md`. It checks the app is handed off, runs `vela handoff verify`, records the vault commit, opens the `design/<slug>` branch, and says what to read and in what order.

Read your app's slices' flow check from the handoff rather than running it again: `handoffs/<APP-id>.md`, under `## Flow checks when written`. If the handoff record has no `## Flow checks when written` section, run `vela check-slice <slice> --for-lead` once. If a slice is 'not fully checked' or has open findings, tell the team lead before you design against it.

If `docs/tech-design/<slug>.md` already exists, say in words where it stands and offer the choices that fit: at `complete-with-gaps`, "The design is finished, with 3 known gaps. Close the gaps, redo it, or start a separate design?" (each closed gap leaves `gaps[]`); at `complete`, redo it or start a separate one; at `in-progress`, carry on from the first unfinished section or open question.

No vault in the folder: follow `STANDALONE.md` instead, which starts from a requirements doc.

## 2. Start from the walking skeleton

Before the first question, find this app's piece of the tracer: the tracer slice page (`slices/SLC-001-*.md`, its `**Flows:**` and `## Not in this slice`) or, with no slice pages, release one's `- **Tracer:**` and `- **Not in the tracer:**` bullets in `04b-releases.md`. The walking skeleton is the smallest path through this app's components that carries those flows, with the other apps' sides stubbed at their contracts until their pieces land.

Propose it in a sentence or two and ask whether it's right.

When neither names a tracer, ask one question first: which flow should release one prove end to end? Recommend one from the flows this app takes part in, with the reason ("unlocking a bike, because it crosses all three apps"), and write it in the doc as "Nobody named the first working path yet, so this one is a proposal for the team lead to confirm." A release that says `**Tracer:** none, <reason>` has no skeleton to serve: say so, and design in template order. Otherwise design the skeleton's components and contracts first, then widen to the rest of `TECH-DESIGN-FORMAT.md`. The skeleton changes the order of the interview, not its coverage: every trace target still needs an owner.

For the Fernway Rider app it read: "The rider scans a dock, the app asks the payment check, sends the unlock to the Dock service and shows the bike's number. The payment check and the Dock service are stubbed at their contracts until those teams' pieces land."

If the vault has no releases page at all, propose a skeleton from the app's first epic and ask. If the team lead says the skeleton isn't ready ("we don't know the Dock service's shape yet"), say once what it protects (a team that can show the flow working early), record their words as an override, and carry on in template order.

## 3. Ask one question at a time

`GRILL-LOOP.md` holds the loop: one question, your recommended answer with a one-line reason, then wait; concrete edge cases over general ones; checks against this conversation, then the documents, then the code. Ask until the answer is specific enough to build from. When the code can answer, read the code.

## 4. Write as you go

Write a choice in only after the person says yes to it: propose it with its reason ("I'd keep the key behind a small interface, so it can move later. OK?") and wait. Your own expertise is a recommendation, not a decision. Write each answer into `docs/tech-design/<slug>.md` as its section settles, and commit it on the branch with `vela team commit --about "<the section>"`, naming the section. Batching loses work when a session is cut off; the branch is the resume point.

- The doc follows `TECH-DESIGN-FORMAT.md`, its frontmatter `FRONTMATTER-FORMAT.md`: a summary first, then full detail, each topic under about 120 words.
- An ADR only when a decision is hard to reverse, surprising without context and a real trade-off: `ADR-FORMAT.md`.
- The vault's glossary owns its terms. `CONTEXT.md` holds only terms the app adds: `CONTEXT-FORMAT.md`.
- A choice deliberately put off is a deferral (`D-XXX`); a question nobody can answer yet is an open question (`OQ-XXX`). `FRONTMATTER-FORMAT.md` says which is which.
- In a mermaid diagram a `;` ends the statement, so a message or label never holds one: `R->>S: stop; cancel` stopped a cancel-hold flow from drawing. Write a comma or "then".

## 5. When the vault is wrong or silent

The design settles how, and the vault settles what. When the work shows a missing requirement, a contract that can't carry what's asked of it, or a vault answer the team lead disputes, write it as an open question with `**Challenges:**` naming the vault ID and the scenario that shows the problem. Tell the team lead in plain words, and that `/vela:challenge <vault ID>` raises it with the solution lead. Then carry on with every branch it doesn't touch. The design never edits vault pages; its own files under `docs/` and `CONTEXT.md` are its to write.

If nothing is left that the gap doesn't touch, say so, leave the doc at `in-progress`, and say which challenge it waits on.

## 6. Review, then the self-audit

Once every section is written, run `REVIEW-CHECKPOINT.md`. Then run the self-audit in `${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md`.

Tell the team lead the findings in plain words, what is wrong and what you'd do, about four at a time: "All seven components run as one process, so one bug in the core takes the agent down. I'd accept that and say how it fails closed, or split the readers out." The checklist itself goes in the pull request body.

A gap the team lead accepts goes into `gaps[]` in the same plain words, with their handle in `acknowledged_by` (ask once if you don't know it). The status rules are in `FRONTMATTER-FORMAT.md`: `complete` needs a clean audit and no finding left open; anything accepted or left open makes it `complete-with-gaps`.

## 7. Finish

Before the pull request, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela check-diagrams docs/tech-design/<slug>.md` with each ADR that has a diagram. Exit 1 names every diagram mermaid can't draw, at its line: fix each and run it again. A W604 means Node.js is missing and nothing was checked; tell the team lead so, and never call the diagrams checked.

Push the branch and open the pull request when the design is `complete` or `complete-with-gaps`, after saying what will be sent and getting a yes. Its body holds the summary, the audit checklist and the challenges. Never say a push or a pull request exists unless the tool printed it; if git or GitHub fails, say in one plain sentence that it didn't go, never the raw error.

When the design challenges vault items, offer a handover note at `docs/handover-<slug>-challenges.md`, titled `# Questions the <app> team is raising with the planning lead`: one entry per challenge, most urgent first, each named in words with its ID as a tag, the one `/vela:challenge <ID>` command that raises it, and the open question's text as the design has it. Then say the next step in one line: `/vela:breakdown` plans the build from this design.

When a command can't do what the team lead wants, say so and stop. If the session runs out of room first, `TECH-DESIGN-FROM-VAULT.md` says how to leave it.
