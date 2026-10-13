---
name: releases
description: Releases session for an initiative vault. After allocation, asks when anyone outside the team first uses or sees the result, then for each release which requirements must be there, which can wait and which only in part, and writes the dated releases to 04b-releases.md line by line after the user's yes, at assumption for a later Grill. Names the requirements it leaves on no release. Use after allocate and before epics.
argument-hint: "[a release name or date, or none for the whole plan]"
disable-model-invocation: true
---

# Releases

Say when people get each part of what the initiative builds. Requirements say what the business needs and allocation says who carries it; neither says by when. A release is a date somebody outside the team will see, and the requirements, or only some of a requirement's checks, that must hold on that day. A releases session never decides: what it writes is an `assumption` until a Grill.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The format is `CONVENTIONS.md` under "Releases".

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `releases`. Read the Releases row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read `04b-releases.md`, every capability page's functional requirements with their acceptance criteria, `04a-capability-delta.md`, the `allocation` block (run `planner render` first), the goals and constraints for dates anybody already gave, and the open unknowns. If there are no functional requirements, say so and offer `/planner:requirements`. If requirements exist and none is allocated, offer `/planner:allocate`, and go on only if the user says to, recording that as an override as `START.md` says. A release that already exists is kept: change only the lines the user confirms.

## 2. One question at a time

Ask one question at a time, with your recommendation. Run it as a release-scope workshop, the way a business analyst would: date first, then must, should and later, requirement by requirement.

1. **The first release.** "What is the first date anyone outside the team uses or sees this, and who are they?" Take a name and a date. Propose the name from the audience, such as "January board demo", and say where the date came from: a source, the user's words, or `(claude)` for a guess, which the user must replace before it is written.
2. **What must be there.** For each requirement that is not yet placed, in the order of the capability map: "For that date, take <requirement>. Must it be there, can it wait, or does only part have to be there?" If part: list its criteria as AC1, AC2 and so on, and ask "Which of these checks must hold on that day?" The rest goes on a later release.
3. **What comes next.** "What comes next, and when?" Repeat steps 1 and 2 for the next release. Go on until every requirement at `assumption` or later is on a release or the user says "later, no date" for it.
4. **What the first date depends on.** "Does anything on the first date depend on something not yet agreed?" Each answer becomes an unknown, with an owner handle, an ask-by date and `**Blocks:**` linking the release's heading. When the owner is not who would actually know, ask "Who would actually know this? If that is not the owner, give me a name or a role, like outside counsel." and write it as `**Ask:**`. Ask the lead first, as `MODES.md` says under "Unknowns".

Label every line with what it rests on: a source, the user's words, or `(claude)`. Write nothing until the user has said yes to that line. Silence, or "ok" with nothing else, does not count: ask again. A requirement the user will not date stays out of the file, and you tell them that the check will keep listing it as undated until it has a release.

## 3. Write the confirmed releases

On `04b-releases.md`, one section per release, in the order they ship:

```
## Release one: January board demo

- **Target:** 2027-01-15
- **State:** assumption

| Delivers | Criteria | Note |
|---|---|---|
| [[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]] | AC1, AC2 | AC3 in release two |
```

- **Target** is a real `YYYY-MM-DD` date. A date the user has not given is not written; the release waits as a question. A bad date fails E344.
- **Delivers** links the requirement's heading. **Criteria** is `all`, or the criteria that hold on that day, numbered in the order the bullets appear under the requirement. **Note** says in a few words where the rest goes, such as "AC3 in release two", or is left empty.
- A requirement may stand on several releases, each with different criteria. A requirement the user placed on no release is not written at all.
- Replace the page's "No release is planned yet" line with one opening paragraph: how many releases, the first date and what is undated. Close rewrites it in the house voice.
- Each release written gets a capture marked at once, `→ keep: [[04b-releases#<release heading>|<release name>]] (assumption)`, and a `## Changes` row in the session record, `| releases | - | assumption | [[<id>#^cNN]] |`. A release has no ID of its own, so the row names the page, and the capture names the release.

Then run `planner render` and `planner check`, fix every error (E340 and E341 mean a link or a criterion number is wrong), tell the user which requirements are still on no release, by their plain names (that is what the W343 lines list; do not say the code), and commit a checkpoint.

## 4. Review, then finish

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the releases are written" and `04b-releases.md` as its focus. Show the digest as REVIEW section 5 says, once and at most three questions, and capture what the lead takes.

Run `git status` and confirm nothing under `.inbox/` is staged. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on `releases` decides them, and `/planner:epics` cuts each team's epics against them.

## Never

These are the defaults. The user may override any of them, as `START.md` says, and the override is recorded.

- Write `decided`. Only a Grill decides, unless the user overrides it as `START.md` says.
- Invent a date, or turn a hope into a target. A date has a source or the user's word.
- Change a requirement or its criteria to fit a release. A release that needs a check split differently is a question for `/planner:requirements`, never a quiet rewrite.
- Make a release for an epic. An epic never needs a release of its own.
