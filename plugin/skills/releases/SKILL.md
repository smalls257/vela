---
name: releases
description: Cut the plan into slices, the tracer first, each one journey proven end to end. Date the releases that point at them, say which requirements must be there and which can wait, and save it all as not decided yet. Use after allocate, before epics.
argument-hint: "[a release name or date, or none for the whole plan]"
disable-model-invocation: true
---

# Releases

Say in what order the plan gets built, and when people see it. A release is a milestone: a date somebody outside the team will see, the slices that should be on by then, and the requirements, or only some of their checks, that must hold that day. Nothing waits for a release. What this session writes is `assumption` (to the lead, "not decided yet") until a grill decides it, and a slice has no status until a grill plans it.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The release format is `vela conventions "Releases"`. Say a command's `--for-lead` lines to the lead in your words, and reason over its `--json`. When a command can't express what the lead wants, say so and stop.

## 1. Start

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`; write page prose through `house-voice` (read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` as a file).

Then, before any other command, run `vela freshness --for-lead`. If it exits 3, this copy is behind the shared plan: stop, say what it printed in your words and offer to bring it up to date, and run `vela session start --mode releases` once they agree. A stale copy is how a releases session says nothing is allocated when the allocation is already on main. If it fails, say in one plain sentence that you couldn't check, and go on; never pass the tool's own error text to the lead.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `releases`. Read the Releases row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The first time you say slice, tracer or grill to the lead, say what it is in the words `vela terms` gives.

Run `vela releases brief --for-lead` and tell the lead, in your words, what it says: the releases, the slices in order, the requirements and which are on no release, the first thin path the boundary session recorded, and what is missing. When it says there are no requirements, offer `/vela:requirements`. When it says none is allocated, offer `/vela:allocate`, and go on only if the lead says to, recording that as an override as `START.md` says. Read the goals and constraints for dates anybody already gave. A release that already exists is kept: change only the lines the lead confirms.

## 2. One question at a time

Ask one question at a time, with your recommendation. Run it as a release-scope workshop, the way a business analyst would: date first, then must, should and later, requirement by requirement.

1. **The first release.** Ask when anyone outside the team first uses or sees this, and who they are. Take a date, and a name for the release that you propose yourself from the audience, such as "March dock pilot". Say where the date came from: a source, the lead's words, or `(claude)` for a guess, which the lead must replace before it is written.
2. **What must be there.** For each requirement not yet placed, in the order of the capability map, ask whether it must be there for that date, can wait, or only part of it has to be there. If part: read its criteria back in their own words from the capability page, and ask which of these checks must hold on that day. The rest goes on a later release.
3. **The first thin path (the tracer).** Ask this once the first release has its requirements, before the later releases. It runs in five short moves, and it becomes the first slice.
   - *Start from what boundary recorded.* If the brief names the first thin path the boundary session recorded, open with it and ask whether it is still right. Ask the lead to name one only when none was recorded.
   - *Offer it.* Say once, in your own words, why it comes first: it is built first and kept, so the contracts between the apps get proved early and each team's first story is its steps of it. Run `vela releases tracer-candidates --for-lead` and show its ranking as a short table: the flow by name, the apps it crosses, the new contracts it crosses (an outside party is not counted). Recommend the flow at the top, the one that proves the most of the system. Break a tie by what the first release's audience sees first. A tracer is often several flows in the order they run. For example, if two flows each cross three apps and three new contracts, recommend the one the first audience sees first, and put the flow that gets a person to it before it. If no flow page exists yet for the path the lead wants, take it in plain words, say a boundary session can draw it, and write no link (the slice page says "no flow page yet").
   - *Thin it.* For each requirement the tracer touches, ask whether it needs all of its checks or only some, said by their words. The checks left out go on a later release through the Delivers table below.
   - *What it leaves out.* Ask whether anything is held back from this path because it is not ready, such as a review or an approval. Each answer is a line under the slice's Not in this slice. Keeping the whole requirement in the tracer is a fine answer: write it as given and record in the session that the lead kept it all. Nothing here holds the session back; a lead who wants no tracer says so, and that is written as `**Flows:** none, <reason>`.
   - *How it ships, and what done is.* Ask how it goes live switched off (a flag, a switch, who holds it) and what done looks like from the side of the person who uses it. "Not decided yet" is a fine answer; write it so.
   The tracer is the slice page SLC-001.
4. **The next slices.** Ask which journey comes next, and what it comes after. Offer each remaining flow, or a short group of flows that make one journey, as a slice of its own, with what it comes after: the tracer, or another slice. Several slices may follow the tracer side by side. The lead decides each cut; you recommend. Steer toward thin journeys a person can watch working, never a layer.
5. **What comes next, and when.** Ask what the next date is, and which slices should be on by then. Repeat steps 1 and 2 for the next release. Go on until every requirement at `assumption` or later is on a release or the lead says "later, no date" for it.
6. **What the first date depends on.** Ask whether anything on the first date depends on something not yet agreed. Each answer becomes an unknown, with an owner handle and `**Blocks:**` linking the release's heading, and an ask-by date only if the lead gave or agreed one. Ask the lead first, and write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

Label every line with what it rests on: a source, the lead's words, or `(claude)`. Write a line only after the yes `START.md` defines; read the release back by name, in groups of about five lines. A requirement the lead won't date stays out of the file; tell them the check will keep listing it as undated until it has a release.

## 3. Write the confirmed slices and releases

Each slice is `vela add slice --title "<the journey, in the lead's words>" --flows FLO-nnn --after SLC-nnn --ships-switched-off "<how>" --done-when "<what passes>" --owner <handle> --capture ^cNN`, with `--milestone` when a release lists it and no `--after` on the tracer. It numbers the page, writes its bullets, its Changes row and its mark. Then add the opening of two or three sentences under the title, and the lines under `## Not in this slice`. A slice with no flow page, or the tracer with `**Flows:** none, <reason>`, is one `vela add slice` can't take: write that page by hand in the form `vela conventions "Slices"` gives, and tell the lead.

When the lead says a slice has moved to `building`, ask when its journey should run, and write the date they give as `- **Journey due:** YYYY-MM-DD` under Owner. Write no date nobody gave.

When you've added slices or changed their After, run `vela check-slice --changed --for-lead` and tell the lead, in your words, which slices it checked and why.

On `04b-releases.md`, one section per release, in the order they ship:

```
## Release one: March dock pilot

- **Target:** 2027-01-15
- **State:** assumption
- **Slices:** SLC-001, SLC-002

| Delivers | Criteria | Note |
|---|---|---|
| [[CAP-002-unlock-a-bike#CAP-002.FR2 Unlock with the app\|CAP-002.FR2]] | AC1, AC2 | AC3 in release two |
```

- **Target** is a real `YYYY-MM-DD` date. A date the lead has not given is not written; the release waits as a question. A bad date fails E344, and so does no date on a release at `assumption` or `decided`. A release at `inkling` may have none: W349 notes it.
- **Slices** names, by ID, the slices that should be on by the date; leave it out until one does.
- A vault that already names its tracer on release one (`**Tracer:**`, `**Not in the tracer:**`) or a later release's `**Flows:**` keeps working; offer to move each to a slice page, and replace the bullets with `**Slices:**` once the lead agrees.
- **Delivers** links the requirement's heading. **Criteria** is `all`, or the numbers of the criteria that hold, in the order of the requirement's bullets. **Note** says where the rest goes, such as "AC3 in release two", or is empty. A requirement may stand on several releases, each with different criteria; one placed on no release is not written.
- Replace the page's "No release is planned yet" line with one opening paragraph: how many releases, the first date and what is undated.
- Each release written gets a capture marked at once, `→ keep: [[04b-releases#<release heading>|<release name>]] (assumption)`, and a `## Changes` row, `| releases | - | assumption | [[<id>#^cNN]] |`: a release has no ID, so the row names the page.

Then run `vela render` and `vela check`, fix every error (E340 and E341 mean a link or a criterion number is wrong, E394 a circle of After), fix what W392, W393 and W347 say about a slice, tell the lead which requirements are still on no release, by their plain names (what the W343 lines list; don't say the code), and commit a checkpoint with `vela close stage --checkpoint --for-lead`.

## 4. Review, then finish

When the lead says a plain yes to a pick, run `vela decide` on it: if it answers that this session can't decide and marks the item ready to decide, offer the lead a short grill on it now, as it says.

Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the releases are written" and `04b-releases.md` as its focus. Show the digest as REVIEW says and capture what the lead takes.

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then a grill on the releases decides them, and `/vela:epics` cuts each team's epics against them.

## Never

- Write `decided`. Only a grill decides, unless the lead overrides it as `START.md` says.
- Invent a date, or turn a hope into a target. A date has a source or the lead's word.
- Change a requirement or its criteria to fit a release. A release that needs a check split differently is a question for `/vela:requirements`, never a quiet rewrite.
- Make a release for an epic. An epic never needs a release of its own.
