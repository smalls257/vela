# Conventions

This file is the vault's one written format. Every page follows it, and `planner check` enforces the parts a script can see. If a rule here and the check disagree, the check has a bug. Search this file for any field, label or code to find the rule behind it.

## Layout

One vault holds one initiative. Pages are numbered by arc42 section.

| Path | What it holds |
|---|---|
| `README.md` | Home page: layout, reading paths, setup checklist |
| `CLAUDE.md` | How Claude answers questions from this vault. A person writes it. |
| `.planner.yaml` | `initiative` (`INI-nnn`) and `title` |
| `01-goals.md` | Goals table and the `where-it-stands` block |
| `02-constraints.md` | Constraints table, `CST-n` |
| `03-context-and-scope.md` | Systems today and after; apps in and out of scope |
| `04-solution-strategy.md`, `04a-capability-delta.md` | The core move; links to every capability that changes |
| `05-building-blocks/` | Index with the `context-map` block, then `<app>-building-blocks.md` per app, with its contracts |
| `06-runtime/` | `06-flows.md`, `flows/FLO-nnn-<slug>.md`, `apps/<app>-runtime.md` |
| `08-concerns/` | `08-concerns.md` with the `concern-matrix` block, then `concern-<name>.md` |
| `09-decisions/` | Index, then `ADR-nnnn-<slug>.md` |
| `11-unknowns-and-risks.md` | Every unknown and risk, and the `unknowns-index` block |
| `12-glossary.md` | Terms |
| `13-epics/` | Index, then `EPC-nnn-<slug>.md` |
| `capabilities/` | `CAP-nnn-<slug>.md` per capability touched |
| `sources.md` | The source register, `SRC-nn` |
| `sessions/` | One record per session, `YYYY-MM-DD-<topic>.md` |
| `voice/examples/` | House-voice passages. Never a source. `voice/corpus/` is gitignored. |
| `.inbox/` | Documents dropped for Discover. Gitignored, never parsed. |

`planner check` reads every `.md` file except `CLAUDE.md`, `CONVENTIONS.md`, anything under `voice/`, and anything under a folder whose name starts with a dot.

## Areas and stages

An area is an app whose `change` is `new` or `changed`, or one of `initiative`, `capabilities`, `concern-<name>` and `epics`. Only apps move through stages. The initiative is at Frame while no app has a stage. Frame is never typed.

`stage` sits on the app's building-blocks page and means "in this stage now". It is typed by hand. The `where-it-stands` block shows counts beside it, so a stage the counts contradict is easy to see. Apps whose `change` is `integrated`, `unchanged` or `retired` sit outside the ladder and take no `stage`.

The ladder checklist. Before typing a stage, check its entry list:

| Stage | Enter when |
|---|---|
| `baseline` | The app is named as in scope. Nothing else. |
| `target` | The app page cites at least one source that is not a dump. |
| `boundaries` | Every flow that names the app is at `assumption` or higher. |
| `contracts` | The app page is `decided`: what it does and what it does not do. Its containers table exists. |
| `handoff` | Every contract it provides is `decided`, or `fact` when unchanged. Every contract it consumes is `decided` or `fact`. Its runtime page says how it behaves on failure. No open unknown blocks one of its contracts. |
| `epics` | It has no `unexamined` cell. Every container is `confirmed`, `unchanged` or `retired`. |

## Frontmatter

Every page starts with a YAML block. Quote any value that holds a colon or starts with `@`.

| `type` | Required fields | Optional fields | `state` values |
|---|---|---|---|
| `index` | `id`, `type`, `title`, `authored` | `initiative`, `arc42`, `c4`, `owner`, `sources` | none |
| `initiative-section` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `c4`, `sources` | `inkling`, `assumption`, `fact`, `decided` |
| `app-building-blocks` | as above, plus `change` | `stage`, `initiative`, `arc42`, `c4`, `sources`, `handed_off` | `inkling`, `assumption`, `fact`, `decided` |
| `app-runtime` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `inkling`, `assumption`, `fact`, `decided` |
| `flow` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `inkling`, `assumption`, `fact`, `decided` |
| `concern` | `id`, `type`, `title`, `owner`, `authored` | `initiative`, `arc42`, `sources` | none: the cells hold the states |
| `decision` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `proposed`, `decided`, `superseded`, `rejected` |
| `epic` | as above, plus `apps`, `delivers` | `consumes`, `flows`, `depends_on`, `initiative`, `sources` | `draft`, `decided` |
| `capability` | as above, plus `origin`, `change` | `sources`, `domain` | `inkling`, `assumption`, `decided` |
| `session` | `id`, `type`, `date`, `modes`, `status`, `summary` | `title` | none: `status` is `open` or `closed` |
| `sources` | `id`, `type`, `title`, `authored` | `owner` | none |

Field values:

- `authored`: `authored` (people wrote it), `generated` (only blocks), `mixed` (both).
- `owner`: a GitHub handle or team, `"@handle"` or `"@org/team"`. Several owners are separated by spaces, as in CODEOWNERS. Close uses it to request reviews and to mention owners.
- `initiative`: if present, it must equal `.planner.yaml`.
- `c4`: `landscape`, `context` or `container`. `arc42`: the section, for example `"§5"`.
- `sources`: a list. Use `SRC-nn` IDs for documents. Free text, such as a session name, is allowed as a summary.
- `change` on an app page: `new`, `changed`, `integrated`, `unchanged` or `retired`.
- `stage`: `baseline`, `target`, `boundaries`, `contracts`, `handoff`, `epics`. Required when `change` is `new` or `changed`, absent otherwise.
- `handed_off`: set once a senior takes the app. Form: `"<name>, <date>, PR #N"`.
- `change` on a capability page: `new`, `extend`, `replace`, `narrow`, `retire` or `unchanged`. `origin`: `proposed` or `imported`. Proposed capabilities keep their IDs and are mapped to an official map later, never renamed.
- `domain` on a capability page: a short name for the business area it belongs to, such as `Booking`. The `capability-map` block groups capabilities by it. A capability with no `domain` is drawn under "No domain".
- Epic lists, all of IDs: `apps` (the `APP-` pages it touches), `delivers` (what it builds or changes: capabilities, contracts on the provider side, goals), `consumes` (contracts it builds a client for), `flows`, `depends_on` (other epics). A contract relied on unchanged goes in neither `delivers` nor `consumes`.
- `modes` on a session: a list of `dump`, `discover`, `shape`, `grill`, `requirements`, `epics`.

## IDs

IDs are never reused or renumbered. A file's basename is frozen once anything links to it. Basenames are unique across the vault, ignoring case.

| Kind | Pattern | Where it lives | File name |
|---|---|---|---|
| Initiative | `INI-001` | `.planner.yaml` | |
| App | `APP-booking` | app page `id` | `booking-building-blocks.md` |
| Runtime page | `RUN-booking` | runtime page `id` | `booking-runtime.md` |
| Capability, flow, epic | `CAP-013`, `FLO-001`, `EPC-031` | page `id` | starts with the ID, then `-<slug>` |
| Decision | `ADR-0001` | page `id` | starts with the ID, then `-<slug>` |
| Concern | `concern-testing` | page `id` | the ID |
| Session | `2026-08-12-goals-and-data` | page `id` | the ID. Add `-2` on a same-day clash. |
| Contract, unknown, risk, functional requirement | `CON-001`, `UNK-001`, `R-01`, `CAP-001.FR1` | `### <ID> <short name>` heading | |
| Goal, constraint, source | `G1`, `CST-1`, `SRC-01` | first column of their table | |
| Other pages | lower-case slug, for example `goals` | page `id` | |

## Certainty and sources

Every item has a state. `inkling` is a hunch. `assumption` is believed but not checked. `fact` has a source. `decided` came out of a Grill. `unknown` is a question with an owner, an ask-by date and a list of what it blocks.

- **Only a Grill decides.** A `decided` page carries a page-level `- **Decision:** [[<session>]]` bullet, and a `decided` contract or functional requirement carries one under its heading. The linked session's `modes` must include `grill`. Goal rows take their decision from the Goals page's bullet.
- **A requirements session cannot decide.** It writes at most `assumption`.
- **A fact needs a source.** A `fact` page lists `sources`. A `fact` contract or functional requirement carries `- **Source:** SRC-nn`. A goal row at `fact` needs its page to list `sources`.
- **What counts as a source.** A document describing what exists gives a fact. A document stating intent gives an assumption. A person's first-hand knowledge gives a fact. Claude's general knowledge is never a source.
- **Sources live in the register.** `sources.md` has one row per document: `ID | Title | Owner | Date | Kind | Location`. `Kind` is `exists`, `intends` or `repo`. A `repo` source is a code repository read at a commit, with Location `<url>@<sha>`. Raw files stay in `.inbox/`; document text is never copied into the vault.
- **Disputes are unknowns.** When two sources or two people disagree, write an unknown naming both. Do not pick one.
- **State a value once.** The item that owns a value states it. Every other page links to it.

## Fact bullets

A fact bullet is a list line `- **Label:** value`, one label per line. Unknown labels are prose. Bullets under a `### <ID> <name>` heading belong to that item. Bullets elsewhere belong to the page.

Page level: `**Decision:**` (a link to the deciding Grill) and `**Dissent:**` (`<name>, <date>: <reason>`).

Contract, under `### CON-nnn <name>` on the provider's building-blocks page:

| Label | Rule |
|---|---|
| `**Crosses the boundary:**` | Required. What goes in and out. |
| `**Consumers:**` | Required. Links to each consumer's building-blocks page, or `none`. Notes may follow the links. |
| `**Change policy:**` | Required. |
| `**Change:**` | Required. `new`, `changed`, `new consumers` or `unchanged`. |
| `**State:**` | Required. `inkling`, `assumption`, `fact` or `decided`. |
| `**Tested by:**` | Required once `decided`. Who tests it from each side. |
| `**Source:**` | Required when `fact`. |
| `**Decision:**` | Required when `decided`. |
| `**Provider:**` | Only for an external provider with no page. The contract then lives on the consumer's page. |
| `**Dissent:**` | Optional. |

Functional requirement, under `### CAP-nnn.FRn <what it does>` on the capability page. It carries `**State:**` (`inkling`, `assumption`, `fact` or `decided`) and is checked like a contract. `decided` needs `**Decision:**` linking a Grill session, `fact` needs `**Source:**`, and an open unknown that lists it in `**Blocks:**` stops it being `decided`.

Unknown, under `### UNK-nnn <short name>` on `11-unknowns-and-risks.md`:

| Label | Rule |
|---|---|
| `**Question:**` | Required. The heading stays a short name, so rewording the question breaks no link. |
| `**Owner:**` | Required. Starts with a handle: `@hl-platform-lead (Platform lead)`. |
| `**State:**` | Required. `open` or `resolved`. |
| `**Blocks:**` | Required. Links to what it blocks, or a value starting `nothing`. |
| `**Ask by:**` | Required while `open`. `YYYY-MM-DD`. Past this date the check warns. |
| `**Outcome:**`, `**Resolved in:**` | Required once `resolved`. |
| `**Opened:**`, `**Notes:**` | Optional. |

An item an open unknown lists in `**Blocks:**` cannot be `decided`. Resolve the unknown first.

Risk, under `### R-nn <name>`: `**Owner:**` and `**State:**` are required. State is `open`, `mitigated`, `accepted` or `closed`. `**Mitigation:**` is optional.

## Fact tables

A fact table is recognised by its first header cells.

| Table | Header | Rules |
|---|---|---|
| Goals | `ID \| Goal \| Measure \| State` | ID `G1`; State `inkling`, `assumption`, `fact`, `decided` |
| Constraints | `ID \| Constraint \| ...` | ID `CST-1` |
| Sources | `ID \| Title \| Owner \| Date \| Kind \| Location` | ID `SRC-01`; Kind `exists`, `intends`, `repo` |
| Containers | `Container \| Job \| ... \| State` | State `assumption`, `confirmed`, `unchanged`, `retired` |
| Concern cells | `App \| State \| ...` | See below |
| Session changes | `ID \| From \| To \| Source` | One row per item a session changed |

## Concern cells and waivers

Each concern page holds one cell per app in a table headed `App | State | ...`. The App column links the app's building-blocks page. State is one of:

- `addressed`: this initiative decided something for the app under this concern.
- `unchanged`: the app's existing practice holds. Unchanged apps default to this.
- `n/a`: the concern does not touch the app. The next column says why.
- `unknown`: an open unknown must be answered first. The row links it.
- `unexamined`: nobody has looked. An app with no row counts as `unexamined (no row)`.

A waiver records that an `addressed` cell needs no epic work. The cell text starts `no work (@handle, review YYYY-MM-DD): <reason>`.

## Pages

- **App pages go one level in.** A new or changed app gets a building-blocks page (what it does, what it does not do, the `app-context` block, containers, contracts it provides, the `contracts-consumed` block) and a runtime page (its part in each flow, and how it behaves when something fails).
- **Slim pages for unchanged apps.** An `integrated` or `unchanged` app gets one page with its job, why it is a black box, the `app-context` block, and the contracts it provides at `fact`. It has no runtime page; the consumer's runtime page says what happens when it fails.
- **Contracts live on the provider's page.** A contract with an external provider lives on its consumer's page with a `**Provider:**` bullet.
- **Containers, never components.** Each container row says who proposed it and its state.
- **About one screen per section.** Split a page along its `##` headings when it grows.

## Links and headings

- Links are Obsidian wikilinks to a basename: `[[booking-building-blocks|Booking]]`. No paths, no Markdown links between pages.
- An anchor equals the full heading text: `[[booking-building-blocks#CON-001 Booking API|CON-001]]`. A same-page anchor is `[[#UNK-006 Finance on Booking events|UNK-006]]`.
- Item headings are `### <ID> <short name>`, at most six words, with none of `# | ^ : % [ ]`.
- Inside a table, escape the pipe: `[[booking-building-blocks\|Booking]]`.
- A link to a capture line uses its block ID: `[[2026-08-12-goals-and-data#^c01]]`.
- Links inside code are ignored.

## Diagrams

Mermaid only, as `flowchart` (or `graph`) or `sequenceDiagram`. A flowchart has at most 20 elements, counting each node and each subgraph once. A sequence diagram has at most 8 participants. Draw only the level the page owns: initiative pages draw systems, app pages draw that app's containers and direct neighbours, and nothing draws components.

Four diagrams are generated blocks, drawn from the model: `context-map`, `system-context`, `app-context` and `capability-map`. Nothing in them is drawn by hand. A generated diagram keeps to the same budget. Over it, the diagram draws the app in focus first, then new and changed apps, then the other apps, then external providers, and lists every node it left out in a table under the diagram, with its contracts. The capability map first splits into one diagram per domain. Generated diagrams hold no `%%` directives and no frontmatter. Diagrams with no generator, such as an app's containers or a flow's swimlanes, are drawn by hand.

## Sessions

One record per session at `sessions/YYYY-MM-DD-<topic>.md`, with `date`, `modes`, `status` (`open` or `closed`) and `summary` in the frontmatter. The body has `## Captures` and `## Changes`.

A capture line:

```
- [<tag>] (<origin>) <words> → <mark> ^c<NN>
```

- Tag: `idea`, `thought`, `unknown`, `wild` or `worry`.
- Origin: a person's name, role or handle, whose words are quoted verbatim; `claude` for Claude's own idea; or `claude, from <name>` for Claude's summary of what someone said.
- Mark, added at close: `keep: [[<page>#<heading>|<ID>]] (<state>)`, `park`, or `drop: <reason>`. Claude's own lines default to `park`. An `unknown` capture is kept or dropped with a reason, never parked.
- The block ID `^cNN` is the last token on the line and unique in the file.

## Generated blocks

A generated block sits between two markers and is written only by `planner render`:

```
<!-- generated:unknowns-index sha=1f3a9c0e: do not edit, run planner render -->
...
<!-- /generated:unknowns-index -->
```

The `sha` is the first 8 hex digits of SHA-256 over the block's text, with trailing spaces and blank edge lines removed. A text that no longer matches its `sha` was edited by hand. To add a block, write both markers with `sha=00000000` and nothing between them, then run `planner render`. Blocks hold links and numbers and dates, never ages or prose.

| Block | Page | What it shows |
|---|---|---|
| `where-it-stands` | `01-goals.md` | Apps with their typed stage, and beside it the counts of blocking unknowns, `unexamined` cells and contracts `decided` or `fact`; every open unknown with owner, ask-by and what it blocks; the last session date; once epics exist, "Delivery status: not tracked in this vault" |
| `concern-matrix` | `08-concerns.md` | One row per app, one column per concern, each cell's state |
| `unknowns-index` | `11-unknowns-and-risks.md` | Every unknown and risk with owner, state and ask-by |
| `contracts-consumed` | each app page | Every contract whose `**Consumers:**` links this app |
| `epics-for-app` | each app page | Every epic whose `apps` lists this app, with owner and state |
| `traceability` | `13-epics.md` | Each trace gap in full, and the number of checks that pass |
| `traces-to` | each epic page | The epic's `apps`, `delivers`, `consumes`, `flows` and `depends_on` as links, and the concerns its acceptance criteria mark |
| `delivered-by` | each capability page | Every epic whose `delivers` lists this capability |
| `context-map` | `05-building-blocks.md` | One node per app page and per external `**Provider:**`, and one arrow per contract from its provider to each consumer, labelled with the contract ID. Each app's label and colour say its `change`. |
| `system-context` | `03-context-and-scope.md` | The after view: apps in one box, external providers outside it, and the same contract arrows. Retired apps are listed under it, not drawn. |
| `app-context` | each app page | The app and its direct neighbours by contract, provided or consumed |
| `capability-map` | `04a-capability-delta.md` | Every capability in a box per `domain`, labelled and coloured by `change` |

A view with no generator is a list of links to where the data lives, never a copy kept by hand.

## planner check and planner render

Run `python3 .claude/skills/planner/bin/planner check` from the vault root. It reads, never writes, and never stops at the first problem. `--today YYYY-MM-DD` sets the date for overdue unknowns; without it the system date is used, and the first line of output says which. Exit code 0 means no errors (warnings may print), 1 means errors, 2 means the tool itself failed.

`planner render` rewrites generated blocks only. It writes nothing if any page fails to parse or any block was edited by hand. `--discard-edits` overwrites hand-edited blocks and prints what it threw away.

| Code | Finding | Code | Finding |
|---|---|---|---|
| E101 | page has no frontmatter | E303 | decided without a Grill decision |
| E102 | frontmatter is not a valid YAML mapping | E304 | fact without a source |
| E103 | required field missing | E306 | fact table row is not valid |
| E104 | unknown page type | E311 | consumers name no app |
| E105 | value not allowed | E315 | app has no cell on a concern page |
| E106 | not a YYYY-MM-DD date | E316 | decided while an open unknown blocks it |
| E107 | id does not fit its type or file name | E317 | a requirements session cannot decide |
| E108 | two pages share an id | E318 | decided contract has no Tested by |
| E201 | link to a page that does not exist | E319 | stage does not fit the app's change |
| E202 | link anchor matches no heading | E320 | contract is missing a required fact |
| E204 | two files share a basename | E401 | generated block was edited by hand |
| E207 | ID reference resolves to nothing | W402 | generated block is out of date |
| E208 | item ID used by two headings | E403 | generated block not allowed here |
| E301 | concern cell is not valid | E404 | generated block markers are broken |
| E302 | unknown or risk is missing a required fact | E601 | flowchart over its element budget |
| W705 | unknown is past its ask-by date | E602 | sequence diagram over its participant budget |
| | | E603 | diagram type not supported |
| W501 | no epic delivers a capability that changes | E501 | no epic delivers a capability that changes |
| W502 | no epic delivers a new or changed contract | E502 | no epic delivers a new or changed contract |
| W503 | no epic covers a concern cell with work | E503 | no epic covers a concern cell with work |
| W504 | epic delivers nothing | E504 | epic delivers nothing |

Codes are stable. A retired code is never reused.

## Epics and traceability

An epic page holds a description, the owning team, 4 to 7 numbered acceptance criteria, dependencies, rollout notes and what is out of scope. Its trace data is the frontmatter lists; the `traces-to` block shows them as links. Each acceptance criterion describes behaviour a tester can see at a contract or flow boundary, never inside a container.

A concern marker ends an acceptance criterion with the concern's name in brackets, `[testing]` for `concern-testing`. One criterion may carry several, `[security] [data]`. A criterion whose text starts with `~~` is struck and its markers count for nothing.

Four trace rules run once the vault holds an epic. They are warnings in `planner check` and errors under `planner check --gate epics`, which is run before anyone calls an app's epics complete.

| Rule | Passes when | Codes |
|---|---|---|
| T1 | Every capability whose `change` is not `unchanged` is in some epic's `delivers` | W501, E501 |
| T2 | Every contract whose `**Change:**` is `new` or `changed` is in some epic's `delivers`. A contract with an external `**Provider:**` may be in `consumes` instead. | W502, E502 |
| T4 | Every `addressed` cell is covered: a waiver, or an acceptance criterion with the concern's marker on an epic whose `apps` lists the app. An Ownership cell is covered by any epic whose `apps` lists the app. | W503, E503 |
| T6 | No epic has an empty `delivers` | W504, E504 |

A cell that starts `no work` but does not follow the waiver form covers nothing, and T4 says so.

## Handoff

`handed_off` goes on the app page in the PR the senior approves. Before offering an app, check the boundary list:

- The page says what the app does and what it does not do.
- Every container is `confirmed`, `unchanged` or `retired`, or the app is a black box with a reason.
- Every contract it provides is `decided`, with change policy, `**Tested by:**` and `**Change:**`.
- Every contract it consumes is `decided` or `fact`, or links an open unknown.
- No concern cell for the app is `unexamined`.
- The runtime page says how the app behaves when something fails.
- Every open unknown that blocks the app has an owner and an ask-by date.

Then the acceptance-criteria list: every epic the app's team owns is `decided`, and `planner check --gate epics` exits 0.
