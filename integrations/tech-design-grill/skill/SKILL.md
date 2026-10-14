---
name: tech-design-grill
description: Use when designing a system after requirements are settled. Drives architecture, components, data model, API contracts, NFRs, and ADRs out of the room. Requires a complete requirements doc, or, in vault mode (`--vault <path> --app <APP-id>`), an app handed off from a vela initiative vault. Triggers include "tech design", "design the system", "how should we build this", "architecture session".
---

<what-to-do>

Interview the user relentlessly about every tech-design decision until shared understanding is reached. Walk the template in `TECH-DESIGN-FORMAT.md` section by section.

Ask one question at a time. Provide your recommended answer with each question. Wait for feedback before continuing.

Pure *how*. Assumes *what* is settled in `docs/requirements/<slug>.md` with `status: complete` — refuse to start otherwise. In vault mode the *what* is the app's handed-off pages in the vault instead; see **Vault mode** below.

If the codebase can answer a question (brownfield), explore the code instead of asking.

Trace every `FR-XXX` (in vault mode, every allocated requirement row, contract and epic criterion) to an owning component. Reject the design if any has no owner.

Capture answers inline in `docs/tech-design/<slug>.md` and `CONTEXT.md` as decisions crystallize. Do not batch.

Use `D-XXX` for explicit deferrals (logged in frontmatter `deferred[]`). Offer an ADR only when the decision is hard to reverse, surprising without context, and reflects a real trade-off.

</what-to-do>

<supporting-info>

## Inputs

- **Required prereq:** `docs/requirements/<slug>.md` with `status: complete`. If missing or in-progress, stop and tell the user to run `requirements-grill`. In vault mode, the prereq is the app page's `handed_off` field instead (see `PREREQ-CHECK.md`).
- **Auto-scan at start (silent):** existing `CONTEXT.md`, `docs/adr/*.md`, codebase if brownfield. See `PREREQ-CHECK.md`.
- **External context (any time):** accept and integrate.

## Outputs

- `docs/tech-design/<slug>.md` — primary. See `TECH-DESIGN-FORMAT.md`.
- `docs/adr/NNNN-<slug>-<topic>.md` — lazy. See `ADR-FORMAT.md`.
- `CONTEXT.md` at repo root — lazy. See `CONTEXT-FORMAT.md`.

## Vault mode

Given `--vault <path> --app <APP-id>`, the design is for one app of a vela initiative vault.

- `PREREQ-CHECK.md` checks the app is handed off, then you read `<vault>/.claude/skills/vela/references/TECH-DESIGN-FROM-VAULT.md` and follow it. It replaces the requirements-doc prereq, says what to read in the vault and in what order, and how to link back.
- The app's requirements are the rows of its `## Requirements allocated` table: its share of each functional requirement, and the contracts that carry the part that crosses to another app. Each row is a trace target, as `CAP-nnn.FRn@APP-<slug>`, alongside the contracts it provides and consumes and its epics' acceptance criteria.
- Never edit the vault. A gap or a disputed vault answer is an `OQ-XXX` with `challenges: <vault ID>`; tell the senior to raise it with `/vela:challenge`.
- Requirements are not written in the team's repository: there is no `docs/requirements/<slug>.md` in vault mode. If the design shows a requirement is missing, that is a challenge, not a draft.

## Boot sequence

1. Run `PREREQ-CHECK.md`. Refuse to start without a complete requirements doc, or, in vault mode, without the app's `handed_off:` in the vault.
2. **Promote glossary.** Read `Glossary` section of requirements doc. Offer to seed `CONTEXT.md` from it on first run.
3. **Trace requirements.** Read every `FR-XXX`. Build internal map: which component will own each FR. Reject the design if any FR has no owner.

## During the session

### One question at a time

Per `GRILL-LOOP.md`. Recommended answer included with every question.

### Explore code instead of asking

Brownfield: if a question can be answered by reading the codebase, read the codebase.

### Defer cleanly

`D-XXX` for explicit deferrals — log in frontmatter `deferred[]`. `OQ-XXX` from requirements either resolves here or stays open (carried forward).

### Offer ADRs sparingly

Only when **all three** hold:
- Hard to reverse
- Surprising without context
- Reflects a real trade-off (not just the obvious answer)

### Capture inline

Update the design doc + `CONTEXT.md` after each section. Do not batch.

## Review checkpoint

Before the completion gate, run `REVIEW-CHECKPOINT.md`: five fresh-context reviewers read the written design, one area each, and their checked findings become `OQ-XXX` entries the user disposes of. The interview cannot see what nobody in the room knows; the reviewers are there for the vendor limit, the license clause or the reset nobody mentioned.

## Completion gate

Run `NEG-AUDIT.md`. Focus:

- **Leaky Narrative** — Are component interfaces in domain language or tech?
- **Infected Core** — Does domain depend on infra anywhere?
- **God Class** — Any component owning too much?
- **Distributed Monolith** — Can components actually deploy / change independently?

Flip `status: complete` only if neg-audit passes and no review finding is left open: each was answered, deferred as a `D-XXX`, or ruled not applicable. A finding left as an open `OQ-XXX`, or a violation the user acknowledges instead of fixing, makes the status `complete-with-gaps`, with one `gaps[]` entry for each (see `FRONTMATTER-FORMAT.md`). Never write `complete` over an acknowledged gap.

## Hard rule

Do **not** open functional-requirement questions. If gaps surface, stop the session and tell the user to revisit `requirements-grill`. Don't paper over.

In vault mode, do not stop the session. Record the gap as an `OQ-XXX` with `challenges: <vault ID>` and the scenario that shows it, tell the senior to raise it with `/vela:challenge`, and carry on with the branches it does not touch.

## References

- `TECH-DESIGN-FORMAT.md`
- `ADR-FORMAT.md`
- `CONTEXT-FORMAT.md`
- `GRILL-LOOP.md`
- `PREREQ-CHECK.md`
- `FRONTMATTER-FORMAT.md`
- `NEG-AUDIT.md`
- `REVIEW-CHECKPOINT.md`

</supporting-info>
