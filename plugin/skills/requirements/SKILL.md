---
name: requirements
description: Requirements session for an initiative vault, the first of two levels. Once the strategy is decided, it writes each capability's functional requirements, what the business needs with no app named, with their acceptance criteria, line by line after the user's yes, at assumption for a later Grill. It creates a capability page the strategy needs and the vault lacks. Use after the strategy grill and before boundary, so boundary can test each cut against the requirements.
argument-hint: "[CAP-nnn, several, or none for every capability the strategy needs]"
disable-model-invocation: true
---

# Requirements

Say what the business needs, once, before anyone decides which app does it. A requirement here names no app: boundary cuts the work into apps afterwards, and `/planner:allocate` divides each requirement among them. A requirements session never decides: what it writes is an `assumption` until a Grill.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The format is `CONVENTIONS.md` under "Requirements and allocation" and "Fact bullets" (the functional requirement row).

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `requirements`. Read the Requirements row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. If `04-solution-strategy.md` is not `decided`, say so: requirements written against an undecided strategy may be written again. Go on only if the user says to, and record that as an override as `START.md` says.

Read the strategy, the goals, the constraints, `04a-capability-delta.md` and every capability page. List the capabilities the strategy needs: the user's argument, or every one the strategy implies. For each that has no page, propose its name in the domain's words, such as "Paper-trade a stock", with its `change` (`new`, `extend`, `replace`, `narrow` or `retire`), and on the user's yes write `capabilities/CAP-nnn-<slug>.md`: `id`, `type: capability`, `title`, `state: assumption`, `owner`, `authored: authored`, `origin: proposed`, its `change`, opening prose saying what the business can do with it, and a link from `04a-capability-delta.md`. Take the next free number as `CONVENTIONS.md` says under "IDs".

## 2. One capability at a time

For each capability, read back what the vault already says it must do, from the strategy, the goals, the constraints and the captures, as a numbered list of proposed requirements. Each one is a single thing the business needs, said without naming an app, a screen, a technology or a team: "A reader places a market order for whole shares of a stock on the list, and sees it pending until it fills or is turned down", never "Coach exposes POST /orders". Under each, propose its acceptance criteria: what someone checking the finished work would see, stated at a boundary the vault knows (an actor in the glossary, a flow, or an outside party).

Then take them one at a time, one question each, with your recommended answer, as a Grill asks. Push on the edge cases the plain statement hides: what happens at the limits, when something is turned down or late, when the reader does it twice, when they are not allowed to. Write nothing until the user has said yes to that requirement and its criteria. A line the user cannot answer becomes an unknown on `11-unknowns-and-risks.md` with an owner handle, an ask-by date and `**Blocks:**` linking the requirement's heading, written in the same checkpoint. Ask the lead first, as `MODES.md` says under "Unknowns". When the owner is not the person who would actually know, ask once: "Who would actually know this? If that is not the owner, give me a name or a role, like outside counsel." Write the answer as `**Ask:** @handle` or `**Ask:** outside counsel`, and leave the line out when the owner holds the answer.

## 3. Write the confirmed requirements

On the capability page, under `## Functional requirements`:

```
### CAP-nnn.FRn <short name, at most six words>

<one paragraph: what the business needs, in the domain's words>

- **State:** assumption
- **Source:** [[<session id>#^cNN]]

- <acceptance criterion>
  - Trace: <ID, ID>
- <acceptance criterion>
```

A criterion is a sentence in plain words. When it rests on another item, an unknown or a contract, say that item by its name in the sentence and put its ID on the indented `- Trace:` line beneath it; leave the line out when it cites nothing. The Trace line is not a criterion, so release criteria (AC1, AC2) skip it. A requirement with more than about seven criteria is two requirements: propose the split before writing it.

Number new requirements after the highest on the page; numbers are never reused. When the lead drops a requirement, never strike its heading through: that breaks every link to it and fails the check on each page that names it. Run `planner query refs <ID>`, take the requirement out of every row that names it (allocation, release, app page) in the same checkpoint, then delete the requirement, and keep the reason in the session record as a `→ drop` capture. Each written requirement gets a capture marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`, and a `## Changes` row, as Boundary does for its pages. Then run `planner render` and `planner check`, fix every error, and commit a checkpoint.

## 4. Review, then finish

When the lead pauses after a capability, or when every capability is done, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the requirements are written" and the capability pages written so far as its focus. Show the digest as REVIEW section 5 says, once in the session and at most three questions, and capture what the lead takes.

When every capability is done, or the user stops, run `git status` and confirm nothing under `.inbox/` is staged. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on each capability decides the requirements, and a Boundary session cuts the apps against them; say the one line the lead types, `/planner:grill CAP-nnn` or `/planner:boundary`.

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Write an ID in a requirement's sentence or a criterion's: name the thing, and put the ID on a `- Trace:` line.
- Name an app, a container, a technology or a team in a requirement or its criteria. That is boundary's and allocate's work, then the team's design.
- Write `decided` or `fact`. Requirements state intent, and only a Grill decides, unless the user overrides it as `START.md` says.
- Write a non-functional requirement as a functional one. A speed, an availability or a security rule is a concern: write it as a capture for the concern page it belongs to.
