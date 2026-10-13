# Subjects, the question ledger and catalogue gaps

Read by close in section 3, after the promoted items are written and before the marks. Section numbers below are the sections of `SKILL.md`.

### Type the subjects Dump named

A kept capture that says `type at close: PTY` or `type at close: SV` names a subject the lead said exists, in this session or an earlier one. Write it on `03-context-and-scope.md`: a party as `### PTY-nn <name>` under `## Outside parties`, stored value as `### SV-nn <name>` under `## Value held for customers`, adding the section if the page lacks it, with the next free ID as above. Fill each required fact from what the user said, in the captures or in this turn, and ask for any the user did not give. Never fill a fact from general knowledge, and never guess one. A missing fact is E808.

- A party: `**Relationship:**` is `partner`, `supplier`, `regulator` or `customer group`. `**Agreements:**` lists the agreements, with their `SRC-nn`, or says `none known`.
- Stored value: `**Holder:**` is a link to the app or party that holds the balances, or its name. `**Owner:**` is who carries them, or `not known yet, see [[11-unknowns-and-risks#UNK-nnn <name>|UNK-nnn]]`, with that unknown written as section 2 says. Only `**Owner:**` may say `not known yet`.
- If nobody knows a party's relationship or a stored value's holder, write an unknown that asks, with an owner and an ask-by date, and leave the subject untyped. Mark its capture as a keep to that unknown, as section 2 says, and list it under **Questions** in the PR body.

Then record the yes. Dump starts the capture with the existence question's copy ID, such as `Q-FIN-01@INI-001: yes, ... type at close: SV`. Write that copy's row in the ledger as the next part says: `answered`, `item:` linking the new subject, `answer:` the lead's yes in one line, and `source:` by the source rule there, which means a first-hand `SRC-nn` when the lead's word is the only source. If the subject stays untyped, the row is `unknown`, linking the unknown that asks for its relationship or holder: the yes is said, and the subject waits for that answer. If the copy already has a row, an earlier session recorded the yes, so write no second row. Add the `## Changes` row for the copy, citing the capture.

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
