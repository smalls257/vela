# Modes

Each mode skill holds only what is particular to it. This table is what every mode shares: when it ends, what Claude must do, and what it must not. The eval cases grade the last column. Each "must not" is the default when nobody says otherwise. The user may override any of them, and Claude then records the override as `START.md` says under "The user may override any rule".

| Mode | Ends when | Claude must | Claude must not |
|---|---|---|---|
| Dump & Diverge (`dump`) | the user stops, or after the pre-mortem and its review checkpoint | build on each idea; label its own ideas `(claude)` and its wild ones `[wild]` | push back, judge, or write to any page before close |
| Discover (`discover`) | every ranked source is read and the user has corrected "here's what I think exists" | show its reading as a numbered list before writing anything; cite a `SRC-nn` for every fact | state anything from general knowledge as a fact, or copy document text into the vault |
| Shape (`shape`) | the user picks an option, or rejects them all | offer 2 or 3 options with trade-offs; record each rejected one with its reason | offer one option or more than three; write `decided` |
| Boundary (`boundary`) | every app of the picked cut has its sheet written or its open lines listed, or the user stops | offer 2 or 3 cuts into apps; read back one sheet per app as a numbered list and write only the lines with an explicit yes; label each line with what it rests on | write `decided` or a concern cell as `addressed`, offer one cut or more than three, or write a line nobody said yes to |
| Grill (`grill`) | the agenda is empty, or the user stops | ask one question at a time with a recommended answer; keep the recommendation under pushback until the user gives a reason | answer its own questions, decide without the owner unless the user decides on the owner's behalf, or batch writes |
| Epics (`epics`) | every chosen team's gaps are closed or listed, or the user stops | read the `traceability` block; offer 2 or 3 cuts; draft criteria at a contract or flow boundary; ask for an explicit yes per criterion, then a read-back; run `check --gate epics` | write a requirement into an epic, name a component or technology in a criterion, or write `decided` without a yes on every criterion |
| Requirements (`requirements`) | every requirement branch is closed or is an unknown | stay at the "what"; write at most `assumption` | write `decided` or `fact`, or write under `docs/requirements/` |
| Challenge (`challenge`) | the challenge is an open unknown and its PR is open, or the senior stops | quote the senior's words; write one open unknown the senior owns that blocks the item, and one `**Dissent:**` line on the item | change the item's state or text, decide anything, or argue the item's side |
| Answer (`answer`) | the challenged item is decided again, set back, or its unknown resolved, or the lead stops | work on the challenge's own branch; decide only inside a Grill part, with `grill` added to `modes` | open a second PR, or decide anything outside a Grill |

## Who writes what, and when

| Mode | During the session | At close |
|---|---|---|
| `dump` | captures only, and the `## Reviews` of its checkpoint | promoted items at `inkling`, unknowns with owner and ask-by, question ledger rows |
| `discover` | `sources.md` rows; facts after each correction round, with sources, and the parties and stored value they name | prose, question ledger rows |
| `shape` | captures only, and the `## Reviews` of its checkpoint | `assumption` items with `**Options considered:**`, question ledger rows |
| `boundary` | the picked cut's `**Options considered:**`; then, after each sheet's yeses, the app page, its containers and contracts, its runtime page and concern cells, all at `assumption`, with a checkpoint commit | prose, question ledger rows |
| `grill` | each decided item as its branch closes, with a checkpoint commit | prose, read-back, question ledger rows |
| `epics` | `draft` epic pages, bullets and criteria only; `decided` only inside its Grill part | epic description paragraphs |
| `requirements` | requirements on the capability page at `assumption`; unknowns | prose |
| `challenge` | the unknown and the `**Dissent:**` line, then its own PR | nothing: a challenge closes its own record |
| `answer` | what its Grill decides, or the item set back, on the challenge's branch | a push to that branch and a comment on the challenge PR, never a new PR |

No mode writes inside a generated block. `planner render` fills them. Close runs it, and so does `epics`, mid-session, to read its frontier. Whoever runs it stages every file it reports, by exact path.

## Where to start

`planner next` names the one app and mode to work on next, and `planner status` shows every app's stage, certainty mix and oldest open unknown. START runs `planner next`. While no app page exists, it suggests a Dump or a Discover, or a Boundary once `04-solution-strategy.md` is `decided`. Both follow the rules in `CONVENTIONS.md` under "Progress and next step".

## Unknowns

Any question nobody present can answer becomes an unknown on `11-unknowns-and-risks.md`, with `**Owner:**` starting with a handle, `**Ask by:**` and `**Blocks:**`. Offer two ways forward: an ask with that owner and date, or a research task Claude does with a source. There is no separate Probe skill.

When two sources or two people disagree, write an unknown that names both. Do not pick one.

## Owed questions

What a session must ask comes from code, not from this file. `planner questions` lists the copies the question catalogue owes, and a review checkpoint adds what one focused reviewer per focus area finds, as `REVIEW.md` says. Dump runs one after its pre-mortem, Discover after its read-back, Shape before it shows its options, and a Grill on its agenda. There is no cap on questions and no quota: the digest ranks them, the lead takes what they want, and the rest stay open and visible in the ledger. Between checkpoints, ask whatever the work needs.
