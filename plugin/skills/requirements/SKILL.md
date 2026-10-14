---
name: requirements
description: Write each capability's functional requirements, with acceptance criteria and no app named, after the strategy is decided. Use after the strategy grill and before boundary.
argument-hint: "[CAP-nnn, several, or none for every capability the strategy needs]"
disable-model-invocation: true
---

# Requirements

Say what the business needs, once, before anyone decides which app does it. A requirement here names no app: boundary cuts the work into apps afterwards, and `/vela:allocate` divides each requirement among them. A requirements session never decides: what it writes is an `assumption` until a Grill.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format is `vela conventions "Requirements and allocation"` and `vela conventions "Fact bullets"` (the functional requirement row).

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `requirements`. Read the Requirements row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. If `04-solution-strategy.md` is not `decided`, say so: requirements written against an undecided strategy may be written again. Go on only if the user says to, and record that as an override as `START.md` says.

Read the strategy, the goals, the constraints, `04a-capability-delta.md` and every capability page. List the capabilities the strategy needs: the user's argument, or every one the strategy implies. For each that has no page, propose its name in the domain's words, such as "Refund a canceled booking", with its `change` (`new`, `extend`, `replace`, `narrow` or `retire`), and on the user's yes write `capabilities/CAP-nnn-<slug>.md` as `vela conventions "Frontmatter"` says for a capability (`state: assumption`, `origin: proposed`), with opening prose saying what the business can do with it, and a link from `04a-capability-delta.md`. Take the number from `vela next-id CAP`.

## 2. One capability at a time

For each capability, read back what the vault already says it must do, from the strategy, the goals, the constraints and the captures, as a numbered list of proposed requirements. Each one is a single thing the business needs, said without naming an app, a screen, a technology or a team: "A guest cancels a booking up to 48 hours before arrival and sees the refund as pending until it is paid or turned down", never "the Payments app exposes POST /refunds". Under each, propose its acceptance criteria: what someone checking the finished work would see, stated at a boundary the vault knows (an actor in the glossary, a flow, or an outside party).

Then take them one at a time, one question each, with your recommended answer, as a Grill asks. Push on the edge cases the plain statement hides: what happens at the limits, when something is turned down or late, when the reader does it twice, when they are not allowed to. Write a requirement and its criteria only after the yes `START.md` defines. A line the user cannot answer becomes an unknown on `11-unknowns-and-risks.md` with an owner handle, an ask-by date and `**Blocks:**` linking the requirement's heading, written in the same checkpoint. Ask the lead first, and write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

**Fix each term once.** When the lead uses two words for one thing, such as "order" and "booking", ask once which is the vault's word, and use that word from then on in every requirement and criterion. Capture the choice as a term for `12-glossary.md`, so the glossary owns the language.

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

A filled-in example, from a booking system:

```
### CAP-004.FR2 Refund a canceled booking

A guest who cancels in time gets their money back, and sees where the refund stands until it lands.

- **State:** assumption
- **Source:** [[2027-01-12-requirements-refunds#^c07]]

- A guest who cancels up to 48 hours before arrival sees a pending refund for the full price at once.
- A guest who cancels later sees the price they will not get back before they confirm.
  - Trace: UNK-012
```

A criterion is a sentence in plain words. When it rests on another item, an unknown or a contract, say that item by its name in the sentence and put its ID on the indented `- Trace:` line beneath it; leave the line out when it cites nothing. The Trace line is not a criterion, so release criteria (AC1, AC2) skip it. A requirement with more than about seven criteria is two requirements: propose the split before writing it.

Number new requirements after the highest on the page; numbers are never reused. When the lead drops a requirement, never strike its heading through: that breaks every link to it and fails the check on each page that names it. Run `vela query refs <ID>`, take the requirement out of every row that names it (allocation, release, app page) in the same checkpoint, then delete the requirement, and keep the reason in the session record as a `→ drop` capture. Each written requirement gets a capture marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`, and a `## Changes` row, as Boundary does for its pages. Then run `vela render` and `vela check`, fix every error, and commit a checkpoint.

## 4. Review, then finish

When the lead pauses after a capability, or when every capability is done, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the requirements are written" and the capability pages written so far as its focus. Show the digest as REVIEW says and capture what the lead takes.

When every capability is done, or the user stops, and the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on each capability decides the requirements, and a Boundary session cuts the apps against them; say the one line the lead types, `/vela:grill CAP-nnn` or `/vela:boundary`.

## Never

- Write an ID in a requirement's sentence or a criterion's: name the thing, and put the ID on a `- Trace:` line.
- Name an app, a container, a technology or a team in a requirement or its criteria. That is boundary's and allocate's work, then the team's design.
- Write `decided` or `fact`. Requirements state intent, and only a Grill decides, unless the user overrides it as `START.md` says.
- Write a non-functional requirement as a functional one. A speed, an availability or a security rule is a concern: write it as a capture for the concern page it belongs to.
