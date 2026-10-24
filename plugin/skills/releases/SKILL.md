---
name: releases
description: "Cut the plan into slices, tracer first, and date the releases, saved as not decided yet. Offer it when someone asks what ships when or in what order; start it only on a yes."
argument-hint: "[a release name or date, or none for the whole plan]"
---

# Releases

Say in what order the plan gets built, and when people see it. A release is a milestone: a date somebody outside the team will see, the slices that should be on by then, and the requirements, or only some of their checks, that must hold that day. Nothing waits for a release. What this session writes is "not decided yet" until a grill decides it, and a slice has no status until a grill plans it.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `releases`, and read the Releases row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The first time you say slice, tracer or grill, say what it is from `vela terms`. Page formats: `vela conventions "Releases"` and `vela conventions "Slices"`.

## 1. Start from what's there

Run `vela releases brief --for-lead` and tell the lead what it says. With no requirements, offer `/vela:requirements`; with none allocated, offer `/vela:allocate`; go on only as an override. Read the goals and constraints for dates anybody already gave. A release that already exists is kept: change only the lines the lead confirms.

## 2. One question at a time

Run it as a release-scope workshop, the way a business analyst would: date first, then must, should and later, requirement by requirement. One question at a time, each with your recommendation.

1. **The first release.** Ask when anyone outside the team first uses or sees this, and who they are. Take a date, and propose a name from the audience, such as "March dock pilot". Say where the date came from: a source, the lead's words, or a guess of yours, which the lead must replace before it is written.
2. **What must be there.** For each requirement not yet placed, in capability-map order, ask whether it must be there for that date, can wait, or only part of it must. For a part, read its criteria back in their own words and ask which must hold on that day; the rest goes on a later release.
3. **The first thin path (the tracer).** Once the first release has its requirements, before the later ones. It becomes the first slice.
   - *Start from what Boundary recorded.* If the brief names the first thin path the boundary session recorded, open with it and ask whether it is still right. Ask the lead to name one only when none was recorded.
   - *Offer it.* Say once why it comes first: it is built first and kept, so the contracts between the apps are proved early and each team's first story is its steps of it. Run `vela releases tracer-candidates --for-lead`, show its ranking as a short table (the flow, the apps it crosses, the new contracts it crosses), and recommend the top one, the one that proves the most. Break a tie by what the first audience sees first: if two flows each cross three apps and three new contracts, recommend the one the first audience sees first, and put the flow that gets a person to it before it. With no flow page yet for the path the lead wants, take it in plain words, write no link (the slice page says "no flow page yet"), and say a boundary session can draw it.
   - *Thin it.* For each requirement the tracer touches, ask whether it needs all its checks or only some, said by their words.
   - *What it leaves out.* Ask what is held back because it isn't ready, such as a review or an approval; each answer goes under the slice's Not in this slice. Keeping the whole requirement is a fine answer: write it as given and record that the lead kept it all. A lead who wants no tracer says so, written as `**Flows:** none, <reason>`.
   - *How it ships, and what done is.* Ask how it goes live switched off (a flag, a switch, who holds it) and what done looks like to the person who uses it. "Not decided yet" is a fine answer.
   The tracer is the slice page SLC-001.
4. **The next slices.** Ask which journey comes next, and after what. Offer each remaining flow, or a short group that makes one journey, as a slice of its own; several may follow the tracer side by side. Recommend thin journeys a person can watch working, never a layer; the lead decides each cut.
5. **What comes next, and when.** Ask the next date and which slices should be on by then, and repeat 1 and 2 until every requirement at `assumption` or later is on a release or the lead says "later, no date".
6. **What the first date depends on.** Ask whether anything on it depends on something not yet agreed. Each answer is an unknown that blocks the release's heading; ask the lead first, and who would actually know (`MODES.md`, "Unknowns").

Label every line with what it rests on: a source, the lead's words, or `(claude)`. Read each release back by name, in groups of about five lines, and write only what has a yes. A requirement the lead won't date stays off the page; tell them the check will keep listing it as undated.

## 3. Write the confirmed slices and releases

Write each slice with `vela add slice --title "<the journey, in the lead's words>" --for-lead` with the rest of its flags (`--help` gives the flags; no `--after` on the tracer). Then add its opening of two or three sentences and the lines under `## Not in this slice`. A slice with no flow page, or a tracer with no flows, is one `add slice` can't take: write it by hand in the form `vela conventions "Slices"` gives, and tell the lead. When a slice moves to `building`, ask when its journey should run and write the date they give as `**Journey due:**`. When you've added slices or changed their After, run `vela check-slice --changed --for-lead` and tell the lead, in your words, which slices it checked and why.

Write `04b-releases.md` by hand (no command writes a release yet), one section per release in the order they ship:

```
## Release one: March dock pilot

- **Target:** 2027-01-15
- **State:** assumption
- **Slices:** SLC-001, SLC-002

| Delivers | Criteria | Note |
|---|---|---|
| [[CAP-002-unlock-a-bike#CAP-002.FR2 Unlock with the app\|CAP-002.FR2]] | AC1, AC2 | AC3 in release two |
```

The Target is a date the lead gave (none given, the release waits as a question); Slices names those that should be on by then; Criteria is `all` or the numbers that hold, and the Note says where the rest goes (`vela conventions "Releases"`). Replace the page's "No release is planned yet" line with an opening: how many releases, the first date, and what is undated. Each release gets a capture marked at once, `→ keep: [[04b-releases#<release heading>|<release name>]] (assumption)`, and a `## Changes` row in the session's notes, `| releases | - | assumption | [[<id>#^cNN]] |`.

Then run `vela render` and `vela check`, fix what they say, tell the lead which requirements are still on no release, by name, and run `vela close stage --checkpoint --for-lead`. Draft the paragraph each filed item owes, as `START.md` says under "Draft the paragraph when the item is filed".

## 4. Review, then finish

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md` "after the releases are written", with `04b-releases.md` as its focus, and capture what the lead takes. When the lead is done, close as `START.md` says under "Closing a session". Then a grill decides the releases, and `/vela:epics` cuts each team's epics against them.

## Never

- Invent a date, or turn a hope into a target.
- Change a requirement or its criteria to fit a release. A check that needs splitting differently is a question for `/vela:requirements`.
- Make a release for an epic.
