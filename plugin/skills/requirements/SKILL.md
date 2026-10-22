---
name: requirements
description: "Write each capability's functional requirements with acceptance criteria, no app named, kept as not decided yet. Offer it when someone asks what the business needs; start it only on a yes."
argument-hint: "[CAP-nnn, several, or none for every capability the strategy needs]"
---

# Requirements

Say what the business needs, once, before anyone decides which app does it. A requirement names no app: boundary and `/vela:allocate` come after. A requirements session never decides: what it writes is `assumption` (to the lead, "not decided yet") until a grill decides it.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format is `vela conventions "Requirements and allocation"`. When a command can't express what the lead wants, say so and stop.

## 1. Start

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`; write page prose through `house-voice` (read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` as a file).

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `requirements`. Read the Requirements row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The first time you say grill to the lead, say what it is in the words `vela terms grill` gives. If `04-solution-strategy.md` is not `decided`, say so: requirements written against it may be written again. Go on only if the lead says to, and record that as an override as `START.md` says.

Read the strategy, the goals, the constraints, `04a-capability-delta.md` and every capability page. List the capabilities the strategy needs: the lead's argument, or every one the strategy implies. For each that has no page, propose its name in the domain's words, such as "Refund a canceled booking", with its `change` (`new`, `extend`, `replace`, `narrow` or `retire`), and on the lead's yes write `capabilities/CAP-nnn-<slug>.md` as `vela conventions "Frontmatter"` says for a capability (`state: assumption`, `origin: proposed`), with opening prose saying what the business will be able to do with it, and a link from `04a-capability-delta.md`. Take the number from `vela next-id CAP`. Mark its capture at once, `→ keep: [[<page>|<ID>]] (assumption)`, with a `## Changes` row.

## 2. One capability at a time

For each capability, read back what the vault already says it must do, from the strategy, the goals, the constraints and the captures, as a numbered list of proposed requirements. Each one is a single thing the business needs, said without naming an app, a screen, a technology or a team: "A guest cancels a booking up to 48 hours before arrival and sees the refund as pending until it is paid or turned down", never "the Payments app exposes POST /refunds". Under each, propose its acceptance criteria: what someone checking the finished work would see, at a boundary the vault knows (an actor in the glossary, a flow, or an outside party).

Then take them one at a time, one question each, with your recommended answer, as a grill asks. Push on the edge cases the plain statement hides: what happens at the limits, when something is turned down or late, when the reader does it twice, when they are not allowed to. Write a requirement and its criteria only after the yes `START.md` defines. A line the lead can't answer becomes `vela add unknown --name "<name>" --capture ^cNN --blocks CAP-nnn.FRn`, in the same checkpoint. Ask the lead first, and pass who would actually know as `--ask`, as `MODES.md` says under "Unknowns".

**Fix each term once.** When the lead uses two words for one thing, such as "order" and "booking", ask once which is the vault's word, and use that word from then on in every requirement and criterion. Capture the choice as a term for `12-glossary.md`.

## 3. Write the confirmed requirements

Write each requirement with `vela add fr --capability CAP-nnn --name "<short name>" --need "<one paragraph, in the domain's words>" --criteria "<criterion>" --capture ^cNN`, one `--criteria` per criterion. It numbers the requirement, writes its heading, state and source, and marks the capture. What it writes, from a booking system:

```
### CAP-004.FR2 Refund a canceled booking

A guest who cancels in time gets their money back, and sees where the refund stands until it lands.

- **State:** assumption
- **Source:** [[2027-01-12-requirements-refunds#^c07]]

- A guest who cancels up to 48 hours before arrival sees a pending refund for the full price at once.
- A guest who cancels later sees the price they will not get back before they confirm.
  - Trace: UNK-012
```

A criterion is a sentence in plain words. When it rests on another item, an unknown or a contract, say that item by its name in the sentence and pass its ID in `--traces`, which writes the `- Trace:` line beneath it. The Trace line is not a criterion, so release criteria skip it. A requirement with more than about seven criteria is two requirements: propose the split before writing it.

When the lead drops a requirement, never strike its heading through: that breaks every link to it. Run `vela query refs <ID>`, take the requirement out of every row that names it (allocation, release, app page) in the same checkpoint, then delete the requirement, and keep the reason in the session record as a `→ drop` capture. Then run `vela render` and `vela check`, fix every error, and commit a checkpoint with `vela close stage --checkpoint --for-lead`.

Draft the paragraph each filed item owes now, as `START.md` says under "Draft the paragraph when the item is filed", and show it with the filed line.

## 4. Review, then finish

When the lead pauses after a capability, or every capability is done, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the requirements are written" and the capability pages written so far as its focus. Show the digest as REVIEW says and capture what the lead takes.

When every capability is done, or the lead stops and says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a grill on each capability decides the requirements, and a boundary session cuts the apps against them. Say the one line the lead types by the capability's name, such as "/vela:grill Refund a canceled booking", or `/vela:boundary`.

## Never

- Write an ID in a requirement's sentence or a criterion's: name the thing, and put the ID on a `- Trace:` line.
- Name an app, a container, a technology or a team in a requirement or its criteria. That is boundary's and allocate's work, then the team's design.
- Write `decided` or `fact`. Requirements state intent, and only a grill decides, unless the lead overrides it as `START.md` says.
- Write a non-functional requirement as a functional one. A speed, an availability or a security rule is a concern: write it as a capture for the concern page it belongs to.
