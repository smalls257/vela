---
name: close
description: Close an initiative-vault session. Marks every capture keep, park or drop by default and asks only what is unsettled, writes the promoted items into the pages, drafts prose in the house voice, renders and checks the vault, then commits, pushes and opens the PR with reviewers. Use when the lead says they are done ("close", "we're done", "switch to ...") or types /planner:close. Never start it on your own.
argument-hint: "[session id, if more than one is open]"
---

# Close a session

Close turns a session record into a reviewed PR. Run every step in order. Never skip a step to save time, and never report a step as done when it failed.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The format is `CONVENTIONS.md`.

## Starting a close

Close is started by the lead's word, never by yours. If the lead typed `/planner:close`, go on. If you were asked to start it in conversation ("close", "close it", "we're done", "switch to requirements"), that word is the yes to filing: say in one line what will happen ("I'll file your notes, write the pages and send the branch for review") and go on. If the lead only sounded finished, ask "Shall I close this out now?" and wait. Do not start a close because the work looks complete, a turn limit is near or a gate stopped you.

One confirmation stays, because the push and the pull request are the only steps that leave the machine and a hard stop forbids sending company material without consent. Before section 7 pushes, say what is about to be sent ("I'll push `session/<id>` and open a pull request for <reviewers>") and wait for a yes. Skip that wait only when the lead has said "push" or "open the PR" in so many words in this conversation. A bare "close" is consent to file, not to send.

Close talks in the session's voice. If this conversation has not read `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` yet (a close typed in a fresh conversation), read it now, as step 6 of `${CLAUDE_PLUGIN_ROOT}/references/START.md` says.

What the lead reads while close runs is short and in plain words. No check code, gate name, capture number, copy ID or finding ID appears in what you say to them; those go in the files and the pull request body. A command that fails and that you fix is not news.

## Reader copy: no git, no PR

Run `planner role` first. If it says `reader` (a published copy: `.planner/workspace.json`, no `.git`), say once, plainly: "This is a read copy, so close writes your session record and stops. Nothing is committed, pushed or sent." Then run the sections below with these changes, and no other:

- **Section 1:** find the open record with `grep -l '^status: open' sessions/*.md`. There are no branches; run no `git` or `gh` command.
- **Section 3:** an item the session decided or overrode keeps `decided` and gets `- **Pending approval:** @<handle>, <today>` beside it (see "Pending approval" in `CONVENTIONS.md`). Use the handle START.md asked for. An owner's decision never gets the marker; here every decision is a reader's.
- **Section 4:** the changed pages are the ones the session's `## Changes` table and captures name, not `git diff`. Skip the examples harvest (it needs `gh` and `git`). Skip the `git restore` and checkpoint-commit lines of the voice review: write the rewrite to the page only after `planner voicecheck` passes, and keep the earlier draft in a copy beside it until then.
- **Section 6:** run only the render and the check. Skip the fetch and the merge of `main`.
- **Section 7:** write `summary:` and set `status: closed`, render and check; stage nothing. Never write a handoff manifest: handoff is the owner's.
- **Section 9:** runs as written; it needs neither git nor `gh`.
- **Section 8:** skip it. Say: "Nothing was committed, pushed or sent. Your changes are in this folder; to send them to the owner as a proposal, run `/planner:propose`." Never say a PR exists.

Write the session record as usual: it is the one record of what you did.

## 1. Find the session

Open records live on `session/<id>` branches, so first run `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`, and read each record with `git show <branch>:sessions/<id>.md`. Find the one with `status: open`. If none is open, say so plainly in one line, change nothing in the vault's pages, and go straight to section 9, which has its own path for a close with no session. If there is more than one, ask which. A branch can hold more than one record, because an answer session shares its challenge's branch, so also run `git grep -l '^status: open' <branch> -- sessions/` for each branch. Find that record's branch and switch to it with `git switch <branch>` before anything else. For most sessions it is `session/<id>`. For a session whose `modes` include `answer`, it is the challenge's branch.

## 2. Mark every capture

Mark every capture that has none yet by the defaults below, without asking. Filing is the tool's work, not the lead's. Keep the full list of marks, each with its one-line reason, for the pull request body; never show it to the lead as a numbered list to approve. A new item gets its ID in section 3, and the marks are written into the lines at the end of it, once every ID exists.

Then show the lead only what the defaults could not settle: at most three items, each one plain sentence with your recommended answer, asked in one message. These are the kinds of thing that qualify, and nothing else does:

- a `claude`-origin line the lead might want kept, or an `unknown` of yours that needs a keep or a drop;
- an unknown with nobody who could answer it;
- a line you would copy word for word that the lead did not say themselves;
- a belief the plan seems to rest on, when you cannot tell whether it is load-bearing.

For example: "I'd write the 18 January slot down as a constraint, from your account. Right?" and "Nobody has said who could settle whether a call digest is a client record. I'd ask legal and chase it on 6 November. Is that the right person?" If more than three are unsettled, ask the three that matter most and take your recommended answer for the rest, listing them in the pull request body. When the lead answers, write it, and say in two or three sentences what you filed, by group and in their words ("I kept the 8 hard limits as constraints, parked the 12 what-ifs and dropped 5 that repeat other lines"). Never show a capture number. Do not ask "anything to change?" a second time.

Never ask the lead for bookkeeping the record already holds or the tool can work out: not a handle (`START.md` says where it is kept), not the session's minutes (section 8), not whether a source document gets a row in `sources.md` (write the row for each document the lead brought in, and say so in the summary), not whether another gap turned up. Defaults:

- In a session whose `modes` include `shape`, the picked option is kept as an `assumption`, never an `inkling`. See section 3.
- A capture that names something the initiative cannot change, such as a date, a budget, a law, a contract term or a system it must keep, is kept as a constraint: a row on `02-constraints.md`, `| CST-n | <the constraint> | <where it comes from, as a link on the words> | <what it forces> |`. The link's label pipe is written `\|` there, because the link sits in a table cell.
- A person's `idea` or `thought` is kept as an `inkling` on the page it belongs to.
- A capture that says `type at close: PTY` or `type at close: SV` names a subject the lead said exists. It gets one mark, to the subject, `→ keep: [[03-context-and-scope#<heading>|<ID>]] (subject)`, because a party or stored value carries no state. That holds when its words also start with the existence question's copy ID: section 3 writes that copy's row, and the row's `## Changes` line cites the capture, so the capture needs no second mark. If section 3 leaves the subject untyped, mark it as a keep to the unknown section 3 writes instead, `→ keep: [[11-unknowns-and-risks#<heading>|UNK-nnn]] (open)`, so no mark links a heading that does not exist.
- Any other capture whose words start with a copy ID or a finding ID is kept as its ledger row, `→ keep: [[11-unknowns-and-risks#Question ledger|<copy>]] (<state>)`, with the state of the row. A finding the lead did not take has no capture, so it gets no mark. Section 3 says which of those still get a row.
- A capture that says how a concern touches an app, as `unchanged`, `n/a` with why, or `unknown` with its unknown, is kept as that concern cell, as `CONVENTIONS.md` says under "Concern cells and waivers". Only a Grill writes `addressed`.
- A capture that answers an open unknown, the lead's first-hand word or a source the session read, is kept as that unknown resolved, as `MODES.md` says under "Unknowns": `→ keep: [[11-unknowns-and-risks#<heading>|<ID>]] (resolved)`. A first-hand answer needs its own row in `sources.md` first.
- A person's `unknown` or `worry` is kept as an unknown, or as a concern cell. Its `**Owner:**` is the handle of the lead who is chasing it, and the person who would know goes on the `**Ask:**` line as the role the lead named ("CISO", "outside counsel"); never stop to ask for a handle. Its ask-by date is the date the lead gave, else the nearest hard date the vault holds (a constraint or a release target), else two weeks from today. Say the date you chose in the summary.
- An `unknown` capture is kept or dropped with a reason. It is never parked. For a `claude`-origin `unknown`, the user must choose, so it is one of the few items you ask about: kept as an UNK with an owner and an ask-by date, or dropped with a reason. Number each new UNK with `planner next-id UNK`, run again after each one is written, so the number is never guessed or reused from an open session branch. Claude never decides it alone. This rule wins over the park default for `claude` lines.
- A person's `wild` line is parked, never dropped.
- A `(claude)` line is parked unless the user picks it. This covers every origin that starts with `claude`, including `(claude, from <name>)`.
- Never propose `fact`. A capture becomes a fact only if the user names its source in this turn and the source has a row in `sources.md`.
- A line you will copy word for word onto a page is a lifted line. When the lead said it themselves, copy it and list it in the pull request body. When anyone else said it, or it is `claude`'s, it is one of the few items you confirm before you copy it.

A line a Grill already marked `(decided)`, a Discover already marked `(fact)`, or a Boundary, Requirements, Allocate or Releases session already marked `(assumption)`, keeps its mark. Leave it alone. It still appears under "Promoted on a nod" when its origin starts with `claude`.

## 3. Write the promoted items

Write each kept item onto its page as structured content only: fact bullets, table rows and `### <ID> <short name>` headings, per `CONVENTIONS.md`. A Grill already wrote its decided items, Discover already wrote its facts, Boundary already wrote its app, contract and runtime pages, Requirements already wrote its functional requirements, Allocate already wrote its allocation rows and any contract it proposed, and Releases already wrote `04b-releases.md`, so leave those alone. Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written, and never move, merge or reword one. If the user overrode a rule during the session and no bullet records it yet, write it now, in the grammar of `CONVENTIONS.md` under "Overrides", with the handle, date and reason from the capture. If no rule was set aside, write no `**Override:**` bullet: something the lead wishes (who may reopen an item, and when) is a Notes line, not an override, and an `**Override:**` never names a rule that exists nowhere in the skills.

For a session whose `modes` include `epics`, the epic pages already exist, so write no `assumption` item for a picked cut, and skip the `shape` paragraph that follows. Still add the `## Changes` rows for every epic whose state changed, `| EPC-nnn | - | draft | [[<id>#^cNN]] |` and `| EPC-nnn | draft | decided | ... |`, or `| EPC-nnn | reopened | decided | ... |` for a reopened epic, if the session has not already. For any other session whose `modes` include `shape`, write the picked option as an `assumption` item with an `**Options considered:**` bullet, at page level or under the item's heading: `- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`. `planner next` reads it: an `assumption` without it still needs a Shape, and one with it is ready for a Grill. If a capture says "that's decided", add a "grill to confirm" note to the item. The item must pass grill's GATE-2 afterwards: at `assumption`, with a preferred option and the rejected options with their reasons. New items get the next free ID of their kind: grep the vault for the existing IDs of that kind, and also read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'` (`git show <branch>:sessions/<id>.md`), because another open session may already hold the next ID. Add one to the highest in use. Add one row to `## Changes` for each item whose state changed: `| ID | From | To | [[<id>#^cNN]] |`.

### Type the subjects Dump named

A kept capture that says `type at close: PTY` or `type at close: SV` names a subject the lead said exists, in this session or an earlier one. Write it on `03-context-and-scope.md`: a party as `### PTY-nn <name>` under `## Outside parties`, stored value as `### SV-nn <name>` under `## Value held for customers`, adding the section if the page lacks it, with the next free ID as above. Fill each required fact from what the user said, in the captures or in this turn, and ask for any the user did not give. Never fill a fact from general knowledge, and never guess one. A missing fact is E808.

- A party: `**Relationship:**` is `partner`, `supplier`, `regulator` or `customer group`. `**Agreements:**` lists the agreements, with their `SRC-nn`, or says `none known`.
- Stored value: `**Holder:**` is a link to the app or party that holds the balances, or its name. `**Owner:**` is who carries them, or `not known yet, see [[11-unknowns-and-risks#UNK-nnn <name>|UNK-nnn]]`, with that unknown written as section 2 says. Only `**Owner:**` may say `not known yet`.
- If nobody knows a party's relationship or a stored value's holder, write an unknown that asks, with an owner and an ask-by date, and leave the subject untyped. Mark its capture as a keep to that unknown, as section 2 says, and list it under **Questions** in the PR body.

Then record the yes. Dump starts the capture with the existence question's copy ID, such as `Q-FIN-01@INI-001: yes, ... type at close: SV`. A capture with only the note comes from an older session: its copy is the initiative copy of the entry whose `creates:` is that kind, so ask the lead which question they answered if more than one fits. Write that copy's row in the ledger as the next part says: `answered`, `item:` linking the new subject, `answer:` the lead's yes in one line, and `source:` by the source rule there, which means a first-hand `SRC-nn` when the lead's word is the only source. If the subject stays untyped, the row is `unknown`, linking the unknown that asks for its relationship or holder: the yes is said, and the subject waits for that answer. If the copy already has a row, an earlier session recorded the yes, so write no second row. Add the `## Changes` row for the copy, citing the capture.

A typed subject makes the catalogue owe its questions. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --subject <ID>`, list its copies under **Questions** in the PR body, and write its row below for each copy a capture answers. The rest stay undisposed until a session takes them.

### The question ledger

Every owed copy the lead took, and every finding a review checkpoint kept, ends in a row of the table under `## Question ledger` on `11-unknowns-and-risks.md`, in the grammar of `CONVENTIONS.md` under "Questions and the ledger". If the page has no such section, add it after `## Risks`: the heading, an empty block (`<!-- generated:undisposed-questions sha=00000000: do not edit, run planner render -->` and `<!-- /generated:undisposed-questions -->` on the next line), then the header `| Copy | State | Evidence | By | Date |` and `|---|---|---|---|---|`.

List every capture whose words start with a copy ID such as `Q-FIN-03@SV-01`, a wildcard such as `Q-OPS-01@APP-*`, or a finding ID such as `F1.2`, and every row of the record's `## Reviews` tables. Write a ledger row for each by the rules below, without asking; the rows go in the pull request body, not the conversation. Only a row whose state the lead's words leave unclear is one of the few items section 2 asks about:

- A capture `waits on UNK-nnn: <IDs>` makes each ID's row `unknown`, with `unknown: UNK-nnn`. A copy or `R-` id that already has a row keeps its one row, changed in place, with a reviewer question's `question:`, `quote:` and `severity:` kept; a copy with no row gets one. A finding ID in the list stands for the copy or `R-` id its row in `## Reviews` names; a finding with copy `new` first gets its `R-<AREA>-nn` id, as the next item says, and that row is written `unknown`. Each gets a `## Changes` row from its old state, such as `| R-OPS-12 | open | unknown | [[<id>#^cNN]] |`, or from `-` for a new row. The unknown must be open and its owner a handle; if it is not, use the lead's handle as owner and the role the lead named as `**Ask:**`.
- A finding about an owed copy that the lead did not take adds no row. The copy stays undisposed, and the `undisposed-questions` block shows it.
- A finding with copy `new` becomes a reviewer question, `R-<AREA>-nn`, with the next free number for its area. When its Area cell lists several areas, because the merge folded the same question from each, the row takes the first area's code and is one row, never one per area. Section 6 merges `main` in later, so look in the ledger on this branch and on `origin/main` (run `git fetch origin`, then `git show origin/main:11-unknowns-and-risks.md`), and in the ledger rows and `## Changes` tables on the other `session/*` branches. Its evidence holds `question:`, `quote:` and `severity:` from its row in `## Reviews`. Its state is `open` unless the lead took it.
- The state comes from what the lead said, and its evidence follows the state table in `CONVENTIONS.md`. What close adds:
  - `answered`: `item:` links the item the answer was written into. A document the lead names is cited by its `SRC-nn`. When the lead's own word is the only source, add a first-hand row to `sources.md`, `| SRC-nn | <name>'s first-hand account of <subject> | @<lead> | <today> | exists | said in session <id> |`, and cite it. A page quote may cite only text that was on the page before this close, or that sits under an item at `fact` or `decided`, never words this close wrote. With no such source, the row is `assumed`.
  - `assumed`: write `load-bearing: yes` when the captures show the plan resting on it and `no` otherwise, and a `signpost:` from what the lead said would show it wrong. Ask only when the question is high severity and you cannot tell.
  - `unknown`: link the UNK this close writes, with its owner and ask-by date.
- One answer for several copies is one row: a wildcard such as `Q-OPS-01@APP-*`, or an initiative row with `covers: <scope>`. A copy that is an exception gets its own row.
- By is the handle of whoever recorded or decided the row, and Date is today. Never write `answered` without an item link and a source, and never invent a source.
- A Grill's capture "decided with <copy IDs> open (W807)" is a record of a decision, not an answer: write no row for those copies, and keep the note on the item's `## Changes` row as the Grill wrote it.

Add a `## Changes` row for each new ledger row: `| <copy> | - | <state> | [[<id>#^cNN]] |`, citing the capture. A reviewer question the lead did not take has no capture, so its row cites its checkpoint's heading in `## Reviews` instead: `[[<id>#<n>. <checkpoint>, <date>]]`.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check`. Each E801, E802 or E803 on the ledger is a row written wrong: show it and fix it with the user. If no source the check accepts exists, write the row as `assumed` or `open`, whichever the lead's words support, and list it in the pull request body. Never delete a row to quiet the check, and never drop one without saying so.

### Gaps the catalogue missed

Never ask the lead whether a gap turned up late, or by luck: the answer is almost always no, and the question belongs to whoever maintains the catalogue. Instead, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --stats` and list in the pull request body, under **Catalogue proposals**, each entry whose copies in this vault all ended `not-applicable` as one to prune or tighten, and each reviewer question this close wrote that is not `not-applicable` as an entry that never fired. Pruning is the maintainer's call.

If the lead said during the session, in so many words, that the catalogue missed something, draft an entry from that capture:

```yaml
- id: Q-<AREA>-nn  # the next free number in that area of the catalogue
  area: <AREA>
  scope: <initiative, app, contract, capability, party or stored-value>
  trigger: <exists, or a condition in the grammar of CONVENTIONS.md>
  question: <the question, worded for any vault, not only this one>
  why: <found late in session <id>: what was missed, and what finding it late cost>
  severity: <high or normal>
```

Write it under `## Catalogue proposals` in the session record as one YAML block and list it in the pull request body. Never edit `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`: the catalogue belongs to the toolkit, so code decides what is owed only once the toolkit takes the entry.

### Write the marks

Every new item, subject, unknown and reviewer question now has its ID. Write each mark into the line: `→ keep: [[<page>#<heading>|<ID>]] (<state>)`, `→ park` or `→ drop: <reason>`, before the `^cNN`.

## 4. Draft the prose

Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it for every paragraph this session needs. Those are:

- the opening prose of every page this session changed (`git diff --name-only --diff-filter=d main...HEAD`, leaving out `sessions/` and `sources.md`), rewritten to say what is true now, as `CONVENTIONS.md` says under "Pages". Keep the owner's own wording wherever the facts it states have not changed, because a later close harvests those edits; rewrite only what the session made untrue or left out. Never add a paragraph about what changed: that is the page's `## History`. A page has one opening: the one you rewrite replaces the old one, and you never write a new opening beside it. Two or more separate opening paragraphs above the first `##` heading, running past 150 words together, draw W371; keep one and fold what the others add under a heading. The opening is two or three plain sentences, at most about 80 words and three links: what is true now and the one thing that holds it up. It names threads, not items, and sends the reader to the block or table below for the items; a state is said once, in one sentence, and never added to each clause (`house-voice` rules 1, 3 and 7). A page of more than about 900 words with no such opening draws W363, an opening over 90 words or 3 links draws W365, and an opening that is still a line the template wrote draws W368. Run `planner check` for W363, W365, W368 and W371 on every page whose opening you wrote, and rewrite until none remains; do not list the warning in the pull request instead. An opening is never a changelog ("Five more unknowns came from the desks session..."). On a page that is mostly a list (unknowns and risks, concerns, decisions, sources), the opening counts and points and never enumerates the list, as `house-voice` says under "Pages that are mostly a list": "28 questions are open. Five hold up the first release; the most urgent is who owns Heron, due 23 October." The items go below it, grouped by what they hold up;
- the sentences on other pages that mention an item whose state this session changed. For each unknown this session resolved and each item it decided, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner query refs <ID>`, open each page it lists, and rewrite the sentence that links the item so it says what is true now: "the account opens at the first practice trade", not "when the account opens is still open". Leave `## History` alone. `planner check` reports W334 for a sentence still calling an answered question open;
- the `## Strategy` paragraph of each concern page whose cells this session changed;
- on a page that lists more than about seven unknowns, concerns or other items, the few that matter first, and the rest under `## Also open (n)` at the end of the list's section, which the viewer and the explorer fold. Group any other list of more than about seven under subheadings of about five, each line reading the plain name, who to ask and by when, and what it holds up. People hold about four to seven things at once;
- the opening sentence of each `### <ID>` item this session wrote or changed, before its fact bullets;
- a decision record for each page this session made `decided` whose decision shapes the whole design: the solution strategy or another initiative section, an app page, or a flow. Write it as `09-decisions/ADR-nnnn-<slug>.md`, with `id`, `type: decision`, `title`, `state: decided`, `owner`, `authored: authored` and `sources`, and these sections: `## Context` (what forced the choice), `## Decision` (what was chosen, linking the decided page), `## Alternatives considered` (a table, `| Alternative | Why rejected |`, from its `**Options considered:**`) and `## Consequences` (what it commits people to). Put its `**Decision:**` bullet, linking the Grill, under `## History`, and link the record from `09-decisions/09-decisions.md`. Contracts and unknowns get no record of their own;
- a glossary entry for each term the session used that a newcomer to the initiative would not know, such as a product name or a word like "paper trading": one paragraph on `12-glossary.md`, the term in bold, then what it means here;
- the paragraphs below.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner style <each changed page>` and fix every line it prints: move a history bullet under `## History`; write a labelled bullet nothing reads as a sentence in its section, merged with any prose that already says it; open an item that has only bullets with a sentence; say a bracketed aside in the sentence; label a link with the thing's name; and give a page with no opening prose one. An ID in a sentence or a list item is moved to a `- Trace:` line under it and the sentence names the thing in plain words. Fix only what it names, and run it again until it prints nothing. It also lists each word of the lint list (`${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`) the page uses, with its count: say what the thing does in plain words. Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check` and fix each W365 to W369 line on the pages you changed the same way: split a long paragraph at its second topic or move its pointers to a table, cut a table cell to a clause, say a repeated state once and put the rest on a Trace line or in the table, replace a template opening with what is true now, and spell an abbreviation out at its first use. Never delete an `**Ask:**`, `**Target:**` or `**Owning team:**` line, or a `- Trace:` line, to quiet it: the planner reads them, and a line it still flags is a planner bug to report in the PR body. For a session whose `modes` include `epics`, each epic it drafted owes its summary, its `Still open:` line and its `## Who this is for and what changes` section, in the epic template's order, so list those epics under "Prose drafted" in the PR body. The epics session already wrote each `**Owning team:**` line; close leaves it as written. Prose is drafted here and nowhere else. When a merged paragraph is wrong as a whole, `house-voice` says to rewrite it: first copy the old paragraph word for word under `## Replaced prose` in the session record (page, date, then the paragraph), so no edit of the owner's is lost. Commit each drafted page, by exact path, with the message `draft: prose for <id>`. That commit holds each drafted page whole, including its structured section-3 edits, because a page cannot be committed in halves. The reviewer's later edits then show as a diff against it.

### Voice review

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this part if the session drafted no paragraph, and go on to the part "Harvest the owner's edits".

**Voicescore, optional.** `planner voicescore` places each paragraph against the owner's own range with a style embedding, a second reading of a different kind from the reviewer's. It is information, not a gate. It runs only when it is installed and the owner has at least 5 active `owner` and `owner-edit` examples. Run it after step 1 and before step 2:

- Write the paragraphs of step 1's list to `.planner/voicescore-input.md`, in list order, one blank line between them, so ¶n is entry n. It sits in `.planner/` is gitignored, so nothing in it is ever staged. It is not under `.git/`, because Claude Code will not write there without asking.
- Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner voicescore .planner/voicescore-input.md --json`, then `rm -f .planner/voicescore-input.md`.
- It did not run when it printed `"ran": false` (keep its `reason`), when `"reliable"` is false (the reason is "fewer than 5 owner examples"), when its paragraph count differs from the list (the reason is "its paragraphs did not match the list"), or when the command failed in any other way (the reason is what it printed). Then the PR body says "voicescore: not run (<reason>)" and the reviewer gets no labels.
- Otherwise add each paragraph's `label` to its entry, marked "voicescore hint", and keep the `summary` line for the PR body, such as "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p96)".
- Never block, rewrite or skip a paragraph because of its voicescore. Only the reviewer's flags lead to a rewrite.

1. List only the prose paragraphs this section drafted, from the `draft: prose for <id>` commit. The word list the reviewer lints with is `${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`; give it that path, and do not copy the words into the list or into your own drafting. Leave out the bullets, table rows and headings section 3 wrote, even though the commit holds them. For each paragraph give a number, the page path, its voice type from house-voice's table, and the paragraph's text. Run `git status --porcelain` and keep the output.
2. Dispatch the `planner:voice-reviewer` subagent with the Agent tool, and give it the list. If the Agent tool lists no `planner:voice-reviewer`, dispatch a general-purpose subagent instead, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter as its instructions, then the list, then this: you must not change any file, and you must report any file you changed. Never review the drafts yourself in this conversation. If no subagent can be dispatched, write "**Voice review:** not run: <the reason>" in the PR body and go on to the part "Harvest the owner's edits". The harvest does not depend on the review.
3. Run `git status --porcelain` again. If the output differs from step 1 of this part, the reviewer changed a file: stop and show the user. If the reviewer errored, or returned anything but the table, treat the review as not run, write "**Voice review:** not run: <the reason>" in the PR body, and go on to the part "Harvest the owner's edits". If it flagged no paragraph, skip steps 4 and 5 of this part: there is nothing to rewrite and no commit, so go on to the part "Harvest the owner's edits".
4. Rewrite each paragraph the reviewer flags once, in the working tree, from what it says differs. The reviewer may also name a sentence as redundant, because its claim stands elsewhere in the paragraph. Drop only a sentence it named, in the rewrite of that paragraph, and keep its exact text for step 5. Do not send the rewrite back for review. A paragraph it did not flag stays as drafted. Note the pages you rewrote. Touch no other file. Before you rewrite a page, check it holds no uncommitted edit from sections 2 and 3, because a restore would discard that edit. For each `<page>`:

   ```
   git diff --quiet HEAD -- <page> || { git add -- <page> && git commit -qm "Checkpoint <id>" -- <page>; }
   ```

   This commits that page alone, with the message `Checkpoint <id>`, when it differs from HEAD. Then rewrite it, so `git restore -- <page>` returns the page to a state that already holds those edits.
5. Check only the pages you rewrote, one at a time, because the working tree also holds the work of sections 2 and 3 that is not committed. For each rewritten `<page>`:

   ```
   tmp=$(mktemp)
   git show HEAD:<page> > "$tmp"
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)
   ```

   voicecheck fails if a rewrite lost, added or moved a wikilink, code span, date, ID, number (with its units or currency), table cell, version, frontmatter line or negation.

   For a page where the rewrite dropped sentences the reviewer named as redundant, add `--redundant "<the sentence exactly as it stood>"` for each: `planner voicecheck "$tmp" <page> --redundant "<sentence>"`. voicecheck then lets that sentence's own negation go, still fails if the sentence carried an ID, number, date or link that is now gone, and exits 2 if the sentence was not in the draft or is still in the rewrite. The PR body lists every such sentence under **Voice review**.
   - Exit 0: keep the rewrite.
   - Exit 1: run `git restore -- <page>`. That discards every rewrite on that page and keeps its earlier draft whole. Run it for no other file.
   - Exit 2: show the error, then run `git restore -- <page>` so the unchecked rewrite stays out of the work that section 7 stages. Never commit a rewrite voicecheck could not check.

   Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`, staging each page by exact path.

### Harvest the owner's edits

Only the vault's owner harvests, and only their own edits. The owner is the `author` of the `source: owner` examples in `voice/examples/` and `voice/local/`. If there are none, say "No owner examples yet, so nothing to harvest. `/planner:voice-seed` adds them." and go on to section 5, Read back decided wording. Harvest does not depend on the voice review: run it even when the review did not run.

Each command runs in its own shell call, and no shell variable survives from one call to the next. So each paragraph's text is kept in a file with a fixed path every later step names: `.planner/harvest/<pr>-<n>.txt`, where `<pr>` is the PR number and `<n>` is the paragraph's order in this harvest, from 1. It sits in `.planner/`, which is gitignored, so it never shows in `git status` and is never staged. When harvest ends, by any route, run `rm -rf .planner/harvest`.

Every `gh` or `git` call below can fail. When one does, say which call failed and what it left unchecked. Never read a failure as "no edits found". Say "no edits found" only when every merged PR was checked.

1. Get the user's handle with `gh api user -q .login`. If `gh` fails, say "gh could not read your handle, so nothing was harvested." and go on to section 5, Read back decided wording. If the handle is not the owner's handle without the `@`, say "Harvest is owner-only." and go on to section 5, Read back decided wording.
2. List the user's merged session PRs: `gh pr list --state merged --search "head:session/" --author @me --json number,headRefName --limit 10`. If `gh` fails, say "gh could not list merged PRs, so nothing was harvested." and go on to section 5, Read back decided wording. If it returns 10 PRs, say "10 merged PRs came back, so older PRs were not checked."
3. Take one PR at a time, because `FETCH_HEAD` holds only the last fetch. Run `gh pr view <number> --json commits`, which lists each commit's `oid`, `messageHeadline` and `messageBody`, and `git fetch origin pull/<number>/head`. If `gh` fails, say "gh could not read the commits of PR <number>, so its edits were not checked." and go to the next PR. If the fetch fails, say "git could not fetch PR <number>, so it was not checked." and go to the next PR. Then:
   - Keep the commits whose `messageHeadline` starts `draft: `, both `draft: prose for` and `draft: voice rewrite for`. Skip the PR if there are none.
   - For each, list its pages with `git diff-tree --no-commit-id --name-only -r <oid>`. For each page, the baseline is the last draft commit in the PR's list that touched it.
4. For each page of the PR:
   - Run `git log --format=%H <baseline>..FETCH_HEAD -- <page>` and keep the commits that are in the PR's list. Drop each one whose `messageHeadline` starts with `draft: `, `Checkpoint ` or `Close session `, and each one whose `messageBody` carries a `Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer. Those are the skill's own commits. Drop a merge commit too. If none remain, the owner did not edit the page, so skip it.
   - For each remaining commit, run `git diff -U0 <oid>^ <oid> -- <page>`. Never compare the baseline with the tip, because the tip also holds section 3's content. The added lines are the owner's edit. Find the paragraph of `git show FETCH_HEAD:<page>` that holds them. If a later commit removed them, skip. The draft paragraph is the one in its place in `git show <oid>^:<page>`. Read the merged text from `FETCH_HEAD`, never from `origin/main`.
   - Extract the merged paragraph into its file, and hash it, in one call:

     ```
     mkdir -p .planner/harvest
     git show FETCH_HEAD:<page> | sed -n '<first>,<last>p' > .planner/harvest/<pr>-<n>.txt
     shasum < .planner/harvest/<pr>-<n>.txt | cut -c1-12
     ```

   - Skip a paragraph that is already saved or declined, and run `rm -f .planner/harvest/<pr>-<n>.txt`. It is saved when an example in either folder has the same `page`, a `harvested_from` equal to the baseline's full hash, and a body equal to the merged paragraph. It is declined when `grep -rh '^Harvest declined: ' sessions/` has its line: `Harvest declined: PR <number> <page> <hash>`.
5. Offer each remaining paragraph, one at a time. Show the draft paragraph, the file `.planner/harvest/<pr>-<n>.txt` and the voice type from house-voice's table, so the text is never retyped. Harvest offers and never saves by itself. Ask "Did you write this change?" The owner's answer is the check that the edit is theirs. If the answer is unclear, ask once more. If it is no, or still unclear, record a decline, run `rm -f .planner/harvest/<pr>-<n>.txt`, and do not ask the save question. Otherwise ask "Save the merged paragraph as a <type> example?" Save it only on an explicit yes. On any other answer, record a decline and run `rm -f .planner/harvest/<pr>-<n>.txt`. To record a decline, insert one bare line `Harvest declined: PR <number> <page> <hash>` directly under `## Captures` in the session record. It is never a bullet.
6. Ask where it goes, and say plainly that a committed example is pushed in this PR, where everyone with access to the repository can read it:
   - committed: `voice/examples/<type>/`. Ask "May this text be committed to the vault?" and wait for an explicit yes.
   - local only: `voice/local/<type>/`. It stays on this machine and no step below stages it.

   If the owner's employer owns the text, or the owner is not sure, recommend local only. If the answer is not an explicit choice, do not save, and run `rm -f .planner/harvest/<pr>-<n>.txt`.
7. Plan the room before you save, and change no example yet. A type keeps at most 5 active examples. Count both folders together, with the new one. If that makes 6, plan to retire one: the oldest `public-seed` example first, then the oldest `owner-edit`, then the oldest `owner`, by `added` and then file name. A local example never retires a committed seed, and in a local-only save only local examples may retire. If the cap blocks a local-only save, store nothing, run `rm -f .planner/harvest/<pr>-<n>.txt`, and say "The cap blocks a local save: <type> holds 5 active examples and none in voice/local/ may retire." Show the owner each planned retirement and ask. If they refuse, store nothing for that type, and run `rm -f .planner/harvest/<pr>-<n>.txt`.
8. Save the merged paragraph word for word as `<folder>/<type>/VX-<type>-NNN.md`, NNN one higher than the highest in that type in both folders, retired files included. First write the frontmatter with the Write tool, quoting every free value, ending with the closing `---` and one blank line:

   ```
   ---
   id: VX-<type>-NNN
   voice_type: <type>
   source: owner-edit
   author: "@<handle>"
   page: '<page path>'
   harvested_from: '<full hash of the baseline draft commit>'
   state: active
   added: <today>
   ---

   ```

   Then append the paragraph's file and compare it with the stored body, with a tool, in one call. The block removes the file whatever `cmp` finds:

   ```
   cat .planner/harvest/<pr>-<n>.txt >> <file>
   awk 'body { if (first && $0 == "") { first = 0; next } first = 0; print; next } $0 == "---" && ++n == 2 { body = 1; first = 1 }' <file> | cmp - .planner/harvest/<pr>-<n>.txt; code=$?; rm -f .planner/harvest/<pr>-<n>.txt; (exit $code)
   ```

   If `cmp` reports a difference, stop, tell the owner, and do not repair the file. Then re-read the frontmatter and confirm it parses as YAML and that `page` and `harvested_from` hold the text you gave. Only now apply the retirements you planned in step 7, changing only each `state:` line. If the save made a folder's active `owner` and `owner-edit` examples of the type 2 or more, retire that folder's active `public-seed` examples of the type the same way, as `/planner:voice-seed` does. A local save retires only local seeds. Retire by editing `state:` and never delete an example.

## 5. Read back decided wording

For each item that became `decided` in this session, show its final wording. If its owner is present, they confirm it. If not, list it in the PR body for them.

## 6. Render and check

First bring in `main` if it moved since the branch was made, so render and check see what will merge:

1. Run `git fetch origin`. If it fails, say the branch was not compared with `main`, and go on to the render below.
2. Run `git merge-base --is-ancestor origin/main HEAD`. Exit 0: `main` has not moved, so go on to the render. Exit 1: go on to step 3. Any other exit: show the error, say the branch was not compared with `main`, and go on.
3. A merge refuses to run over uncommitted edits, so commit them first. Stage every changed tracked file and the session record by exact path, never `git add -A`, and commit with the message `Checkpoint <id>`.
4. Run `git merge --no-edit origin/main`. If it exits 0, go on to the render.
5. On a conflict, list the files with `git diff --name-only --diff-filter=U` and read each conflict hunk (`<<<<<<<` to `>>>>>>>`). If any hunk sits outside a `<!-- generated:` block, stop: run `git merge --abort`, show those files and lines, and leave the merge for the user.
6. If every hunk sits inside a generated block, render rebuilds those blocks, so the side does not matter. Run `git merge --abort`, then `git merge --no-edit -X ours origin/main`. `-X ours` decides only the conflicting hunks, so every edit that merged cleanly, on either side, is kept. Never use `git checkout --ours` or `--theirs` on a file: that takes one side of the whole file and drops the other side's edits.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render`, then `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check`. Fix each W326 at once: set the page's `state` as the warning says, because a page whose rows have moved on but whose own state has not reads as unsettled to everyone. For a session whose `modes` include `shape`, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check --gate shape` as well: each W806 is a question still `assumed`, so list it under **Questions** in the PR body. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --open --digest` and keep its first line, the coverage, for the PR body.

Two warnings point at questions the ledger cannot see, so tell the lead about each one in plain words (never the code), and not only in the PR body. These count among the few items section 2 allows you to ask about:

- W809 is possibly an untyped subject: a fact names points, a clause, a licence or another word an existence question lists, and the page holds or links no subject of that kind. For each one, offer to type the subject, as "Type the subjects Dump named" says, with the facts the user gives, or to answer the existence question in the ledger.
- W804 is a ledger row that is orphaned (its subject is gone), no longer owed (its subject no longer matches the trigger), or a wildcard that covers nothing because other rows shadow it or no copy matches. For each one, offer to fix the row, such as renaming its copy to the subject's new ID, or to leave it as a record. Never delete it without the user's yes.

Carry each one into the PR body's **Questions** line with what the user chose. Fix each error with the user. An E321 or E322 is an override the check cannot read: fix its grammar, never delete it. A W303, W304, W316, W317, W318 or W324 is an override doing its job: list it under **Overrides**, and do not remove the bullet to quiet it. Never delete a ledger row to quiet the check: fix its grammar or change its state with the user. If the user leaves an error in place, put it in the PR body. CI will block the merge until it is fixed.

## 7. Finish the record

Stage every file `planner render` reported, every example harvested or retired in `voice/examples/`, plus the session record and the changed pages, by exact path. Never stage anything in `voice/local/`. Never use `git add -A`. Before pushing, `git status --short` must show nothing modified. A rewritten block left out of the commit fails CI's render check. Write a one-line `summary:` yourself, in plain words, and mention it in your closing message. Set `status: closed`, then stage. Commit with the message `Close session <id>`.

If this session set `handed_off:` on an app page, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner handoff <APP-id>` only now, after that commit, so the manifest records a clean commit and not "with uncommitted changes". It writes `handoffs/<APP-id>.md`, the record of what the senior accepts. If the manifest already exists, the senior is accepting changes: run it with `--replace` only once they say so in this session. Then commit the manifest alone, by exact path, with the message `Handoff manifest for <APP-id>`.

Before you push, ask the one confirmation the section "Starting a close" describes, unless the lead has already said "push" or "open the PR". Run `git push -u origin session/<id>`. For a session whose `modes` include `answer`, push to the challenge's branch instead: `git push origin <branch>`. If the push fails, say in a sentence what failed, give the branch name and the one command that would retry it, and stop. Do not open a PR for a branch that is not pushed.

## 8. Open the PR

For a session whose `modes` include `answer`, do not open a new PR: the answer belongs in the challenge's PR. Find it with `gh pr list --head <branch> --state open --json number,url`. Write the body below to a temporary file, and in its **Check:** line add "E316 for <ID> should now be gone." If check still reports E316 for that item, say so in its place. Run `gh pr comment <number> --body-file <file>`, and skip the rest of this section. If `gh` fails, say so, print the exact command, and stop. Never say the comment exists unless `gh` printed its URL.

Collect the reviewers:

- the `owner:` of each app page this session changed;
- the `owner:` of each consumer app of a contract this session changed.

Get the user's own handle with `gh api user -q .login`. Strip the leading `@` from each individual handle. A team handle `@org/team` is passed as `org/team`. Drop the user's own handle. If nobody remains, leave out `--reviewer`.

Write the PR body to a temporary file. Fill the headings of the vault's PR template:

- **What changed.** The promoted items, each with its new state. Then these lists, each with "none" when empty:
  - **Prose drafted:** each prose paragraph drafted in section 4, page by page, and each merged paragraph rewritten whole, with the page and a pointer to `## Replaced prose` in the session record.
  - **House voice:** each "No examples for <type>: drafted without examples" line house-voice gave, one per type, or "none".
  - **Voice review:** each paragraph the reviewer flagged, what it said, and whether it was rewritten or kept because voicecheck named a changed token; each sentence dropped as redundant, quoted, with the reviewer named as the one who asked and the sentence that already says it; or "not run: <reason>". Then the voicescore `summary` line, or "voicescore: not run (<reason>)".
  - **Voice examples:** each example harvested or retired. Name a local example only as a count, never by its text. Add each PR harvest could not check, and why, and say when the PR limit hid older PRs.
  - **Decided wording not yet read back:** each `decided` item whose owner was not present in section 5.
  - **Promoted on a nod:** every item kept or promoted from a capture whose origin starts with `claude`, not only the deciding capture, with the capture quoted.
  - **Overrides:** every `**Override:**` bullet this session wrote, with its item, rules and reason, and every item decided on an owner's behalf that is not yet confirmed, with the owner @-mentioned so they can confirm or raise `/planner:challenge`. Or "none".
  - **Changed contracts:** each contract, and for each consumer, who was asked: present, async, in this PR, or "not consulted: <reason>".
  - **Overdue unknowns:** each `W705` line from section 6, with its owner @-mentioned.
  - **Questions:** the coverage line from section 6, each ledger row this session wrote with its state, each W806 from the shape gate, each item decided with a question open (W807), each subject typed with the copies it now owes, each left untyped with its unknown, and each W809 and W804 from section 6 with what the user chose. Never write that the questions are complete.
  - **Reviews:** each checkpoint's `**Coverage:**` line from `## Reviews`, word for word, with its dropped findings and their reasons; or "none: no checkpoint ran". An area that did not run is listed with its reason, never left out.
  - **Catalogue proposals:** each entry the user approved, and each entry `--stats` names as one to prune or tighten; or "none".
  - **May still say the old value:** for each `decided` or `fact` value this session changed, run `grep -rn -F "<old wording>" --include='*.md' . | grep -v '^./sessions/'` and list every hit.
  - **Check:** the first line of the check output, and any error left in place.
  - **Stage:** run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner ladder` and copy each line whose `pages reach` is later than its `stage`, word for word; or "none". This is a line in the report, never a question: the lead types `stage` on the app page when they choose, in this session or a later one.
- **Minutes.** Work it out from the session's commits: `git log --format=%ct <main>..HEAD` gives the first and last commit times. Write "about <n> minutes (from the commit log)", and if there is only one commit, write "not recorded". Never ask.
- **Structural fixes** and **Prose edits.** Write "Filled in by the reviewer."

Then run the command below, with one `--reviewer` per remaining reviewer (none, if nobody remains). `<Mode name>` is the display name in `MODES.md`.

```
gh pr create --base main --head session/<id> --title "<date> <Mode name>: <topic>" --body-file <file> --reviewer <handle> --reviewer <org/team>
```

If `gh` fails, write the body to `.planner/pr-body.md` (it is not committed) and say one sentence: "The branch is pushed; I couldn't open the pull request from here. The text is in `.planner/pr-body.md`." Never say a PR exists unless `gh` printed its URL. Show the URL. If this session wrote `handed_off: "<senior>, <date>, PR pending"`, replace `pending` with `#<the PR's number>`, commit it as `Handoff PR number for <APP-id>`, and push. If `gh` failed, leave `pending`: W325 says so until someone writes the number.

## What you tell the lead at the end

Three to six plain sentences: what was filed, by group and in the lead's words; what is waiting on someone, with the date; and the pull request link, or why there is none. No capture number, copy ID, finding ID or check code, and no list of what a tool did or did not install. The pull request body is the reviewer's record; the lead does not need to read it. For a switch, end with the one line that starts the next mode.

## 9. Rebuild the explorer

This is the last step of every close. Run it even when section 8 stopped because `gh` or the push failed, since the explorer needs neither. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner explore` from the vault root, without `--serve`, as a command of its own: never pipe it, because a pipe hides its exit status. Read the exit status before you say anything about the result. It rewrites `dashboard.html` at the vault root, the page colleagues open from git or OneDrive, and takes about a second. A reader's copy has no git: nothing is committed, and the rebuilt page shows the reader's drafts.

In an owner's vault, when `git status --short -- dashboard.html` shows it changed:

- **With a session branch** (section 7 ran), commit only that file by exact path with the message `Rebuild dashboard`, and push the branch if section 7 pushed it.
- **With no session** (section 1 found none, so you are on `main`), do not commit to `main` and do not push. Say: "The dashboard is rebuilt in your folder but not committed, because no session is open. It goes in with the next close, or I can put it on its own branch for a pull request." On a yes, create `dashboard/<today>`, commit only `dashboard.html` by exact path, push it after the same confirmation section 7 asks, and open the pull request as section 8 does.

- If it exits 0, say one plain line: "The dashboard is up to date: dashboard.html — open it, or run /planner:explore to ask Claude from it". Then add one line for each `warning:` and each `no design doc found` it printed, in its own words, such as a `team_repos:` folder that does not exist. Do not read the rest of its output back.
- If it fails, say so plainly with its message: "The explorer could not be built: <message>. The close itself is done." A failed build never undoes or blocks the close, and you never say the dashboard is up to date unless the command exited 0.
