# Modes

Each mode skill holds only what is particular to it. This table is what every mode shares: when it ends, what Claude must do, and what it must not. The eval cases grade the last column.

| Mode | Ends when | Claude must | Claude must not |
|---|---|---|---|
| Dump & Diverge (`dump`) | the user stops, or after the pre-mortem and at most 2 gentle prompts | build on each idea; label its own ideas `(claude)` and its wild ones `[wild]` | push back, judge, or write to any page before close |
| Discover (`discover`) | every ranked source is read and the user has corrected "here's what I think exists" | show its reading as a numbered list before writing anything; cite a `SRC-nn` for every fact | state anything from general knowledge as a fact, or copy document text into the vault |
| Shape (`shape`) | the user picks an option, or rejects them all | offer 2 or 3 options with trade-offs; record each rejected one with its reason | offer one option or more than three; write `decided` |
| Grill (`grill`) | the agenda is empty, or the user stops | ask one question at a time with a recommended answer; keep the recommendation under pushback until the user gives a reason | answer its own questions, decide without the owner, or batch writes |
| Requirements (`requirements`) | every requirement branch is closed or is an unknown | stay at the "what"; write at most `assumption` | write `decided` or `fact`, or write under `docs/requirements/` |

## Who writes what, and when

| Mode | During the session | At close |
|---|---|---|
| `dump` | captures only | promoted items at `inkling`, unknowns with owner and ask-by |
| `discover` | `sources.md` rows; facts after each correction round, with sources | prose |
| `shape` | captures only | `assumption` items with "Options considered" |
| `grill` | each decided item as its branch closes, with a checkpoint commit | prose, read-back |
| `requirements` | requirements on the capability page at `assumption`; unknowns | prose |

No mode writes inside a generated block. Close runs `planner render` for those.

## Unknowns

Any question nobody present can answer becomes an unknown on `11-unknowns-and-risks.md`, with `**Owner:**` starting with a handle, `**Ask by:**` and `**Blocks:**`. Offer two ways forward: an ask with that owner and date, or a research task Claude does with a source. There is no separate Probe skill.

When two sources or two people disagree, write an unknown that names both. Do not pick one.

## Gentle prompts

After the main work of a mode, Claude may raise at most two questions nobody asked, drawn from the ladder table in `CONVENTIONS.md` and the eight concern pages. For example: "Nobody has mentioned data migration. Is there one?" A dump raises none until after its pre-mortem.
