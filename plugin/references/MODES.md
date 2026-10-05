# Modes

Each mode skill holds only what is particular to it. This table is what every mode shares: when it ends, what Claude must do, and what it must not. The eval cases grade the last column.

| Mode | Ends when | Claude must | Claude must not |
|---|---|---|---|
| Dump & Diverge (`dump`) | the user stops, or after the pre-mortem and at most 2 gentle prompts | build on each idea; label its own ideas `(claude)` and its wild ones `[wild]` | push back, judge, or write to any page before close |
| Discover (`discover`) | every ranked source is read and the user has corrected "here's what I think exists" | show its reading as a numbered list before writing anything; cite a `SRC-nn` for every fact | state anything from general knowledge as a fact, or copy document text into the vault |
| Shape (`shape`) | the user picks an option, or rejects them all | offer 2 or 3 options with trade-offs; record each rejected one with its reason | offer one option or more than three; write `decided` |
| Grill (`grill`) | the agenda is empty, or the user stops | ask one question at a time with a recommended answer; keep the recommendation under pushback until the user gives a reason | answer its own questions, decide without the owner, or batch writes |
| Epics (`epics`) | every chosen team's gaps are closed or listed, or the user stops | read the `traceability` block; offer 2 or 3 cuts; draft criteria at a contract or flow boundary; ask for an explicit yes per criterion, then a read-back; run `check --gate epics` | write a requirement into an epic, name a component or technology in a criterion, or write `decided` without a yes on every criterion |
| Requirements (`requirements`) | every requirement branch is closed or is an unknown | stay at the "what"; write at most `assumption` | write `decided` or `fact`, or write under `docs/requirements/` |
| Challenge (`challenge`) | the challenge is an open unknown and its PR is open, or the senior stops | quote the senior's words; write one open unknown the senior owns that blocks the item, and one `**Dissent:**` line on the item | change the item's state or text, decide anything, or argue the item's side |
| Answer (`answer`) | the challenged item is decided again, set back, or its unknown resolved, or the lead stops | work on the challenge's own branch; decide only inside a Grill part, with `grill` added to `modes` | open a second PR, or decide anything outside a Grill |

## Who writes what, and when

| Mode | During the session | At close |
|---|---|---|
| `dump` | captures only | promoted items at `inkling`, unknowns with owner and ask-by |
| `discover` | `sources.md` rows; facts after each correction round, with sources | prose |
| `shape` | captures only | `assumption` items with `**Options considered:**` |
| `grill` | each decided item as its branch closes, with a checkpoint commit | prose, read-back |
| `epics` | `draft` epic pages, bullets and criteria only; `decided` only inside its Grill part | epic description paragraphs |
| `requirements` | requirements on the capability page at `assumption`; unknowns | prose |
| `challenge` | the unknown and the `**Dissent:**` line, then its own PR | nothing: a challenge closes its own record |
| `answer` | what its Grill decides, or the item set back, on the challenge's branch | a push to that branch and a comment on the challenge PR, never a new PR |

No mode writes inside a generated block. `planner render` fills them. Close runs it, and so does `epics`, mid-session, to read its frontier. Whoever runs it stages every file it reports, by exact path.

## Where to start

`planner next` names the one app and mode to work on next, and `planner status` shows every app's stage, certainty mix and oldest open unknown. START runs `planner next`. Both follow the rules in `CONVENTIONS.md` under "Progress and next step".

## Unknowns

Any question nobody present can answer becomes an unknown on `11-unknowns-and-risks.md`, with `**Owner:**` starting with a handle, `**Ask by:**` and `**Blocks:**`. Offer two ways forward: an ask with that owner and date, or a research task Claude does with a source. There is no separate Probe skill.

When two sources or two people disagree, write an unknown that names both. Do not pick one.

## Gentle prompts

After the main work of a mode, Claude may raise at most two questions nobody asked, drawn from the ladder table in `CONVENTIONS.md` and the eight concern pages. For example: "Nobody has mentioned data migration. Is there one?" A dump raises none until after its pre-mortem.
