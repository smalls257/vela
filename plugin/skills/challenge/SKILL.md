---
name: challenge
description: "Record that a team lead disagrees with what their app was given, as an open question for the solution lead. Offer it when a team lead says a boundary or contract is wrong; start it only on a yes."
argument-hint: "<item ID> <what is wrong>"
---

# Challenge

A team lead who accepted an app at handoff can still find a boundary or a contract wrong; so can an owner whose item someone decided on their behalf (`**Decided by:** @x, on behalf of @owner`; agreeing, they add `- **Confirmed by:** @owner on <date>` instead). The challenge records the dispute without settling it: the item keeps its state and text, and an open question the team lead owns blocks it.

`vela` is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela`. A command that stops names its fix, so do that or ask the team lead. When a command can't express what the team lead wants, say so and stop.

## 1. Start

Run `vela role`. In a reader copy (a published copy with no `.git`), say "Only the owner can record a challenge here. Write your disagreement as a proposal (/vela:propose) and send it to <the owner named in `.vela/published.json`>." Write nothing and open no session.

Run only the steps of `${CLAUDE_PLUGIN_ROOT}/references/START.md` that read how to talk and start the session (its steps 0 and 1): read step 0; `vela session start --mode challenge --topic <ID> --for-lead` is step 1, and you read the Challenge row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The session is `<date>-challenge-<id-lowercased>` (`2026-11-21-challenge-con-001`), titled `Challenge: <ID>`; the answer path finds the PR by that title. Relay its lines as START's "Relaying a command" says. The session's words stay in notes on this machine, and only its header is committed. The topic is the item's ID, never a person's name.

## 2. Find the challenged item

Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela query get <ID> --json`.

- If it says `not_found`, stop: "<ID> isn't in the plan." Do not guess another ID.
- Go on if `kind` is `contract`, `app-building-blocks` or `epic` (its criteria or scope), or if `decided_by` names the user among its `on_behalf_of` owners, whatever the kind. Otherwise say a challenge doesn't cover it and name the item's owner, who answers for it. Never draft a message to them, and never offer to.
- If `decided_by` is set, show who decided on whose behalf and the `override` bullets. The challenge leaves them alone.
- Find the app (the contract's or app's page, or each app in an epic's `apps`). If it has no `handed_off:`, say a disagreement before handoff belongs in a shape or a grill with the solution lead, and ask whether to go on anyway. An owner challenging a decision made on their behalf goes on.
- Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela handoff verify <APP-id> --for-lead` and say it by name: "Here's what changed since you took the app on." If it exits 2, tell its two cases apart from its message (it's for you, not the team lead): "doesn't exist" means no manifest, so say "There's no record of what you accepted at handover"; any other case, say what changed since handoff could not be read. Either way go on without claiming anything about it.

## 3. Hear the challenge

Ask the team lead, one question at a time:

1. What is wrong with the item as written?
2. What concrete case shows it: a request, a failure, a load, a date?
3. What would they have it say instead?
4. By when do they need an answer? If they're unsure, propose a date with its reason and take their yes, as `MODES.md` says under "Unknowns".

Capture each answer as said, with their handle as origin (`claude, from <handle>` for a restatement they accepted). Never answer a question for them, and never argue the item's side. The solution lead does that.

## 4. Write the open question and the Dissent line

Write only these:

- On `11-unknowns-and-risks.md`, at the end of `## Unknowns`, before `## Risks`. Number it with `vela next-id UNK` and use its number. The short name has at most six words and none of `# | ^ : % [ ]`.

```
### UNK-nnn <short name>

- **Question:** <the team lead's question, in their words>
- **Owner:** @<team lead's handle> (<their role>)
- **Opened:** <today> challenge by @<team lead's handle>
- **State:** open
- **Ask by:** <the date they gave>
- **Blocks:** [[<page>#<heading>|<ID>]]
- **Notes:** Challenge after handoff. Case: <the case, in their words>. Proposed: <what they would have it say>.
```

  `**Blocks:**` takes `link` from the query answer; an app page or an epic is `[[<page>|<ID>]]`. Challenging an app page blocks every decided item on it, so E316 fires once per item. Say so without the code before writing, and recommend the one contract when that is the dispute: "Challenging the whole app page flags every decided item on it (about 9), not just the one you dispute. I'd challenge only the contract."
- On the item, one line: under a contract's heading after its last bullet, or for a page or epic after its `**Decision:**` line: `- **Dissent:** @<team lead's handle>, <today>`. The team lead's own words follow it, as `: "<the reason in a few words>" (see [[<session id>]])`, only if they keep them at the read-back in step 5; without that the line says who disagreed and when, and the open question holds the reason.
- In the notes' `## Changes`, `| UNK-nnn | - | open | [[<session id>#^cNN]] |`, citing the question's capture. Mark it, and each other capture of theirs, `→ keep: [[11-unknowns-and-risks#UNK-nnn <short name>|UNK-nnn]] (open)`. Park a `claude` capture unless they picked it.

Touch no other line of the item: a challenge records a dispute, it does not settle one.

Draft the paragraph each filed item owes now, as `START.md` says under "Draft the paragraph when the item is filed", and show it with the filed line.

## 5. Render, check, read back

Run `vela render`, then `vela check`. For a `decided` item, check now reports E316, "decided, but open unknown UNK-nnn blocks it": deliberate, and it stays in the PR as the answer owed. Fix any other error with the team lead, or stop and show it.

Read back by name before anything is sent: "I've added the open question 'Hold expiry under load', owned by you, answer wanted by December 5. It blocks the Booking API contract, which stays decided and unchanged, with your dissent beside it. The check stays red until the solution lead answers. Anything to change?"

Then read the team lead's Dissent words back to them directly from the page before they leave the machine, and any quote the pull request will carry with `vela close readback --for-lead`: they keep, reword or cut each. A line goes in the pull request only if they pick it (`vela close readback --pick ^cNN`), and only their own words can be picked.

## 6. Close and send

This skill files its own session: `vela close finish` and `vela close push` stop on the deliberate red check.

The reviewer is the solution lead: the `owner:` of `01-goals.md`. Strip the leading `@`, pass `@org/team` as `org/team`, and drop the user's own handle (`vela whoami`). If nobody remains, leave out `--reviewer`.

1. Ask before anything leaves the machine: "I'll send this challenge for review to <the solution lead's name>. OK?" Capture the answer with `vela record add --origin @<handle from vela whoami> --tag decision --mark "drop: the yes to send this for review" "<their words>"`. No yes: stop, with the session open.
2. Run `vela close stage --session <id> --close --summary "<one line the team lead accepts>" --paths-from-render`. Tell the team lead about any file it names as left out. The summary opens the pull request and nobody reads it back, so it quotes no one: say what was filed, never what anyone said.
   When the plan shares its repository with other plans (`vela plans` lists more than one), the session's branch is `session/<plan>/<id>`, not `session/<id>`: wherever `session/<id>` appears below, use the `branch` in `.vela/session.json`, and put `[<plan>] ` in front of the PR title (the plan is the last folder of the path `vela plans --here` prints).
3. Run `git push -u origin session/<id>`. If it fails, say in one plain sentence that the challenge didn't go up and why, without pasting the push's own message, give the commands for the user to run, and stop.
4. Write the PR body to a temporary file, each item by name with its ID beside it:
   - **Challenge.** The item, the question, the case and the proposal, in your words. Quote only the team lead's own words that they picked at the read-back, never anyone else's.
   - **Open question.** Its short name, `UNK-nnn`, owner and, when it has one, ask-by date.
   - **Check.** The check's first line and the E316 line, if any.
   - **The red check.** Never promise a red check for an item that is not `decided`. Not decided (an `assumption`, a `draft`): nothing blocks this merge; the dispute lives in `UNK-nnn` and the `**Dissent:**` line, and the item can't be decided while the question is open. Decided: E316 is deliberate. `vela check` fails on it until it is answered, so the PR shouldn't merge while `main` reads `decided` with an open blocker. The solution lead answers on this branch, either by resolving `UNK-nnn` with a grill or by setting the item back: a contract to `assumption`, an epic to `reopened`, which a later grill decides again with `| EPC-nnn | reopened | decided | ... |`. Then the check turns green. `/vela:grill` naming this PR or <ID> opens an answer session on this branch, and `/vela:close` pushes the answer here and comments on this PR. Say: "Run `/vela:grill` and name this PR or <ID>."
   - **Since handoff.** The `vela handoff verify` output.
5. Run `gh pr create --base main --head session/<id> --title "<today> Challenge: <ID>" --body-file <file> --reviewer <handle>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

- Never change the challenged item's state or text. Only the `**Dissent:**` line is added.
- Never decide, resolve, reopen or set back anything. The solution lead answers the challenge, settling it or with a grill.
- Never name anyone but the team lead as the open question's owner.
