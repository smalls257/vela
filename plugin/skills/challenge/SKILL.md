---
name: challenge
description: Record that a team lead disagrees with what their app was given, as an open question the solution lead must answer, and send it for review. Use when a team lead disputes what they accepted at handoff.
argument-hint: "<item ID> <what is wrong>"
disable-model-invocation: true
---

# Challenge

A team lead who accepted an app at handoff can still find a boundary or a contract wrong; so can an owner whose item someone decided on their behalf (`**Decided by:** @x, on behalf of @owner`; agreeing, they add `- **Confirmed by:** @owner on <date>` instead). The challenge records the dispute without settling it: the item keeps its state and text, and an open question the team lead owns blocks it.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). When a command can't express what the team lead wants, say so and stop.

## 1. Start

Run `vela role`. In a reader copy (a published copy with no `.git`), say "Only the owner can record a challenge here. Write your disagreement as a proposal (/vela:propose) and send it to <the owner named in `.vela/published.json`>." Write nothing and open no session.

Run only the steps of `${CLAUDE_PLUGIN_ROOT}/references/START.md` that show the state of the clone, find open sessions, open the record and read how to talk (its steps 0, 1, 2 and 5): `vela session start --mode challenge --topic <ID> --for-lead` does the first three, and you read step 6 and the Challenge row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. The session is `<date>-challenge-<id-lowercased>` (`2026-11-21-challenge-con-001`), titled `Challenge: <ID>`; the answer path finds the PR by that title. Relay its lines as START's "Relaying a command" says; on exit 3, ask what it asks and run it again with `--resume <id>`, `--new` or `--title "<name>"`.

## 2. Find the challenged item

Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela query get <ID> --json`.

- If it says `not_found`, stop: "<ID> isn't in the plan." Do not guess another ID.
- Go on if `kind` is `contract`, `app-building-blocks` or `epic` (its criteria or scope), or if `decided_by` names the user among its `on_behalf_of` owners, whatever the kind. Otherwise say a challenge doesn't cover it and name the item's owner, who answers for it. Never draft a message to them, and never offer to.
- If `decided_by` is set, show who decided on whose behalf and the `override` bullets. The challenge leaves them alone.
- Find the app (the contract's or app's page, or each app in an epic's `apps`). If it has no `handed_off:`, say a disagreement before handoff belongs in a shape or a grill with the solution lead, and ask whether to go on anyway. An owner challenging a decision made on their behalf goes on.
- Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela handoff verify <APP-id> --for-lead` and say it by name: "Here's what changed since you took the app on." Exit 2 covers two cases, so read the tool's message to tell them apart; it's for you, not the team lead. If it says "doesn't exist", there is no manifest: say "There's no record of what you accepted at handover" and go on. Any other exit 2: say what changed since handoff could not be read, and go on without claiming anything about it.

## 3. Hear the challenge

Ask the team lead, one question at a time:

1. What is wrong with the item as written?
2. What concrete case shows it: a request, a failure, a load, a date?
3. What would they have it say instead?
4. By when do they need an answer? Recommend 14 days from today.

Capture each answer as said, with their handle as origin (`claude, from <handle>` for a restatement they accepted). Never answer a question for them, and never argue the item's side. The solution lead does that.

## 4. Write the open question and the Dissent line

Write only these:

- On `11-unknowns-and-risks.md`, at the end of `## Unknowns`, before `## Risks`. Number it with `vela next-id UNK` and use exactly what it prints: it counts `main` and every open session branch, so a number is never handed out twice. The short name has at most six words and none of `# | ^ : % [ ]`.

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
- On the item, one line: under a contract's heading after its last bullet, or for a page or epic after its `**Decision:**` line: `- **Dissent:** <team lead's handle>, <today>: <the reason in a few words> (see [[11-unknowns-and-risks#UNK-nnn <short name>|<short name>]])`.
- In `## Changes`, `| UNK-nnn | - | open | [[<session id>#^cNN]] |`, citing the question's capture. Mark it, and each other capture of theirs, `→ keep: [[11-unknowns-and-risks#UNK-nnn <short name>|UNK-nnn]] (open)`. Park a `claude` capture unless they picked it.

Never touch the item's `state:`, `**State:**`, wording, criteria or any other line. A challenge records a dispute. It does not settle one.

## 5. Render, check, read back

Run `vela render`, then `vela check`. For a `decided` item, check now reports E316, "decided, but open unknown UNK-nnn blocks it": deliberate, and it stays in the PR as the answer owed. Fix any other error with the team lead, or stop and show it.

Read back by name before anything is sent: "I've added the open question 'Hold expiry under load', owned by you, answer wanted by December 5. It blocks the Booking API contract, which stays decided and unchanged, with your dissent beside it. The check stays red until the solution lead answers. Anything to change?"

## 6. Close and send

This skill files its own record: `vela close finish` and `vela close push` stop on the deliberate red check.

The reviewer is the solution lead: the `owner:` of `01-goals.md`. Strip the leading `@`, pass `@org/team` as `org/team`, and drop the user's own handle (`vela whoami`). If nobody remains, leave out `--reviewer`.

1. Ask before anything leaves the machine: "I'll send this challenge for review to <the solution lead's name>. OK?" Capture the answer with `vela record add --origin <handle> --tag thought --mark "drop: the yes to send this for review" "<their words>"`. No yes: stop, with the record open.
2. Set `summary:` to one line the team lead accepts and `status: closed`, then run `vela close stage --session <id> --close --paths-from-render`. It commits the record and the changed pages by exact path; tell the team lead about any file it names as left out.
3. Run `git push -u origin session/<id>`. If it fails, say in one plain sentence that the challenge didn't go up and why, without pasting the push's own message, give the commands for the user to run, and stop.
4. Write the PR body to a temporary file, each item by name with its ID beside it:
   - **Challenge.** The item, the question, the case and the proposal, quoted from the captures.
   - **Open question.** Its short name, `UNK-nnn`, owner and, when it has one, ask-by date.
   - **Check.** The check's first line and the E316 line, if any.
   - **The red check.** Never promise a red check for an item that is not `decided`. Not decided (an `assumption`, a `draft`): nothing blocks this merge; the dispute lives in `UNK-nnn` and the `**Dissent:**` line, and the item can't be decided while the question is open. Decided: E316 is deliberate. It blocks the merge wherever vela-check is a required check, so the PR can't merge while `main` reads `decided` with an open blocker. The solution lead answers on this branch, either by resolving `UNK-nnn` with a grill or by setting the item back: a contract to `assumption`, an epic to `reopened`, which a later grill decides again with `| EPC-nnn | reopened | decided | ... |`. Then the check turns green and the PR can merge. `/vela:grill` naming this PR or <ID> opens an answer session on this branch, and `/vela:close` pushes the answer here and comments on this PR. Say: "Run `/vela:grill` and name this PR or <ID>."
   - **Since handoff.** The `vela handoff verify` output.
5. Run `gh pr create --base main --head session/<id> --title "<today> Challenge: <ID>" --body-file <file> --reviewer <handle>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

- Never change the challenged item's state or text. Only the `**Dissent:**` line is added.
- Never decide, resolve, reopen or set back anything. Only a grill decides, and the solution lead answers the challenge.
- Never name anyone but the team lead as the open question's owner.
- Never cite an ID that `vela query get` reports `not_found`.
