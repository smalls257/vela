---
name: releases
description: Releases session for an initiative vault. After allocation, asks when anyone outside the team first uses or sees the result, then for each release which requirements must be there, which can wait and which only in part, helps choose the first thin path (the tracer) and what it leaves out, and writes the dated releases to 04b-releases.md line by line after the user's yes, at assumption for a later Grill. Names the requirements it leaves on no release. Use after allocate and before epics.
argument-hint: "[a release name or date, or none for the whole plan]"
disable-model-invocation: true
---

# Releases

Say when people get each part of what the initiative builds. Requirements say what the business needs and allocation says who carries it; neither says by when. A release is a date somebody outside the team will see, and the requirements, or only some of a requirement's checks, that must hold on that day. A releases session never decides: what it writes is an `assumption` until a Grill.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The format is `CONVENTIONS.md` under "Releases".

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `releases`. Read the Releases row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read `04b-releases.md`, every capability page's functional requirements with their acceptance criteria, `04a-capability-delta.md`, the `allocation` block (run `planner render` first), the goals and constraints for dates anybody already gave, the first thin path the boundary session recorded (a capture in its session record, which the flow pages back), and the open unknowns. If there are no functional requirements, say so and offer `/planner:requirements`. If requirements exist and none is allocated, offer `/planner:allocate`, and go on only if the user says to, recording that as an override as `START.md` says. A release that already exists is kept: change only the lines the user confirms.

## 2. One question at a time

Ask one question at a time, with your recommendation. Run it as a release-scope workshop, the way a business analyst would: date first, then must, should and later, requirement by requirement.

1. **The first release.** Ask when anyone outside the team first uses or sees this, and who they are. Take a date, and a name for the release that you propose yourself from the audience, such as "January board demo". Say where the date came from: a source, the user's words, or `(claude)` for a guess, which the user must replace before it is written.
2. **What must be there.** For each requirement not yet placed, in the order of the capability map, ask whether it must be there for that date, can wait, or only part of it has to be there. If part: list its criteria as AC1, AC2 and so on, and ask which of these checks must hold on that day. The rest goes on a later release.
3. **The first thin path (the tracer).** Ask this once the first release has its requirements, before the later releases. It runs in four short moves.
   - *Start from what boundary recorded.* If the boundary session recorded a first thin path (look in its session record and in the flow pages), open with it and ask whether it is still right. Ask the lead to name one only when none was recorded.
   - *Offer it.* Say once, in your own words, what it is and why it comes first: it is built first and kept, so the contracts between the apps get proved early and each team's first story is its steps of it (`CONVENTIONS.md` defines it under "Releases"). Read the flows from `06-runtime/flows/` and show a short table in plain words, with the flow's name rather than its ID: the flow, the apps it crosses, the new contracts it crosses (an outside party is not counted). Recommend the flow that proves the most of the system, the one crossing the most apps and new contracts. Break a tie by what the first release's audience sees first. A tracer is often several flows in the order they run. For example, if two flows each cross three apps and three new contracts, recommend the one the first audience sees first, and put the flow that gets a person to it before it. If no flow page exists yet for the path the user wants, take it in plain words, say a boundary session can draw it, and write no link (the file says "no flow page yet").
   - *Thin it.* For each requirement the tracer touches, ask whether it needs all of its checks or only some, such as AC1 and AC2. The checks left out go on a later release through the Delivers table below.
   - *What it leaves out.* Ask whether anything is held back from this path because it is not ready, such as a review or an approval. Each answer is a line under Not in the tracer. Keeping the whole requirement in the tracer is a fine answer: write it as given and record in the session that the lead kept it all. Nothing here holds the session back; a lead who wants no tracer says so, and that is written as `**Tracer:** none, <reason>`.
4. **What comes next.** Ask what comes next, and when. Repeat steps 1 and 2 for the next release. Go on until every requirement at `assumption` or later is on a release or the user says "later, no date" for it.
5. **What the first date depends on.** Ask whether anything on the first date depends on something not yet agreed. Each answer becomes an unknown, with an owner handle, an ask-by date and `**Blocks:**` linking the release's heading. Ask the lead first, and write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

Label every line with what it rests on: a source, the user's words, or `(claude)`. Write a line only after the yes `START.md` defines; read the release back in groups of about five lines. A requirement the user will not date stays out of the file, and you tell them that the check will keep listing it as undated until it has a release.

## 3. Write the confirmed releases

On `04b-releases.md`, one section per release, in the order they ship:

```
## Release one: January board demo

- **Target:** 2027-01-15
- **State:** assumption
- **Tracer:** [[FLO-001-switch-heron-on|FLO-001]], [[FLO-002-get-morning-digest|FLO-002]], a person switches Heron on and gets the 7:30 digest from calendar entries only
- **Not in the tracer:** Teams transcripts (CAP-001.FR1): waits on the CISO review of 4 December and the tenant admins' approval

| Delivers | Criteria | Note |
|---|---|---|
| [[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]] | AC1, AC2 | AC3 in release two |
```

- **Target** is a real `YYYY-MM-DD` date. A date the user has not given is not written; the release waits as a question. A bad date fails E344.
- **Tracer** is on release one only. It takes one or more flow links in the order they run, then a comma and the thin version in plain words. A path with no flow page yet is plain words and no link (`**Tracer:** a person gets the 7:30 digest from their calendar, no flow page yet`); a deliberate choice of none is `**Tracer:** none, <reason>`. **Not in the tracer** is one line per piece left out: what it is, its ID in parentheses if it has one, and the reason. The thinning itself is the Delivers table: the row's Criteria says which checks hold, and the Note says where the rest goes. Later releases say what they add through their own Delivers tables.
- **Delivers** links the requirement's heading. **Criteria** is `all`, or the criteria that hold on that day, numbered in the order the bullets appear under the requirement. **Note** says in a few words where the rest goes, such as "AC3 in release two", or is left empty.
- A requirement may stand on several releases, each with different criteria. A requirement the user placed on no release is not written at all.
- Replace the page's "No release is planned yet" line with one opening paragraph: how many releases, the first date and what is undated. Close rewrites it in the house voice.
- Each release written gets a capture marked at once, `→ keep: [[04b-releases#<release heading>|<release name>]] (assumption)`, and a `## Changes` row in the session record, `| releases | - | assumption | [[<id>#^cNN]] |`. A release has no ID of its own, so the row names the page, and the capture names the release.

Then run `planner render` and `planner check`, fix every error (E340 and E341 mean a link or a criterion number is wrong), tell the user which requirements are still on no release, by their plain names (that is what the W343 lines list; do not say the code), and commit a checkpoint.

## 4. Review, then finish

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the releases are written" and `04b-releases.md` as its focus. Show the digest as REVIEW says and capture what the lead takes.

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on `releases` decides them, and `/planner:epics` cuts each team's epics against them.

## Never

- Write `decided`. Only a Grill decides, unless the user overrides it as `START.md` says.
- Invent a date, or turn a hope into a target. A date has a source or the user's word.
- Change a requirement or its criteria to fit a release. A release that needs a check split differently is a question for `/planner:requirements`, never a quiet rewrite.
- Make a release for an epic. An epic never needs a release of its own.
