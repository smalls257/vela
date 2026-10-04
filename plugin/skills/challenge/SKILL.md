---
name: challenge
description: Challenge a handed-off boundary or contract as a team senior. Records the challenge as an open unknown the senior owns that blocks the challenged item, adds a Dissent line to the item, and opens a PR that asks the solution lead to answer. Never changes the item's state or text. Use when a senior disputes what they accepted at handoff.
argument-hint: "<item ID> <what is wrong>"
disable-model-invocation: true
---

# Challenge

A senior who accepted an app at handoff can still find that a boundary or a contract is wrong. This skill records that disagreement where the solution lead must answer it, without settling it. The challenged item keeps its state and its text. The senior's challenge becomes an open unknown that blocks it, so the vault cannot stay quietly `decided` on something a senior disputes.

The planner is `python3 .claude/skills/planner/bin/planner`. The format is `CONVENTIONS.md`.

## 1. Start

Run steps 1, 2 and 5 of `.claude/skills/planner/references/START.md` with mode `challenge`. The record has `modes: [challenge]` and the title `Challenge: <ID>`. The topic is the challenged ID, so the session id is `<date>-challenge-<id-lowercased>`, for example `2026-11-21-challenge-con-001`. Read the Challenge row of `.claude/skills/planner/references/MODES.md`.

## 2. Find the challenged item

Run `python3 .claude/skills/planner/bin/planner query get <ID> --json`.

- If it says `not_found`, stop: "<ID> is not in this vault." Do not guess another ID.
- A challenge is about a boundary or a contract. Go on only if `kind` is `contract`, `app-building-blocks` (what the app does and does not do) or `epic` (an epic's criteria or scope). For anything else, say a challenge does not cover it, and offer an ask to the item's owner instead.
- Find the app: the page for a contract or app page, or each app in an epic's `apps`. Read its building-blocks page. If it has no `handed_off:`, say so: before handoff, a disagreement belongs in a Shape or a Grill with the solution lead. Ask whether to go on anyway.
- Run `python3 .claude/skills/planner/bin/planner handoff verify <APP-id>` and show the output, so the senior sees what changed since they accepted the slice. Exit 2 covers two cases, so show the tool's message. If it says "does not exist", there is no manifest: say so and go on. Any other exit 2 is a damaged manifest: tell the senior that what changed since handoff could not be read, and go on without claiming anything about it.

## 3. Hear the challenge

Ask the senior, one question at a time:

1. What is wrong with the item as written?
2. What concrete case shows it: a request, a failure, a load, a date?
3. What would they have it say instead?
4. By when do they need an answer? Recommend 14 days from today.

Capture each answer as said, with the senior's handle as origin. If you restate an answer and the senior accepts it, the origin is `claude, from <handle>`. Never answer a question for them, and never argue the item's side. The solution lead does that.

## 4. Write the unknown and the Dissent line

Write only these, and change nothing else:

- On `11-unknowns-and-risks.md`, add the unknown. Its number is the highest `UNK-nnn` in use plus one, the next free `UNK-nnn`. Never fill a gap. Count the numbers in use in three places: `main`; the `11-unknowns-and-risks.md` of each branch on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:11-unknowns-and-risks.md`); and the `## Changes` tables of those branches' records (`git show <branch>:sessions/<id>.md`), because an open session may already hold the next number. Add the entry at the end of `## Unknowns`, before `## Risks`. The short name has at most six words and none of `# | ^ : % [ ]`.

```
### UNK-nnn <short name>

- **Question:** <the senior's question, in their words>
- **Owner:** @<senior handle> (<their role>)
- **Opened:** <today> challenge by @<senior handle>
- **State:** open
- **Ask by:** <the date the senior gave>
- **Blocks:** [[<page>#<heading>|<ID>]]
- **Notes:** Challenge after handoff. Case: <the case, in the senior's words>. Proposed: <what they would have it say>.
```

  Use `link` from the query answer for the `**Blocks:**` link. For an app page or an epic, link the page: `[[<page>|<ID>]]`. Challenging an APP page blocks every decided unit on it, so E316 fires once per unit. Say so to the senior before writing, and prefer the one contract when the dispute is about one.
- On the challenged item, add one line. For a contract, put it under the contract's heading, after its last bullet. For an app page or an epic, put it at page level, after its `**Decision:**` line: `- **Dissent:** <senior handle>, <today>: <the reason in a few words> (see [[11-unknowns-and-risks#UNK-nnn <short name>|UNK-nnn]])`.
- In the record's `## Changes`, add `| UNK-nnn | - | open | [[<session id>#^cNN]] |`, citing the capture of the question. Mark that capture `→ keep: [[11-unknowns-and-risks#UNK-nnn <short name>|UNK-nnn]] (open)`. Mark each other capture of the senior's `→ keep` the same way, since its words are in the unknown. Park any capture whose origin starts with `claude` unless the senior picked it.

Never touch the item's `state:`, `**State:**`, wording, criteria or any other line. A challenge records a dispute. It does not settle one.

## 5. Render and check

Run `python3 .claude/skills/planner/bin/planner render`, then `python3 .claude/skills/planner/bin/planner check`. If the challenged item is `decided`, check now reports E316: "decided, but open unknown UNK-nnn blocks it". That is deliberate and stays in the PR. It tells the solution lead an answer is owed. Fix any other error with the senior, or stop and show it.

## 6. Close the record and open the PR

Set the record's `summary:` to one line the senior accepts, and `status: closed`. Stage every file `planner render` reported, plus the record, `11-unknowns-and-risks.md` and the challenged page, by exact path. Never use `git add -A`. Commit with the message `Challenge <ID>: UNK-nnn`. Run `git push -u origin session/<id>`. If the push fails, show the error, print the commands for the user to run, and stop.

The reviewer is the solution lead: the `owner:` of `01-goals.md`. Strip the leading `@`, pass a team `@org/team` as `org/team`, and drop the user's own handle, from `gh api user -q .login`. If nobody remains, leave out `--reviewer`.

Write the PR body to a temporary file:

- **Challenge.** The item, the senior's question, the case and what they propose, quoted from the captures.
- **Unknown.** `UNK-nnn`, its owner and its ask-by date.
- **Check.** The first line of the check output and the E316 line, if any.
- **The red check.** Say all of this: E316 is deliberate. It blocks the merge wherever planner-check is a required check, so the PR cannot merge while `main` reads `decided` with an open blocker. The solution lead answers on this branch, either by resolving `UNK-nnn` with a Grill or by setting the item back. For an epic, setting it back means `reopened`. After that the check turns green and the PR can merge.
- **What the solution lead can do.** Resolve `UNK-nnn` with the senior, in a Grill if the answer changes a decision. Or set the item back: a contract to `assumption`, an epic to `reopened`. Until one happens, the check stays red.
- **Since handoff.** The `planner handoff verify` output from step 2.

Run `gh pr create --base main --head session/<id> --title "<today> Challenge: <ID>" --body-file <file> --reviewer <handle>`. If `gh` fails, say so, print the branch name and the exact command, and stop. Never say a PR exists unless `gh` printed its URL.

## Never

- Never change the challenged item's state or text. Only the `**Dissent:**` line is added.
- Never decide, resolve, reopen or set back anything. Only a Grill decides, and the solution lead answers the challenge.
- Never name anyone but the senior as the unknown's owner.
- Never cite an ID that `planner query get` reports `not_found`.
