---
name: releases
description: Cut the plan into slices, the tracer first, each a journey proven end to end; date the releases as milestones that point at slices, say which requirements must be there and which can wait, and write it all at assumption. Use after allocate and before epics.
argument-hint: "[a release name or date, or none for the whole plan]"
disable-model-invocation: true
---

# Releases

Say in what order the initiative gets built, and when people see it. Requirements say what the business needs and allocation says who carries it; neither says by when. A slice is the unit of done: one journey, proven end to end, switched on when that journey passes. A release is a milestone: a date somebody outside the team will see, the slices that should be on by then, and the requirements, or only some of a requirement's checks, that must hold on that day. Nothing waits for a release. A releases session never decides: what it writes is an `assumption` until a Grill, and a slice it writes has no status until a Grill plans it.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The format is `vela conventions "Releases"` and `vela conventions "Slices"`.

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `releases`. Read the Releases row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read `04b-releases.md`, the slice pages in `slices/`, every capability page's functional requirements with their acceptance criteria, `04a-capability-delta.md`, the `allocation` block (run `vela render` first), the goals and constraints for dates anybody already gave, the first thin path the boundary session recorded (a capture in its session record, which the flow pages back), and the open unknowns. If there are no functional requirements, say so and offer `/vela:requirements`. If requirements exist and none is allocated, offer `/vela:allocate`, and go on only if the user says to, recording that as an override as `START.md` says. A release that already exists is kept: change only the lines the user confirms.

## 2. One question at a time

Ask one question at a time, with your recommendation. Run it as a release-scope workshop, the way a business analyst would: date first, then must, should and later, requirement by requirement.

1. **The first release.** Ask when anyone outside the team first uses or sees this, and who they are. Take a date, and a name for the release that you propose yourself from the audience, such as "January board demo". Say where the date came from: a source, the user's words, or `(claude)` for a guess, which the user must replace before it is written.
2. **What must be there.** For each requirement not yet placed, in the order of the capability map, ask whether it must be there for that date, can wait, or only part of it has to be there. If part: list its criteria as AC1, AC2 and so on, and ask which of these checks must hold on that day. The rest goes on a later release.
3. **The first thin path (the tracer).** Ask this once the first release has its requirements, before the later releases. It runs in five short moves, and it becomes the first slice.
   - *Start from what boundary recorded.* If the boundary session recorded a first thin path (look in its session record and in the flow pages), open with it and ask whether it is still right. Ask the lead to name one only when none was recorded.
   - *Offer it.* Say once, in your own words, what it is and why it comes first: it is built first and kept, so the contracts between the apps get proved early and each team's first story is its steps of it (`vela conventions "Slices"` defines it). Read the flows from `06-runtime/flows/` and show a short table in plain words, with the flow's name rather than its ID: the flow, the apps it crosses, the new contracts it crosses (an outside party is not counted). Recommend the flow that proves the most of the system, the one crossing the most apps and new contracts. Break a tie by what the first release's audience sees first. A tracer is often several flows in the order they run. For example, if two flows each cross three apps and three new contracts, recommend the one the first audience sees first, and put the flow that gets a person to it before it. If no flow page exists yet for the path the user wants, take it in plain words, say a boundary session can draw it, and write no link (the file says "no flow page yet").
   - *Thin it.* For each requirement the tracer touches, ask whether it needs all of its checks or only some, such as AC1 and AC2. The checks left out go on a later release through the Delivers table below.
   - *What it leaves out.* Ask whether anything is held back from this path because it is not ready, such as a review or an approval. Each answer is a line under the slice's Not in this slice. Keeping the whole requirement in the tracer is a fine answer: write it as given and record in the session that the lead kept it all. Nothing here holds the session back; a lead who wants no tracer says so, and that is written as `**Flows:** none, <reason>`.
   - *How it ships, and what done is.* Ask how it goes live switched off (a flag, a switch, who holds it) and what done looks like from the side of the person who uses it. "Not decided yet" is a fine answer; write it so.
   The tracer is the slice page SLC-001.
4. **The next slices.** Ask which journey comes next, and what it comes after. Offer each remaining flow, or a short group of flows that make one journey, as a slice of its own, with what it comes after: the tracer, or another slice. Several slices may follow the tracer side by side. The lead decides each cut; you recommend. Steer toward thin journeys a person can watch working, never a layer.
5. **What comes next, and when.** Ask what the next date is, and which slices should be on by then. Repeat steps 1 and 2 for the next release. Go on until every requirement at `assumption` or later is on a release or the user says "later, no date" for it.
6. **What the first date depends on.** Ask whether anything on the first date depends on something not yet agreed. Each answer becomes an unknown, with an owner handle, an ask-by date and `**Blocks:**` linking the release's heading. Ask the lead first, and write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

Label every line with what it rests on: a source, the user's words, or `(claude)`. Write a line only after the yes `START.md` defines; read the release back in groups of about five lines. A requirement the user will not date stays out of the file, and you tell them that the check will keep listing it as undated until it has a release.

## 3. Write the confirmed slices and releases

Each slice is a page, `slices/SLC-nnn-<slug>.md`, numbered with `vela next-id SLC`, the tracer SLC-001. Write it in the form `vela conventions "Slices"` gives: the title says the journey in the user's words, an opening of two or three sentences, then `**Flows:**`, `**After:**` (not on the tracer), `**Ships switched off:**`, `**Done when:**`, `**Owner:**` and `**Milestone:**` when a release lists it, then `## Not in this slice` and `## History` with a dated line saying what it was written from. Leave `**Status:**` out: a Grill sets `planned`. Write no joins: they are read from the flows' steps, so a join missing from a slice means a step missing from a flow, and boundary is where it gets drawn.

When the lead says a slice has moved to `building`, ask when its journey should run, and write the date they give as `- **Journey due:** YYYY-MM-DD` under Owner. Write no date nobody gave: without one, nothing reminds anyone the journey is late.

On `04b-releases.md`, one section per release, in the order they ship:

```
## Release one: January board demo

- **Target:** 2027-01-15
- **State:** assumption
- **Slices:** SLC-001, SLC-002

| Delivers | Criteria | Note |
|---|---|---|
| [[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]] | AC1, AC2 | AC3 in release two |
```

- **Target** is a real `YYYY-MM-DD` date. A date the user has not given is not written; the release waits as a question. A bad date fails E344.
- **Slices** names, by ID, the slices that should be on by the date. A release that points at no slice yet leaves it out. The thinning itself is the Delivers table: the row's Criteria says which checks hold, and the Note says where the rest goes.
- A vault that already names its tracer on release one (`**Tracer:**`, `**Not in the tracer:**`) or a later release's `**Flows:**` keeps working; offer to move each to a slice page, and replace the bullets with `**Slices:**` once the lead agrees.
- **Delivers** links the requirement's heading. **Criteria** is `all`, or the criteria that hold on that day, numbered in the order the bullets appear under the requirement. **Note** says in a few words where the rest goes, such as "AC3 in release two", or is left empty.
- A requirement may stand on several releases, each with different criteria. A requirement the user placed on no release is not written at all.
- Replace the page's "No release is planned yet" line with one opening paragraph: how many releases, the first date and what is undated. Close rewrites it in the house voice.
- Each release written gets a capture marked at once, `→ keep: [[04b-releases#<release heading>|<release name>]] (assumption)`, and a `## Changes` row in the session record, `| releases | - | assumption | [[<id>#^cNN]] |`. A release has no ID of its own, so the row names the page, and the capture names the release. Each slice page written gets one too, `→ keep: [[SLC-nnn-<slug>]] (new)`, and a row `| SLC-nnn | - | new | [[<id>#^cNN]] |`.

Then run `vela render` and `vela check`, fix every error (E340 and E341 mean a link or a criterion number is wrong, E394 a circle of After), fix what W392, W393 and W347 say about a slice, tell the user which requirements are still on no release, by their plain names (that is what the W343 lines list; do not say the code), and commit a checkpoint.

## 4. Review, then finish

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the releases are written" and `04b-releases.md` as its focus. Show the digest as REVIEW says and capture what the lead takes.

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a Grill on `releases` decides them, and `/vela:epics` cuts each team's epics against them.

## Never

- Write `decided`. Only a Grill decides, unless the user overrides it as `START.md` says.
- Invent a date, or turn a hope into a target. A date has a source or the user's word.
- Change a requirement or its criteria to fit a release. A release that needs a check split differently is a question for `/vela:requirements`, never a quiet rewrite.
- Make a release for an epic. An epic never needs a release of its own.
