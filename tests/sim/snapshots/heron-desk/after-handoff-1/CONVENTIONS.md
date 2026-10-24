# Conventions

This file is the vault's one written format. Every page follows it, and `vela check` enforces the parts a script can see. If a rule here and the check disagree, the check has a bug. Search this file for any field, label or code to find the rule behind it.

## Layout

One vault holds one initiative. Pages are numbered by arc42 section.

| Path | What it holds |
|---|---|
| `README.md` | Home page: layout, reading paths, setup checklist |
| `CLAUDE.md` | How Claude answers questions from this vault. A person writes it. |
| `.vela.yaml` | `initiative` (`INI-nnn`), `title`, `stale_after_days` (default 60), and optionally `link_templates` (see Links out of the vault), `designs` (see Team design docs), `owner_contact` (who a published copy's readers write to) and `role: reader` (see Roles and published copies) |
| `01-goals.md` | Goals table, and the `where-it-stands` and `progress-map` blocks |
| `02-constraints.md` | Constraints table, `CST-n` |
| `03-context-and-scope.md` | Systems today and after; apps in and out of scope |
| `04-solution-strategy.md`, `04a-capability-delta.md` | The core move; links to every capability that changes |
| `04b-releases.md` | One section per release, listing the functional requirements it delivers |
| `05-building-blocks/` | Index with the `context-map` block, then `<app>-building-blocks.md` per app, with its contracts |
| `06-runtime/` | `06-flows.md`, `flows/FLO-nnn-<slug>.md`, `apps/<app>-runtime.md` |
| `08-concerns/` | `08-concerns.md` with the `concern-matrix` block, then `concern-<name>.md` |
| `09-decisions/` | Index, then `ADR-nnnn-<slug>.md` |
| `11-unknowns-and-risks.md` | Every unknown and risk, the `unknowns-index` block, and the question ledger with its `undisposed-questions` block |
| `12-glossary.md` | Terms |
| `13-epics/` | Index, then `EPC-nnn-<slug>.md` |
| `capabilities/` | `CAP-nnn-<slug>.md` per capability touched |
| `sources.md` | The source register, `SRC-nn` |
| `sessions/` | One record per session, `YYYY-MM-DD-<topic>.md` |
| `voice/examples/` | House-voice passages. Never a source. Committed. |
| `voice/local/` | The owner's passages that stay on one machine, same format as `voice/examples/`. Gitignored, never committed. `voice/corpus/` is gitignored too. |
| `docs/` | The team's design and plan for a handed-off app, written by the user's `tech-design-grill` and `work-breakdown` skills when run from the vault root: `docs/tech-design/<slug>.md`, `docs/plan/<slug>-breakdown.md`, `docs/adr/`. Not vela pages: `vela check` does not read them, and `publish`, `open` and `propose` carry them like any other file. `CONTEXT.md` at the vault root is the design's glossary, also not a page. |
| `handoffs/` | `<APP-id>.md` per handed-off app: the manifest `vela handoff` writes. Never edited by hand. |
| `.inbox/` | Documents dropped for Discover. Gitignored, never parsed. |
| `dashboard.html` | The explorer page `vela explore` builds (and `/vela:close`, `open` and `import` rebuild), one offline file at the vault root. Committed, so a colleague who pulls the repo or opens the OneDrive folder just opens it; it says at the top when it was built and from which commit. Generated, never edited by hand and never parsed: `vela check`, `search` and `capture` ignore it. `vela publish` rebuilds it from the published pages. |
| `.vela/` | The tool's own files, never parsed. Gitignored except `explorer-pins.json`, which is committed so a team shares one map layout: the explorer's fixed layout, `{node ID: [column, row]}`, written on the first build and added to when an app or party appears; delete it to lay the map out afresh. A reader's workspace (`workspace.json`, `baseline/`, `replay-backup/`) and `findings/` review scratch stay ignored. The template's `.gitignore` says `.vela/*` then `!.vela/explorer-pins.json`; a plain `.vela/` line cannot be undone for one file inside it. |

`vela check` reads every `.md` file except `CLAUDE.md`, `CONVENTIONS.md`, `CONTEXT.md`, anything under `voice/`, `handoffs/` or `docs/`, and anything under a folder whose name starts with a dot.

## Areas and stages

An area is an app whose `change` is `new` or `changed`, or one of `initiative`, `capabilities`, `concern-<name>` and `epics`. Only apps move through stages. The initiative is at Frame while no app has a stage. Frame is never typed.

`stage` sits on the app's building-blocks page and means "in this stage now". It is typed by hand. `vela ladder` shows, for each app on the ladder, the latest stage whose entry list its pages already meet, with every stage below it, and what the next stage still needs; `vela status` adds `pages reach <stage>` when that is later than the typed stage. Neither changes the stage. The `where-it-stands` block shows counts beside it, so a stage the counts contradict is easy to see. Apps whose `change` is `integrated`, `unchanged` or `retired` sit outside the ladder and take no `stage`.

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
| `app-building-blocks` | as above, plus `change` | `stage`, `initiative`, `arc42`, `c4`, `sources`, `handed_off`, `domain`, `icon`, `design` | `inkling`, `assumption`, `fact`, `decided` |
| `app-runtime` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `inkling`, `assumption`, `fact`, `decided` |
| `flow` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `inkling`, `assumption`, `fact`, `decided` |
| `concern` | `id`, `type`, `title`, `owner`, `authored` | `initiative`, `arc42`, `sources` | none: the cells hold the states |
| `decision` | `id`, `type`, `title`, `state`, `owner`, `authored` | `initiative`, `arc42`, `sources` | `proposed`, `decided`, `superseded`, `rejected` |
| `epic` | as above, plus `apps`, `delivers` | `consumes`, `flows`, `depends_on`, `initiative`, `sources` | `draft`, `decided`, `reopened` |
| `capability` | as above, plus `origin`, `change` | `sources`, `domain` | `inkling`, `assumption`, `decided` |
| `session` | `id`, `type`, `date`, `modes`, `status`, `summary` | `title` | none: `status` is `open` or `closed` |
| `sources` | `id`, `type`, `title`, `authored` | `owner` | none |

Every type except `session` may also carry `last_verified`, `verified_by` and `links`.

Field values:

- `authored`: `authored` (people wrote it), `generated` (only blocks), `mixed` (both).
- `owner`: a GitHub handle or team, `"@handle"` or `"@org/team"`. Several owners are separated by spaces, as in CODEOWNERS. Close uses it to request reviews and to mention owners.
- `initiative`: if present, it must equal `.vela.yaml`.
- `c4`: `landscape`, `context` or `container`. `arc42`: the section, for example `"§5"`.
- `sources`: a list. Use `SRC-nn` IDs for documents. Free text, such as a session name, is allowed as a summary.
- `change` on an app page: `new`, `changed`, `integrated`, `unchanged` or `retired`.
- `stage`: `baseline`, `target`, `boundaries`, `contracts`, `handoff`, `epics`. Required when `change` is `new` or `changed`, absent otherwise.
- `last_verified`: the date someone last reread the page against its sources, `YYYY-MM-DD`. `verified_by`: that person's handle, `"@handle"`. Set both together. A page without them is never judged stale.
- `handed_off`: set once a senior takes the app. Form: `"<name>, <date>, PR #N"`, or `"<name>, <date>, PR pending"` until the PR exists; W325 warns until the number is written.
- `change` on a capability page: `new`, `extend`, `replace`, `narrow`, `retire` or `unchanged`. `origin`: `proposed` or `imported`. Proposed capabilities keep their IDs and are mapped to an official map later, never renamed.
- `domain` on a capability page: a short name for the business area it belongs to, such as `Booking`. The `capability-map` block groups capabilities by it. A capability with no `domain` is drawn under "No domain".
- Epic lists, all of IDs: `apps` (the `APP-` pages it touches), `delivers` (what it builds or changes: capabilities, contracts on the provider side, goals), `consumes` (contracts it builds a client for), `flows`, `depends_on` (other epics). A contract relied on unchanged goes in neither `delivers` nor `consumes`.
- `modes` on a session: a list of `dump`, `discover`, `shape`, `boundary`, `allocate`, `grill`, `requirements`, `epics`, `challenge`, `answer`. A `challenge` session is a senior's challenge after handoff, written by `/vela:challenge`. An `answer` session is the solution lead's answer to one, opened by START on the challenge's own branch. Like every mode but `grill`, neither can decide: an answer that decides adds `grill` to its `modes`.

## IDs

IDs are never reused or renumbered. A file's basename is frozen once anything links to it. Basenames are unique across the vault, ignoring case.

| Kind | Pattern | Where it lives | File name |
|---|---|---|---|
| Initiative | `INI-001` | `.vela.yaml` | |
| App | `APP-booking` | app page `id` | `booking-building-blocks.md` |
| Runtime page | `RUN-booking` | runtime page `id` | `booking-runtime.md` |
| Capability, flow, epic | `CAP-013`, `FLO-001`, `EPC-031` | page `id` | starts with the ID, then `-<slug>` |
| Decision | `ADR-0001` | page `id` | starts with the ID, then `-<slug>` |
| Concern | `concern-testing` | page `id` | the ID |
| Session | `2026-08-12-goals-and-data` | page `id` | the ID. Add `-2` on a same-day clash. |
| Contract, unknown, risk, functional requirement | `CON-001`, `UNK-001`, `R-01`, `CAP-001.FR1` | `### <ID> <short name>` heading | |
| Party, stored value | `PTY-01`, `SV-01` | `### <ID> <short name>` heading on `03-context-and-scope.md` | |
| Goal, constraint, source | `G1`, `CST-1`, `SRC-01` | first column of their table | |
| Other pages | lower-case slug, for example `goals` | page `id` | |

## Certainty and sources

Every item has a state. `inkling` is a hunch. `assumption` is believed but not checked. `fact` has a source. `decided` came out of a Grill. `unknown` is a question with an owner, an ask-by date and a list of what it blocks.

- **Only a Grill decides,** unless the user overrides it (see Overrides). A `decided` page carries a page-level `- **Decision:** [[<session>]]` bullet, and a `decided` contract or functional requirement carries one under its heading. The linked session's `modes` must include `grill`, or an `**Override:**` on the item names `grill`. Goal rows take their decision from the Goals page's bullet.
- **A requirements session cannot decide.** It writes at most `assumption`.
- **A fact needs a source.** A `fact` page lists `sources`. A `fact` contract or functional requirement carries `- **Source:** SRC-nn`. A goal row at `fact` needs its page to list `sources`.
- **What counts as a source.** A document describing what exists gives a fact. A document stating intent gives an assumption. A person's first-hand knowledge gives a fact. Claude's general knowledge is never a source.
- **Sources live in the register.** `sources.md` has one row per document: `ID | Title | Owner | Date | Kind | Location`. `Kind` is `exists`, `intends` or `repo`. A `repo` source is a code repository read at a commit, with Location `<url>@<sha>`. Raw files stay in `.inbox/`; document text is never copied into the vault.
- **Disputes are unknowns.** When two sources or two people disagree, write an unknown naming both. Do not pick one.
- **State a value once.** The item that owns a value states it. Every other page links to it.

## Fact bullets

A fact bullet is a list line `- **Label:** value`, one label per line. Unknown labels are prose. A `- Trace:` line under a criterion is not a fact bullet; see Pages. Bullets under a `### <ID> <name>` heading belong to that item. Bullets elsewhere belong to the page.

Page level: `**Decision:**` (a link to the deciding Grill), `**Dissent:**` (`<name>, <date>: <reason>`) and `**Options considered:**` (what a Shape weighed: `<picked option> (picked); <option>: rejected, <reason>; ...`). `**Override:**`, `**Decided by:**` and `**Confirmed by:**` may go on any page or under any item heading; see Overrides. So may `**Pending approval:**`; see Pending approval.

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
| `**Options considered:**` | Optional. What a Shape weighed, in the page-level form. |
| `**Links:**` | Optional. Where the contract is written down outside the vault, such as its API spec. See Links out of the vault. |
| `**Override:**`, `**Decided by:**`, `**Confirmed by:**` | Optional. See Overrides. |
| `**Pending approval:**` | Optional. A reader's decision awaiting the owner. See Pending approval. |

Functional requirement, under `### CAP-nnn.FRn <what it does>` on the capability page. It carries `**State:**` (`inkling`, `assumption`, `fact` or `decided`) and is checked like a contract. `decided` needs `**Decision:**` linking a Grill session, `fact` needs `**Source:**`, and an open unknown that lists it in `**Blocks:**` stops it being `decided`.

Unknown, under `### UNK-nnn <short name>` on `11-unknowns-and-risks.md`:

| Label | Rule |
|---|---|
| `**Question:**` | Required. The heading stays a short name, so rewording the question breaks no link. |
| `**Owner:**` | Required. Starts with a handle: `@hl-platform-lead (Platform lead)`. |
| `**Ask:**` | Optional. Who holds the answer, when that is not the owner: a handle such as `@privacy-lead`, or a role in words such as `outside counsel`. The owner answers for the question; the person to ask answers it. Views of who to ask group by this, then by the owner. |
| `**State:**` | Required. `open` or `resolved`. |
| `**Blocks:**` | Required. Links to what it blocks, or a value starting `nothing`. |
| `**Ask by:**` | Required while `open`. `YYYY-MM-DD`. Past this date the check warns. |
| `**Outcome:**`, `**Resolved in:**` | Required once `resolved`. |
| `**Opened:**`, `**Notes:**` | Optional. |

When an unknown is resolved, every page that mentions it must stop calling it open. `vela check` reports W334 for a sentence that links a resolved unknown with wording such as "still open", "not decided", "waiting on" or "pending", outside `## History` and generated blocks. A link label that only repeats the question's heading is its name, not a claim, so "[[…#UNK-001 Ledger write latency|ledger write latency]]" names the question and claims nothing about it. Close rewrites these sentences, using `vela query refs <ID>` to find them.

An item an open unknown lists in `**Blocks:**` cannot be `decided`. Resolve the unknown first.

Risk, under `### R-nn <name>`: `**Owner:**` and `**State:**` are required. State is `open`, `mitigated`, `accepted` or `closed`. `**Mitigation:**` is optional.

Party, under `### PTY-nn <name>`: an outside organization the initiative works with or answers to. Stored value, under `### SV-nn <name>`: points, credits, balances, vouchers or deposits held for customers. Both live on `03-context-and-scope.md`, parties under `## Outside parties` and stored value under `## Value held for customers`. The question catalog fires on them, so a missing bullet is E808: the questions it should raise would never be owed. A relationship outside the list is E105. A heading that starts `PTY` or `SV` but is not `### PTY-nn` or `### SV-nn` (wrong level, one digit, lower case, a colon after the ID) is E810, so a typo never hides a subject. A party or stored value defined on any other page still loads and warns W811: `03-context-and-scope.md` is its home.

Parties and stored value carry no `**State:**`. A stored value's `**Owner:**` is free text, not a handle. The check only tests that each required fact is not empty; the catalog's questions test what it says.

| Item | Label | Rule |
|---|---|---|
| Party | `**Relationship:**` | Required. `partner`, `supplier`, `regulator` or `customer group`, in any case. |
| Party | `**Agreements:**` | Required. The agreements it is party to, with their `SRC-nn` where one is registered, or `none known`. |
| Party | `**Links:**` | Optional. Its API spec, docs or portal. See Links out of the vault. |
| Stored value | `**Holder:**` | Required. The app or party that holds the balances: a link to its page or heading, or its name. |
| Stored value | `**Owner:**` | Required. Who carries the balances as money owed to customers, such as a finance team, or `not known yet` with a link to the unknown that asks. |

## Overrides

The person using the skills may override any rule in them: a grill gate, "only a Grill decides", a blocking open unknown, an absent owner, or any other skill rule. The lead may decide on others' behalf. An override is never refused and never hidden. It is written on the item it sets a rule aside for, where reviewers, `vela check`, `/vela:ask` and the progress views all read it.

```
- **Override:** <rule>, <rule> by @handle on YYYY-MM-DD: <reason>
- **Decided by:** @handle, on behalf of @owner
- **Confirmed by:** @owner on YYYY-MM-DD
```

- **Override.** One or more rules, separated by `, `, then ` by `, the handle of the person who chose to override, ` on `, the date, `: ` and the reason. Several `**Override:**` bullets may sit on one item. A rule is one of these names, spelled exactly:

  | Rule | Sets aside | Turns this error into this warning |
  |---|---|---|
  | `GATE-1`, `GATE-2`, `GATE-3`, `GATE-5` | that grill gate | none: the check cannot see these gates, so the bullet is the record |
  | `GATE-4` | an open unknown blocks the item | E316 to W316 |
  | `grill` | "only a Grill decides" | E303 to W303, and E317 to W317 |
  | `E303`, `E304`, `E316`, `E317`, `E318` | that check rule alone | E303 to W303, E304 to W304, E316 to W316, E317 to W317, E318 to W318 |
  | `E805` | the epics gate's rule that high-severity questions are disposed | E805 to W805 |
  | `"<the rule's words>"`, in double quotes | a skill rule with no name above, for example `"Shape offers 2 or 3 options"` | none |

- **Where it sits.** Under an item's heading, or under `#### <ID>` in the page's `## History`, it covers that contract or functional requirement. At page level, which is directly under `## History`, it covers the page and its goal rows, not the items under its headings. A rule that belongs to no item, such as how a session ran, goes at page level in the session record. An override of `E805` goes at page level under `## Question ledger` on `11-unknowns-and-risks.md`, and covers every E805 there; each one still prints, as W805.
- **Decided by.** When someone other than the item's owner decided it: the decider's handle, `, on behalf of ` and the owner's handle or handles. The lead's yes settles any item, so `vela decide` writes this line itself whenever the yes isn't the owner's own, with no override and no reason asked; nothing warns, and the owner can add a `**Confirmed by:**` line or challenge it. A bare handle, `- **Decided by:** @owner`, is the owner's own decision: it is what accepting a reader's proposal writes, and it needs no confirmation.
- **Confirmed by.** The owner adds it later: their handle, ` on ` and the date. A team owner is confirmed by one of its people. A confirmation by the person who decided does not count.
- **An owner who disagrees** with a decision made on their behalf raises `/vela:challenge` on the item, as a senior does after handoff. Confirming and challenging are the only two answers.

`vela check` reads them this way:

- A well-formed override that names the rule an error enforces turns that error into its warning, and the warning quotes the override. Nothing else changes: the warning stays until the rule is met or the bullet goes.
- A malformed override is E321: no rule, an unknown rule name, no handle, no date, a date that is not real, or no reason. A malformed `**Decided by:**` or `**Confirmed by:**` is E322. So is a label one typo away from one of the three, such as `**Overide:**`. A typo never silently fails to override.
- W323: an override names a rule the check can test, and the item does not break it, so the override sets nothing aside. A rule only a gate tests, such as `E805`, is judged only when that gate runs, so a plain check never calls its override idle.

## Pending approval

A reader is someone working from a published copy with no git access (see Roles and published copies). They may record a decision or an override, but it is not settled until an owner has seen it, so every item they decide or override carries a marker. An owner's decision never does.

```
- **Pending approval:** @handle, YYYY-MM-DD
```

The bullet goes where `**Override:**` goes: under the item's heading, or under `#### <ID>` in `## History`; at page level it covers the page. The item keeps its state, `decided`. A bullet, not frontmatter, because decisions sit on contracts and functional requirements, many to a page, and frontmatter holds one value per page.

- W327: one warning for the whole vault, `N items pending approval`, then each item with the handle and date. It is never an error, so a reader's copy stays green. On an owner's `main` it means a review skipped one.
- A malformed `**Pending approval:**` (no handle, or a date that is not real) is E322, as is a label one typo away from it. The marker is the only thing telling an owner a decision is a reader's, so a typo must not hide it.
- The owner clears it in review. Accept: remove the marker, record `**Decided by:** @owner`, and add a credit line to History. Reject: revert the change. Edit: commit the owner's version, remove the marker, same credit.

## Roles and published copies

Authority comes from access, not title and not config. An **owner** works inside the vault's git work tree and can commit. A **reader** has a published copy: no `.git`, a `.vela/workspace.json`. `vela role` prints which you are. `.vela.yaml` may say `role: reader` to downgrade an owner who wants to browse safely; `role: owner` is ignored with a warning, because the file ships in published copies and honoring it would let a reader promote themselves.

`vela publish --out <folder|.zip>` writes a read copy of the committed files at HEAD, never the working tree. It leaves out `.git`, generated `.vela/` output (the committed `explorer-pins.json` stays in, so a reader's map matches the owner's), `voice/local/` and the vendored plugin copy, and adds `.vela/published.json`: the initiative, title, full and short commit, date, whether the vault had uncommitted changes (`dirty`), the owner's contact (`owner_contact` in `.vela.yaml`, else `git config`), the `vela check` counts, and a `tree_hash` of the contents. A dirty vault is never refused; the stamp says so. A zip has one top folder, forward-slash names and fixed timestamps, so the same input gives the same zip. A reader cannot publish.

`vela freshness [--json]` says whether anything has changed, and never updates anything. An owner's clone runs `git fetch` (8 seconds, `--timeout` to change) and reports commits behind and ahead of upstream and uncommitted files; offline is said plainly and local state is shown. A reader's workspace compares its baseline stamp with the stamp at the folder or zip it was opened from; an unreachable source is said plainly, and is not a failure.

## Fact tables

A fact table is recognized by its first header cells.

| Table | Header | Rules |
|---|---|---|
| Goals | `ID \| Goal \| Measure \| State` | ID `G1`; State `inkling`, `assumption`, `fact`, `decided` |
| Constraints | `ID \| Constraint \| ...` | ID `CST-1` |
| Sources | `ID \| Title \| Owner \| Date \| Kind \| Location` | ID `SRC-01`; Kind `exists`, `intends`, `repo` |
| Containers | `Container \| Job \| ... \| State` | State `assumption`, `confirmed`, `unchanged`, `retired` |
| Concern cells | `App \| State \| ...` | See below |
| Session changes | `ID \| From \| To \| Source` | One row per item a session changed |
| Question ledger | `Copy \| State \| Evidence \| By \| Date` | Only on `11-unknowns-and-risks.md`; see Questions and the ledger |

## Concern cells and waivers

Each concern page holds one cell per app in a table headed `App | State | ...`. The App column links the app's building-blocks page. State is one of:

- `addressed`: this initiative decided something for the app under this concern.
- `unchanged`: the app's existing practice holds. Unchanged apps default to this.
- `n/a`: the concern does not touch the app. The next column says why.
- `unknown`: an open unknown must be answered first. The row links it.
- `unexamined`: nobody has looked. An app with no row counts as `unexamined (no row)`.

**Who writes a cell.** `unchanged`, `n/a` (with why) and `unknown` (linking its open unknown) state what is so, not a choice, so any mode writes them on the lead's yes, and close writes them from a capture that says so. A cell whose unknown is resolved moves on in the same session: to `unchanged` or `n/a` if the answer says nothing changes, or it waits for a Grill. Only `addressed` is a decision, and only a Grill writes it. A Grill takes a cell to its agenda when the lead states what the initiative does for the app under the concern: that statement is the cell's preferred option, and a cell with no real choice needs no rejected options.

A waiver records that an `addressed` cell needs no epic work. The cell text starts `no work (@handle, review YYYY-MM-DD): <reason>`.

## Questions and the ledger

Code decides which questions the vault owes. The skills decide only how to ask them, and the ledger records how each one ended.

**The catalog.** `.claude/skills/vela/catalog/questions.yaml` ships with the plugin and carries a `version`. Each entry has an `id` such as `Q-FIN-01`, a focus `area`, a `scope`, a `trigger`, the `question`, a `why` (the regulation, practice or simulation miss that earned it a place) and a `severity`, `high` or `normal`. `blocks` lists the kinds of unit an open copy holds up: `app`, `contract`, `requirement`, `capability`, `decision` and `epic`. An initiative-scope entry may say which subject a yes `creates`, `party` or `stored-value`, and list the words that suggest that subject in `mentions`. Each mention is a group of forms such as `license/licenses`, and `mention_why` gives each group its reason. `mention_except` lists phrases such as `credit card*` that use the word for something else and are not read as the subject; a `*` ends a word at any suffix. The five focus areas are `FIN` Finance and liabilities, `DAT` Data and lawful basis, `PTN` Partners and contracts, `REG` Regulation and liability and `OPS` Operations and people. They are labels for readers, and they are not the areas of "Areas and stages".

**Subjects and copies.** A scope names the kind of subject an entry applies to: `initiative` (the initiative in `.vela.yaml`), `app`, `contract`, `capability`, `party` or `stored-value`. A trigger is `exists`, or conditions joined by ` and `, each `<field>: <value>` or `<field> in [<value>, <value>]`. An app has the fields `change`, `state` and `stage`. A contract has `change`, `state` and `provider`, which is `external` when the contract has a `**Provider:**` bullet and `app` otherwise. A capability has `change`, `state`, `origin` and `domain`, and a party has `relationship`. The initiative and a stored value have none, so their entries use `exists`. Values are compared in lower case, and a missing field never matches. Code reads a trigger; it never runs one.

`vela questions` applies each entry once to each subject of its scope that its trigger matches. Each result is a copy, with the ID `<entry>@<subject>`, for example `Q-DAT-02@APP-booking`. The ID follows the subject's ID, so renaming a file keeps it. A subject that is removed takes its copies with it, and a ledger row for one of them is reported as orphaned, never dropped.

**The ledger.** The record is one table under `## Question ledger` on `11-unknowns-and-risks.md`, headed `| Copy | State | Evidence | By | Date |`, spelled exactly, below the `undisposed-questions` block. Every owed copy and every reviewer question ends in a row.

- **Copy** is a copy ID; a wildcard such as `Q-OPS-01@APP-*`, which answers every copy whose subject starts with the text before the `*` (it must start with the scope's prefix, `APP-`, `CON-`, `CAP-`, `PTY-` or `SV-`); or a reviewer question, `R-<area>-nn` such as `R-FIN-01`.
- **State** is one of the six below. **By** is the handle of whoever recorded or decided it, and **Date** is `YYYY-MM-DD`. Both are required unless the state is `open`.
- **Evidence** is `key: value` pairs separated by `; `. A `;` inside double quotes or a wikilink does not split. The keys are `capture`, `item`, `source`, `answer`, `belief`, `load-bearing`, `signpost`, `unknown`, `reason`, `covers`, and on a reviewer question `question`, `quote` and `severity`.

| State | Valid only with |
|---|---|
| `open` | nothing. It is the default, and it never counts as disposed. |
| `asked` | `capture:`, a link to the capture where it was asked, `[[<session>#^cNN]]` |
| `answered` | `item:`, a link to the item that holds the answer, `answer:`, the answer in one line, and `source:`, which is exactly one `SRC-nn` from `sources.md` (a first-hand row counts) or exactly one quote from a page, `"<the words>" in [[<page>]]` |
| `assumed` | `belief:` what is believed, `load-bearing:` `yes` or `no`, and `signpost:` what would show it failing |
| `unknown` | `unknown:`, an `UNK-nnn` that is still `open` and whose `**Owner:**` starts with a handle. A resolved unknown has an answer, so the row is `answered` |
| `not-applicable` | `reason:` why it does not apply. By says who decided. not-applicable means it does not apply, never not yet: a reason that defers, such as "for now", "depends on", "pending", "later", "TBD", "until we know" or "decide after", is E802. A question that waits on something is `unknown`, with an `UNK-nnn`, or `assumed`. |

A copy's own row wins. Then the wildcard with the longest prefix, then an initiative row. An initiative row answers a lower scope at initiative level: `Q-OPS-03@INI-002` with `covers: capability` answers every `Q-OPS-03` copy for a capability, until one has its own row. Exceptions to a wildcard or an initiative row take their own row. A reviewer question carries `question:` with the question, `quote: "<the words>" in [[<page>]]`, and `severity: high` when it is one; without it, it is `normal`.

A quote, whether a `source:` or a reviewer question's `quote:`, names its page, and `vela check` looks for the words in that page's hand-written text: not its frontmatter, a generated block, an HTML comment, on `11-unknowns-and-risks.md` the ledger section, or in a session record the `## Reviews` section. `## Reviews` holds the reviewers' own words and the quotes a merge dropped, so neither can come back as evidence. Case, spacing, curly quotes and Markdown emphasis do not count, so the words may be copied as the page shows them. A quote needs at least four words. A quote with no page, a page that is not in the vault, too few words, or words that are not on the page is E802, so a quote is never taken on trust. A `source:` that mixes a quote and an `SRC-nn`, or adds anything else, is E802 too. A key that belongs to another state, such as `reason:` on an `answered` row, is E802. The `answer:` text is free text, and `vela check` does not compare it with the quote or the item.

`vela check` reads the ledger. A malformed row, two rows for one copy, any table directly under `## Question ledger` whose header is not exactly the ledger's, a ledger table that is not under the first `## Question ledger`, or a second `## Question ledger` heading is E801. A row with any error, and any row of a misplaced ledger table, disposes of nothing: `vela questions` shows it as `invalid` and counts the copy as undisposed. A state without the evidence it needs is E802. A row that names an entry the catalog lacks, a subject that does not fit the entry's scope, or a reviewer area the catalog lacks is E803. A row whose subject is gone, or whose subject no longer matches the trigger, is W804: it stays as a record. A wildcard that no copy uses, because each has a row of its own or a longer wildcard, and a wildcard on an initiative entry are W804 too. A row dated after today is W812. A `11-unknowns-and-risks.md` with no `## Question ledger` heading is W813 while any copy is owed, because every answer would have nowhere to be recorded. A copy with no row, or an `open` row, is never a finding in a plain check. The lead sets the pace.

Three gates read it too. Each names a moment, and a skill runs it then:

| Gate | When | What it reports |
|---|---|---|
| `vela check --gate shape` | the end of a Shape | W806 for each row still `assumed`. An assumption clears into a decision, a requirement or a constraint before Shape closes. |
| `vela check --gate grill --item <ID>` | a Grill, once per agenda item | W807 for each copy with no row, or an `open`, `asked` or invalid row, that blocks the item. A warning: the lead may decide anyway. An item no catalog question can block gets one W807 saying so. |
| `vela check --gate epics` | before epics are called complete | E805 for each high-severity copy or reviewer question with no row, or an `open`, `asked` or invalid row. An `asked` question is still waiting for its answer. A gate that passes while `assumed` rows with `load-bearing: yes` dispose of high-severity questions prints one note naming them. |

`--item` repeats, once per agenda item, and goes only with `--gate grill`, which needs at least one. An ID the vault does not hold exits 2.

A question only fires on a subject someone typed. So W809 warns, "possibly an untyped subject", where a fact bullet or a table row says one of the words an existence question lists in `mentions` (points, balances, credits, vouchers or deposits for stored value; a clause or a license for a party), the page neither holds nor links a subject of that kind, and that existence question has no row yet or an `open` one. It warns once per page and question. Prose, session records, `sources.md` (a source's title names a document, not a subject), generated blocks and the ledger are not read for it. Type the subject and link it, or answer the existence question, and the warning goes.


`vela questions` lists every owed copy with its focus area, severity, state, subject, what it blocks while it is open or asked, and the question, then the reviewer questions. `--json` prints the same as data, `--area FIN` keeps one focus area, `--subject APP-booking` one subject, and `--open` lists only the copies with no row, an `open` row, an invalid row or an `asked` row, and the reviewer questions that are open, invalid or asked. An `asked` question is not undisposed, but it still holds the gates, so every list of what is pending shows it, labeled `asked`. Its first line is the coverage: "57 owed, 3 undisposed, against catalog v1", with ", 2 asked" after the undisposed count when any copy or reviewer question is `asked`. It never says complete, because the catalog finds only what is written into it. An unknown `--area` exits 2, and a `--subject` that names no subject exits 1.

`vela questions --digest` is what a session shows the lead. It groups the undisposed and asked copies by entry, so one answer can serve many, adds the open, invalid and asked reviewer questions, and ranks them: high severity that blocks something first, then high severity, then the rest, by entry ID within each. It leaves nothing out. Up to ten lines it prints every line in full. Past ten it prints the consequential lines in full, those of high severity or that block something, then the rest counted by area, one line each, such as `FIN: 6 more (normal). List them: vela questions --open --digest --all --area FIN`, and ends with the command for every line in full. `--all` prints every line in full at any length. A line counted by area is still in `--open`, in `--json` and in the `undisposed-questions` block. `vela questions --stats` counts, for each entry, how its copies ended in this vault and how often they ended `not-applicable`. An entry that nearly always ends `not-applicable` is one to prune or tighten, and that is the user's call. Neither writes anything.

**Focused reviewers.** At a few checkpoints a session runs one read-only reviewer per focus area, each in a fresh context, given the written pages and its area's owed copies and nothing of the conversation. Each returns its findings as JSON, which the session saves as `<folder>/<AREA>.json`, such as `FIN.json`: `{"area": "FIN", "findings": [...]}`, or `{"area": "FIN", "error": "<why>"}` when the reviewer could not finish. Each finding has `finding`, `quote` (words copied from the page), `page`, `copy` (an owed copy ID, or `new` for a question of the reviewer's own), `severity` (`high` or `normal`) and `question`, the question for the lead. `vela findings merge <folder>` keeps the union, removes exact duplicates (the same copy and the same question, ignoring case, spacing and punctuation), and folds near-duplicates from different areas into one finding that lists every area. Two findings are near-duplicates when they address the same copy, or one is `new` and the other `new` or an open reviewer question, and their questions' content words (English function words left out, each word cut to a crude stem) have a Jaccard of 0.6 or more, or of 0.2 or more when both quote the same words on the same page. The merged finding is `high` if any of them was, takes the reviewer question's ID if one addressed it, and each folded finding stays listed under duplicates with its own words. The merge drops each finding whose quote is not in the hand-written text of the page it cites (the same check a ledger row's quote gets, so a quote needs 4 or more words), or that names a copy the vault does not owe, or whose quote shares no content word with its question, its subject's name or the reviewer question it addresses ("the quote does not mention what the finding is about"), with the reason. Given `--changed`, the pages a session changed (`<page>` for all of it, `<page>:40-52+88-90` for those lines), it also drops a `new` finding whose quote is on any other page or line, as "a new question about a page this session did not change": that question was owed when the page was written. With `--changed`, it also drops a `new` finding that quotes a `decided` page, or a decided item's section or `## History` block, unless its severity is `high`, as "a new question about something already decided, and it is not high severity": a Grill closed it, and only a question that would change a decision, a contract, a liability or the lawful use of data reopens it. The quote is read with the heading above it and the bold label of its bullet, because a gap is quoted where its answer belongs. A question with no English function word is not judged for that. It never votes. Its coverage line gives each focus area one of four results: `found N` (with `, M dropped` when some were), `checked, none`, `did not run (<reason>)`, or `skipped (nothing in scope)` for an area named with `--skipped`, which goes with `--areas` and names the areas a checkpoint left out because nothing in them was owed or touched. A skipped area is never read. A reply that is one fenced code block is read without its fence. A missing file, a file that is not JSON, or a reviewer's error is `did not run`, never `checked, none`. It exits 0 when every area ran or was skipped and nothing was dropped or ignored, 1 otherwise, and 2 when the folder does not exist.

## Pages

A page reads as what is true now. Its history sits at the end, folded in the viewer, for whoever wants it.

- **Opening prose.** Every app, runtime, initiative-section, capability, epic, concern and flow page opens, under its title and before its first `##` heading, with a paragraph or two in the house voice: what the thing is, what it does and does not do, and what is still open. It says the current state, not how it got there. Close rewrites it for every page a session changed.
- **Prose, not lists.** Bullets are for the fact bullets `vela check` reads (the labels in the tables of this file) and for lists a reader scans, such as an epic's criteria. Everything else is a paragraph. A bold label nothing reads, such as `- **Brightwater, what it does:**`, is prose dressed up as data: write the sentence. Say who says a thing in the sentence ("the product lead says"), never in a bracket.
- **Every item opens with a sentence.** Under each `### <ID> <name>` heading, before its fact bullets, a sentence or two say what the item is now: what a contract carries and for whom, what an unknown asks and why it matters. The viewer folds the fact bullets under it.
- **Links on the words.** A source is cited as a link on the words that rely on it, `[[sources#SRC-04|the latency measurement]]`, never a bare "(SRC-04)". A link to an item reads as the item's name, `[[11-unknowns-and-risks#UNK-006 Finance on Booking events|whether Finance reads Booking's events]]`, never its number. Prose names things; IDs stay in headings, fact bullets and tables.
- **Plain names.** In prose, headings and acceptance criteria, refer to a thing by its plain name ("the calendar entries", "the prep-note flow"), never by a bare ID. A wikilink's visible label is the name, not the ID. An abbreviation is spelled out at its first use on a page ("the data protection officer (DPO)"), or not used at all. IDs stay where the machine reads them: frontmatter, generated blocks, tables, wikilink targets and headings, and the Trace line below.
- **The Trace line.** What a criterion or bullet traces to goes on its own line under it, not in brackets inside the sentence: `- Trace: CAP-001.FR1, CON-001, FLO-001`. Indent it under its item (three spaces under a numbered criterion, two under a bullet), write the IDs separated by commas, and put the requirement first. It is a plain line, not a fact bullet, and `**Trace:**` is read the same. Vela reads it where it used to read the IDs in the sentence: `vela query refs` finds an ID there, the explorer and the viewer show the line as one folded row of name chips, and `vela style` and close leave it alone. A page written before this keeps its inline "From CAP-001.FR1" and checks as before; rewrite it the next time a session touches it.
- **A page fits in a head.** People hold about four to seven things in mind at once (Cowan 2001; Miller 1956), so a page is sized to that. It opens with a two or three sentence summary: what it says, and what is still open. A list of more than about seven items is grouped under subheadings of about five. An epic with more than about seven acceptance criteria is a signal to split it: the epics session proposes the cut, and the user may keep it whole, which is recorded. A list of unknowns or concerns shows the few that matter first and folds the rest under `## Also open (n)`, which the viewer and the explorer fold.
- **History at the end.** Every `**Decision:**`, `**Override:**`, `**Decided by:**`, `**Confirmed by:**`, `**Pending approval:**`, `**Options considered:**` and `**Dissent:**` bullet goes under `## History`, the page's last `##` section. Page-level ones sit directly under it; an item's sit under `#### <ID>` inside it, which gives them to that item exactly as if they were under its own heading. Wherever a skill or this file says "at page level" or "under the item's heading" for one of these bullets, it means there. A bullet anywhere else still counts, so older pages stay valid.
- `vela style <page>...` lists where a page still reads as a log: a history bullet above `## History`, an ID or a bare source ID in prose or in a list item, or no opening prose. It never calls a `- Trace:` line prose. Close runs it on the pages a session changed.
- **App pages go one level in.** A new or changed app gets a building-blocks page (what it does, what it does not do, the `app-context` block, containers, contracts it provides, the `contracts-consumed` block) and a runtime page (its part in each flow, and how it behaves when something fails, under `## On failure`).
- **Slim pages for unchanged apps.** An `integrated` or `unchanged` app gets one page with its job, why it is a black box, the `app-context` block, and the contracts it provides at `fact`. It has no runtime page; the consumer's runtime page says what happens when it fails.
- **Contracts live on the provider's page.** A contract with an external provider lives on its consumer's page with a `**Provider:**` bullet.
- **Containers, never components.** Each container row says who proposed it and its state.
- **About one screen per section.** Split a page along its `##` headings when it grows.

## Links and headings

- Links are Obsidian wikilinks to a basename: `[[booking-building-blocks|Booking]]`. No paths, no Markdown links between pages.
- An anchor equals the full heading text: `[[booking-building-blocks#CON-001 Booking API|the booking API]]`. A same-page anchor is `[[#UNK-006 Finance on Booking events|whether Finance reads Booking's events]]`. The label is the name; in a table vela reads, such as an allocation row, the ID stays as the label.
- Item headings are `### <ID> <short name>`, at most six words, with none of `# | ^ : % [ ]`.
- Inside a table, escape the pipe: `[[booking-building-blocks\|Booking]]`.
- A link to a capture line uses its block ID: `[[2026-08-12-goals-and-data#^c01]]`.
- Links inside code are ignored.

## Diagrams

Mermaid only, as `flowchart` (or `graph`) or `sequenceDiagram`. A flowchart has at most 20 elements, counting each node and each subgraph once. A sequence diagram has at most 8 participants. Draw only the level the page owns: initiative pages draw systems, app pages draw that app's containers and direct neighbors, and nothing draws components.

Four diagrams are generated blocks, drawn from the model: `context-map`, `system-context`, `app-context` and `capability-map`. Nothing in them is drawn by hand. A generated diagram keeps to the same budget. Over it, the diagram draws the app in focus first, then new and changed apps, then the other apps, then external providers, and lists every node it left out in a table under the diagram, with its contracts. The capability map first splits into one diagram per domain. Generated diagrams hold no `%%` directives and no frontmatter. Diagrams with no generator, such as an app's containers or a flow's swimlanes, are drawn by hand.

## Sessions

One record per session at `sessions/YYYY-MM-DD-<topic>.md`, with `date`, `modes`, `status` (`open` or `closed`) and `summary` in the frontmatter. The body has `## Captures` and `## Changes`. A session that ran a review checkpoint also has `## Reviews` after `## Captures`: per checkpoint, a `### <n>. <checkpoint>, <date>` heading, a `- **Coverage:**` line copied from `vela findings merge`, a `- **Dropped:**` line, and a table `| Finding | Area | Severity | Copy | Question | Quote |` with one row per kept finding, `F<n>.1` and on. Close may add `## Catalog proposals`, a YAML block of new catalog entries the user approved.

A capture line:

```
- [<tag>] (<origin>) <words> → <mark> ^c<NN>
```

- Tag: `idea`, `thought`, `unknown`, `wild` or `worry`.
- Origin: a person's name, role or handle, whose words are quoted verbatim; `claude` for Claude's own idea; or `claude, from <name>` for Claude's summary of what someone said.
- Mark, added at close: `keep: [[<page>#<heading>|<ID>]] (<state>)`, `park`, or `drop: <reason>`. Claude's own lines default to `park`. An `unknown` capture is kept or dropped with a reason, never parked.
- The `(<state>)` of a keep is the item's state (`inkling`, `assumption`, `fact` or `decided`); `open` for an unknown; the row's state for a ledger row (`open`, `asked`, `answered`, `assumed`, `unknown` or `not-applicable`); or `subject` for a party or stored value, which carries no state.
- The block ID `^cNN` is the last token on the line and unique in the file.

A harvest decline is one bare line, `Harvest declined: PR <n> <page> <hash>`, directly under `## Captures`, never a bullet. `<hash>` is the first 12 characters of the `shasum` of the paragraph. Close writes it and reads it back, so a declined paragraph is not offered again.

## Voice examples

House-voice passages live in `voice/examples/<voice type>/`, one per file named `VX-<voice type>-NNN.md`. The voice types are `diagnosis`, `decision` and `how-it-works`. `vela check` never reads `voice/`.

| Field | Rule |
|---|---|
| `id` | `VX-<voice type>-NNN`, the file name |
| `voice_type` | the folder's voice type |
| `source` | `public-seed` (a licensed passage that ships with the template), `owner` (the owner's own writing, added by `/vela:voice-seed`) or `owner-edit` (a drafted paragraph the owner edited, harvested at close) |
| `state` | `active` (house-voice reads it) or `retired` (kept for its attribution, never read) |
| `added` | `YYYY-MM-DD` |
| `author` | who wrote it: a name for `public-seed`, `"@handle"` for `owner` and `owner-edit` |
| `work`, `chapter`, `url`, `license`, `license_url`, `changes` | `public-seed` only: where it comes from and its license |
| `from` | `owner` only: where the passage comes from, in a few words |
| `page`, `harvested_from` | `owner-edit` only: the page, and the full hash of the draft commit the owner edited |

A voice type holds at most 5 `active` examples, counting `voice/examples/` and `voice/local/` together. When a sixth becomes active, one retires: the `public-seed` examples first, then the `owner-edit`, then the `owner`, the oldest `added` first within each. The owner may refuse a retirement. Then nothing new is stored for that type. Once a type has 2 `active` examples with `source: owner` or `owner-edit` in the same folder as a `public-seed` example, counted after the run, that seed retires, so drafts follow the owner. A local example never retires a committed seed, so every clone keeps its seed. An owner's words are stored as written and never rewritten. Nothing is ever deleted.

`voice/local/<voice type>/VX-<voice type>-NNN.md` holds examples in the same format that stay on one machine, for text the owner may not publish. `/vela:voice-seed` writes there when the owner picks local only. House-voice reads both folders, and on that machine reads local `owner` and `owner-edit` examples ahead of the committed ones.

`vela voicecheck <before> <after>` compares the protected tokens of a text before and after a rewrite. The kinds are `id`, `number` (with its unit and currency symbol), `date`, `version`, `link` (wikilinks, Markdown link URLs and bare URLs), `code`, `cell` (table cells), `frontmatter` (every line, compared exactly) and `negation` (the count of negation words in the prose of each file, outside frontmatter, table rows, code spans, links and URLs: not, no, never, cannot, without, nobody, nothing, none, nor, neither, nowhere, and any word ending in n't. The count is per file, so splitting, merging or moving paragraphs does not change it). `vela voicecheck --range A..B` does the same for every `.md` file two commits changed, and `--range A` compares commit A with the working tree. It exits 1 if a token is missing, added or moved, and names each one with its line, and 2 if it cannot read a file or a commit.

`vela voicescore <file>` is optional. It needs `sentence-transformers` and a one-off `vela voicescore setup`, and the rest of vela never does. It embeds each prose paragraph of a file with the StyleDistance style model and says whether it sits inside or outside the owner's range: how far each active `owner` and `owner-edit` example sits from the others. Below 5 such examples it says the score is unreliable. It uses the public seed only when asked with `--against seed`, and says so. `--rank <a> <b>` orders drafts of one paragraph. It is a hint and never a gate: it always exits 0 when it scored, and 2 when it could not. Its vectors are cached in `.git/vela-voicescore/`, which is never committed.

## Generated blocks

A generated block sits between two markers and is written only by `vela render`:

```
<!-- generated:unknowns-index sha=1f3a9c0e: do not edit, run vela render -->
...
<!-- /generated:unknowns-index -->
```

The `sha` is the first 8 hex digits of SHA-256 over the block's text, with trailing spaces and blank edge lines removed. A text that no longer matches its `sha` was edited by hand. To add a block, write both markers with `sha=00000000` and nothing between them, then run `vela render`. Blocks hold links and numbers and dates, never ages or prose.

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
| `context-map` | `05-building-blocks.md` | One node per app page and per external `**Provider:**`, and one arrow per contract from its provider to each consumer, labeled with the contract ID. Each app's label and color say its `change`. |
| `system-context` | `03-context-and-scope.md` | The after view: apps in one box, external providers outside it, and the same contract arrows. Retired apps are listed under it, not drawn. |
| `app-context` | each app page | The app and its direct neighbors by contract, provided or consumed |
| `capability-map` | `04a-capability-delta.md` | Every capability in a box per `domain`, labeled and colored by `change` |
| `allocation` | `04a-capability-delta.md` | One row per functional requirement, one column per app that carries any: each cell is that app's share, with the contracts it goes through. A blank row is a requirement nobody owns yet. |
| `undisposed-questions` | `11-unknowns-and-risks.md`, under `## Question ledger` | The coverage line, then every undisposed copy (no row, an `open` row or an invalid row), every `asked` copy, and every open, invalid or asked reviewer question, with its state, focus area, severity, subject and question. It is the to-do list; the rows below it are the record. |
| `progress-map` | `01-goals.md` | One row per app: its stage, how many of its items are at each state, with "(n by override)" after the decided count, the oldest open unknown that blocks it with its Opened date, and its next mode. It is judged as of the last session's date, so it changes only when the vault does. |

A view with no generator is a list of links to where the data lives, never a copy kept by hand.

## Progress and next step

`vela status` ends with a completeness line: five shares (items settled, unknowns resolved, concern cells examined, questions disposed, template pages written) and their mean. It never says done. Before that, it prints one line per app: its stage, how many of its items are at `inkling`, `assumption`, `fact` and `decided`, with "(n by override)" after the decided count when n of them carry an `**Override:**`, the oldest open unknown that blocks it with its age, and its next mode with the reason. An app's items are its building-blocks page, its runtime page and the contracts on its page. `vela next` prints the one app and mode to work on next. Both judge overdue unknowns by `--today YYYY-MM-DD`, or the system date, and say which. The `progress-map` block holds the same grid, judged as of the last session's date.

For each app the first rule that matches picks the mode. `vela next` takes the app whose rule has the lowest number, then the earliest stage, then the lowest app ID, and skips apps whose mode is `none`.

| Rule | Mode | Matches when |
|---|---|---|
| 1 | Probe | an open unknown that blocks the app is past its ask-by date |
| 2 | Boundary | the app page is a Boundary stub: it says "Its boundary sheet is still to be read back." and has no containers table |
| 2 | Discover | the app page lists no `sources` |
| 3 | Discover | the app is `integrated` or `unchanged`, and one of its items no open unknown blocks is at `inkling` or `assumption`: what exists needs a source to reach `fact` |
| 3 | Shape | one of its items is at `inkling`, or at `assumption` with no `**Options considered:**` |
| 4 | Discover | an item has options recorded, but the app's `stage` is before `target`, so it fails GATE-1 |
| 5 | Grill | an item at `assumption` has options recorded and no open unknown blocks it |
| 6 | Probe | an open unknown blocks one of its items |
| 7 | none, waits | a contract it provides or consumes is not `decided` or `fact` |
| 8 | Epics | the app is `new` or `changed`, and no epic lists it, or one that does is not `decided` |
| 9 | none | nothing is open |

Requirements cut across apps, so two steps are the initiative's, not any app's, and `vela next` names them ahead of every app rule but rule 1: `initiative, allocate CAP-nnn` while a functional requirement at `assumption`, `fact` or `decided` has no row carrying it, and, before the first epic, `initiative, requirements CAP-nnn` while a changing capability has no functional requirements. While no app page exists, `vela next` suggests `initiative, requirements` once `04-solution-strategy.md` is `decided` and no capability has functional requirements, then `initiative, boundary`, and `initiative, dump` before the strategy is decided.

## Keeping the vault fresh

`stale_after_days` in `.vela.yaml` sets how old a check may be before it is stale. The default is 60. Three warnings follow from it, and a fourth checks this file itself. None of them blocks a PR:

- W704: a page's `last_verified` is more than `stale_after_days` before today.
- W716: a `sources.md` row's `Date` is more than `stale_after_days` before today, or is not a date.
- W711: the last session with `status: closed` is more than 30 days before today. A vault with no closed session yet is not judged.
- W326: a goals page whose every goal is further along than the page's own `state`, or a constraints page at `inkling` or `assumption` whose every row cites where it comes from. Close sets the page's state as the warning says.
- W717: this file is not the copy the installed plugin ships. `vela upgrade` replaces it with the plugin's copy; review the change with `git diff CONVENTIONS.md` and commit it.

A `last_verified`, a source `Date` or the last closed session dated after today is not fresh: W704, W716 or W711 says it is "dated in the future (<date>); check for a typo." `vela health` marks the row the same way.

`vela health` prints the same signals as one Markdown report: stale pages, stale sources, overdue unknowns with their owners @-mentioned, the days since the last closed session, and how many pages were never verified. The weekly workflow `.github/workflows/vela-weekly.yml` posts it as the one open issue titled "Vault health", creating it the first time and editing it after that.

## vela query

`vela query` answers questions about IDs and never writes. Add `--json` for JSON.

- `vela query get <ID>`: the item's page, heading, state, owner, sources, deciding session, dissent, the open unknowns that block it, the wikilink to cite it by, and its overrides: `override` (each `**Override:**` bullet, its rules, handle, date and reason, or `malformed` with the problem), `decided_by` (who decided on whose behalf, and whether it is `confirmed`) and `confirmed_by`.
- `vela query refs <ID>`: every page line that links to the ID, every list in page properties that names it, and every other line that holds the ID as a whole token (`via: mention`). The line that defines the ID is left out.
- `vela query find <words>`: page titles, item headings and goal, constraint and source rows that hold every word, in any case. Put `--` before a word that starts with `-`.
- `vela query search <words>`: plain-word search. It ranks every page and section by how many of the meaningful words it holds and where (title, heading, opening, text), leaves out History, and lists the flows whose steps link each place. A "how" question ranks flows higher. `/vela:find` uses it.
- `vela query status`: the `vela status` grid as data.

An ID the vault does not hold comes back as `not_found` and exits 1. An ID is matched exactly, so `con-001` is not `CON-001`.

## vela check and vela render

Run `python3 .claude/skills/vela/scripts/vela check` from the vault root. It reads, never writes, and never stops at the first problem. `--today YYYY-MM-DD` sets the date for overdue unknowns; without it the system date is used, and the first line of output says which. Exit code 0 means no errors (warnings may print), 1 means errors, 2 means the tool itself failed.

`vela render` rewrites generated blocks only. It writes nothing if any page fails to parse or any block was edited by hand. `--discard-edits` overwrites hand-edited blocks and prints what it threw away.

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
| W704 | page not verified within stale_after_days | E603 | diagram type not supported |
| W711 | no session closed in the last 30 days | W716 | source row older than stale_after_days |
| W501 | no epic delivers a capability that changes | E501 | no epic delivers a capability that changes |
| W502 | no epic delivers a new or changed contract | E502 | no epic delivers a new or changed contract |
| W503 | no epic covers a concern cell with work | E503 | no epic covers a concern cell with work |
| W504 | epic delivers nothing | E504 | epic delivers nothing |
| W505 | no app carries a functional requirement | E505 | no app carries a functional requirement |
| E330 | allocation row names no functional requirement | E331 | allocation row goes through no such contract |
| E332 | allocation row has no valid state | E333 | allocation row is a fact on a page with no sources |
| W334 | prose calls an answered question open | | |
| E344 | release target is not a YYYY-MM-DD date | E350 | flow step names a sender or receiver its contract does not join |
| W351 | flow step links a contract but names no sender and receiver | W352 | app has no domain though other apps in a large initiative do |
| W353 | two domains differ only by case or a trailing s | W355 | unknown asks the person who owns it |
| W356 | changing capability has no functional requirements | W357 | functional requirement lists no acceptance criteria |
| E340 | release row names no functional requirement | E341 | release row names a criterion the requirement does not have |
| E342 | release has no valid state | W343 | no release delivers a functional requirement |
| E321 | override is malformed | W303 | decided without a Grill, by override |
| E322 | decided-by or confirmed-by is malformed | W304 | fact without a source, by override |
| W316 | decided while an open unknown blocks it, by override | W317 | decided by a requirements session, by override |
| W318 | decided contract has no Tested by, by override | W323 | override not needed |
| W329 | a table row's link label pipe is not escaped as `\|` | | |
| E801 | question ledger row is malformed | E802 | ledger state lacks the evidence it needs |
| E803 | ledger row names nothing the catalog owes | W804 | ledger row is orphaned or no longer owed |
| E805 | high-severity question not disposed at the epics gate | W805 | high-severity question not disposed, by override |
| W806 | assumed question not resolved at the end of shape | W807 | open question blocks the grilled item |
| E808 | party or stored value is missing a required fact | W809 | possibly an untyped subject |
| E810 | heading looks like a party or stored value but is not one | | |
| W811 | subject defined off its page | | |
| W812 | ledger row is dated in the future | W813 | ledger page has no question ledger heading |
| W360 | one sentence holds three or more IDs | W361 | an ID in prose, outside a link and not followed by its name |
| W362 | a list of more than nine items with no subheadings | W363 | a long page with no opening summary |
| W364 | an epic lists more than nine acceptance criteria | | |

W360 to W364 are the reading-load warnings. They are warnings only, and each fix line says how to write it in plain words. W360 fires on a sentence with three or more IDs, W361 on an ID written in prose that is neither inside a link nor followed by its name (tables, headings, code, History and `- Trace:` lines are the machine's and are left alone), W362 on more than nine list items under one heading, W363 on a page of more than about 900 words with no paragraph between its title and its first `##` heading, and W364 on an epic with more than nine numbered acceptance criteria. The conventions above aim lower (about seven) so a page at the edge is not nagged.

Codes are stable. A retired code is never reused.

## Requirements and allocation

Requirements come in two levels, both in the vault. A capability's functional requirements say what the business needs and name no app: `### CAP-nnn.FRn <short name>` under `## Functional requirements` on its capability page, with a paragraph of what it does, `**State:**`, and its acceptance criteria as bullets, each followed by an indented `- Trace:` line when it cites another item (the line is not a criterion, and AC numbers skip it). `/vela:requirements` writes them at `assumption`, after the strategy is decided and before boundary, so boundary can test each cut against them, and a Grill decides them.

Allocation divides each requirement among the apps and contracts that deliver it. `/vela:allocate`, after boundary and before epics, writes each app page's share in one table under `## Requirements allocated`:

| Requirement | Share | Through | State |
|---|---|---|---|
| `[[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]]` | accepts the order, rejects fractions and shorting, records the fill | CON-006 | assumption |

- **Requirement** links the functional requirement's heading. **Share** says this app's part in the domain's words. **Through** names the contracts that carry the part across to another app, or `—`. **State** is `inkling`, `assumption`, `fact` or `decided`. A `fact` row records a share an app already carries, and needs the page's `sources`, as a goal row at `fact` does. A `decided` row needs the page's `**Decision:**` to link a Grill, as goal rows do; a Grill on the app decides its rows with its page. An `inkling` row carries nothing: only a row at `assumption` or later counts as the requirement's owner.
- A contract's obligation is a row on its provider's table that names it in **Through**. A contract with an outside provider takes the row on its consumer's page.
- When dividing a requirement shows two apps must talk in a way no contract covers, allocation writes that contract at `assumption` on the provider's page with every required bullet, and raises it.

`vela check` reports E330 for a row that names no functional requirement of this vault, E331 for a **Through** that names no contract, E332 for a State outside the four, and E333 for a `fact` row on a page with no sources. A `decided` row answers to the decision rules as `CAP-nnn.FRn@APP-<slug>`: E303 when the page's Decision links no Grill, E317 when it links only a requirements session. T7 is a trace gap: a requirement at `assumption`, `fact` or `decided` that no row at `assumption` or later carries. It warns, and is an error under `--gate epics`. The `allocation` block on `04a-capability-delta.md` shows every requirement against every app.

An app's allocated rows are its team's input. Epics take their acceptance criteria from them, and the team's `tech-design-grill` traces its components to them.

## Releases

`04b-releases.md` holds one `## <release name>` section per release, such as `## Release one: January board demo`, in the order they ship. Under the heading, `- **Target:** YYYY-MM-DD` and `- **State:**` (`inkling`, `assumption` or `decided`), then a table of what it delivers:

| Delivers | Criteria | Note |
|---|---|---|
| `[[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]]` | AC1, AC2 | AC3 in release two |

**Criteria** is `all`, or the acceptance criteria this release delivers, numbered in the order they appear under the requirement: AC1 is the first bullet (an indented `- Trace:` line under a bullet is not a bullet of its own). A requirement may be split across releases this way, so an epic never needs a release of its own.

Nothing else records a release. What the system looks like after each one is worked out from the requirements it delivers: each app that carries a share of one changes, or arrives if it is new, and each contract its share goes through exists. Today is every app whose `change` is not `new`, and every contract whose `**Change:**` is not `new`.

`/vela:releases` writes this page, after allocate and before epics, in a session with mode `releases`. A requirement the user places on no release ("later, no date") stays out of the file; W343 lists it.

`vela check` reports E340 for a row that names no functional requirement of this vault, E341 for a criterion the requirement does not list, E342 for a release with no valid State, and E344 for a Target that is not a real YYYY-MM-DD date. Once any release exists, W343 warns for a requirement at `assumption`, `fact` or `decided` that no release delivers. A Grill decides a release, as it decides any other item.

## Flow steps

A flow page lists its journey under `## Steps`, one numbered line per step. A step that crosses between two lanes starts with the sender, an arrow and the receiver, then a colon and the sentence:

```
3. [[tickertalk-building-blocks|TickerTalk]] → [[coach-building-blocks|Coach]]: sends the opaque reader ID, and nothing else, over [[tickertalk-building-blocks#CON-005 Reader identity|Reader identity]].
```

`->` reads the same as `→`. An outside party is named by its name or by a link to its party page. The pair is the recorded direction: the explorer draws it as stated, and guesses a direction only for a step without one. A step with no hand-over, such as a reader opting in, needs no pair. `vela check` reports E350 when the sender or receiver is not a party the linked contract joins (its provider, an outside **Provider:**, or a consumer), or when both ends are the same, and W351 when a step links a contract and names no pair.

## Domains

An app page may say which domain it belongs to, as `domain: <name>` in its frontmatter, such as `domain: Channels`. Views of the system group apps by it, so a map of twenty apps opens as a handful of domains. Boundary asks for it once, for all the apps of the cut together, offering the domains already in the vault first so spellings converge. An app with no domain is shown under "No domain". `vela check` warns (W352) when some app has a domain and, in an initiative of 6 or more apps, another has none, and (W353) when two domains differ only by case or a trailing s.

An app page may also name the picture views draw for it, as `icon: <word>`, one short lower-case word such as `icon: payments`. Without it a view picks one from the app's title, domain and opening words. Anything else is E105.

## Team design docs

The inside of an app is the team's own tech design, `docs/tech-design/<slug>.md`, and its build plan, `docs/plan/<slug>-breakdown.md`. Both live in the vault: the team runs `tech-design-grill` and `work-breakdown` from the vault root, so they write there. (`tech-design-grill`'s vault mode says it never edits the vault; that means vela pages. Its own `docs/` files are the design's.) `vela explore` draws them under Inside this app and finds them itself, from local files only (it never fetches anything), taking the first of these for each app that `--design APP-x=<path>` did not name:

1. `design: <path>` in the app page's frontmatter, such as `design: ../team-repo/docs/tech-design/booking.md`;
2. `designs: {APP-booking: ../team-repo/docs/tech-design/booking.md}` in `.vela.yaml`, one entry per app;
3. the vault's own `docs/tech-design/*.md`, with no configuration: the doc whose frontmatter `vault: {app: APP-booking}` names the app, else whose `prereqs` name the app's page, else whose file name is the app's slug (`booking.md` for `APP-booking`);
4. the app's `GitHub`, `Code`, `Repo` or `Repository` link in `links:`, when it is a `file://` URL to a clone, such as `GitHub: file:///Users/sam/code/booking`. The doc in that clone's `docs/tech-design/` whose frontmatter `vault.app` names the app is the design (the inside-view format records it as `vault: {app: APP-booking}`). A link to a web address is not read.

The build plan is the `docs/plan/*-breakdown.md` beside the design whose `prereqs` name it (`breakdown:` on the app page or `breakdowns:` in `.vela.yaml` names one directly). A relative path is relative to the vault root, and `~` is the home folder. A path that leads to no file, a clone with no doc naming the app and a doc whose frontmatter cannot be read are warnings in the build report; the app is then shown as not loaded, and the build goes on. `design:` that is not a path is E105. The report also lists every app no design was found for, so an empty Inside view is never a mystery.

## Links out of the vault

A page may say where its work lives outside the vault, as `links:` in its frontmatter: a map of label to URL, such as `links: {Tracker: "https://tracker.example.com/browse/BOOK-12"}` on an epic or `links: {Confluence: "https://wiki.example.com/x/BOOK", GitHub: "https://github.example.com/acme/booking"}` on an app page. A contract or an outside party, which are items rather than pages, holds them in a `**Links:**` bullet of Markdown links: `- **Links:** [API spec](https://docs.example.com/tidepay/openapi.yaml), [Docs](https://docs.example.com/tidepay)`.

When many pages link one tool, `.vela.yaml` may say once where it lives, as `link_templates: {Tracker: "https://tracker.example.com/browse/{key}"}`. A page then writes only the key, `links: {Tracker: BOOK-12}`, and `{key}` is filled from it. A link that is neither an `http`, `https` or `file://` URL nor a key for a label with a template, a `**Links:**` bullet with no Markdown link, or a template with no `{key}`, is E105. Vela reads links and checks their form; it never opens one, so `vela check` stays offline. A `file://` link names a local clone, which `vela explore` reads for a team's design (see Team design docs); views draw no chip for it. Boundary asks where each app's code and wiki live and whether an outside party has an API spec, epics asks for the tracker item, and handoff confirms them; each is the user's to give or skip, and a skip writes nothing. `vela capture` counts how many apps and epics have one.

## Epics and traceability

An epic page holds a description, the owning team (written as `**Owning team:**` and a handle in the description, a label vela knows), 4 to 7 numbered acceptance criteria, dependencies, rollout notes and what is out of scope. Its trace data is the frontmatter lists; the `traces-to` block shows them as links. Each acceptance criterion describes behavior a tester can see at a contract or flow boundary, never inside a container.

A criterion is written in plain words: it names the contract or flow by its name ("the calendar entries", "the prep-note flow"), and the requirement it comes from, the contract and the flow go on a `- Trace:` line under it (`- Trace: CAP-001.FR1, CON-001, FLO-001`). The boundary test reads that line: a criterion needs at least one contract or flow on it. More than about seven criteria is a signal to split the epic (W364 warns past nine); criteria may sit under `###` subheadings of about five, which do not end the acceptance-criteria section. The page opens with a two or three sentence summary of what the epic does and what is still open.

A concern marker ends an acceptance criterion with the concern's name in brackets, `[testing]` for `concern-testing`. One criterion may carry several, `[security] [data]`. A criterion whose text starts with `~~` is struck and its markers count for nothing.

Five trace rules run once the vault holds an epic, and T7 alone runs as soon as it holds an app page, because allocation comes before epics. They are warnings in `vela check` and errors under `vela check --gate epics`, which is run before anyone calls an app's epics complete. The same gate fails on a high-severity question nobody has disposed (E805, under Questions and the ledger).

| Rule | Passes when | Codes |
|---|---|---|
| T1 | Every capability whose `change` is not `unchanged` is in some epic's `delivers` | W501, E501 |
| T2 | Every contract whose `**Change:**` is `new` or `changed` is in some epic's `delivers`. A contract with an external `**Provider:**` may be in `consumes` instead. | W502, E502 |
| T4 | Every `addressed` cell is covered: a waiver, or an acceptance criterion with the concern's marker on an epic whose `apps` lists the app. An Ownership cell is covered by any epic whose `apps` lists the app. | W503, E503 |
| T6 | No epic has an empty `delivers` | W504, E504 |
| T7 | Every functional requirement at `assumption`, `fact` or `decided` is carried by at least one app's `## Requirements allocated` table | W505, E505 |

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

Then the acceptance-criteria list: every epic the app's team owns is `decided`, and `vela check --gate epics` exits 0.

In the PR that sets `handed_off`, run `vela handoff <APP-id>`. It writes `handoffs/<APP-id>.md`: every ID in the app's slice (the app page, its runtime page, the contracts it provides and consumes, the functional requirements its allocation rows carry, the epics whose `apps` lists it, and the open unknowns that block any of them), each with its state and a hash of its text, and the commit it was written at. The hash leaves out generated blocks, the `last_verified`, `verified_by` and `handed_off` lines, and `**Confirmed by:**` bullets, so rendering or rereading a page, or an owner confirming a decision made on their behalf, changes nothing. The hash also ignores trailing whitespace on a line, but a changed blank line or column padding in a table counts as a change. `vela handoff` writes nothing while `vela check` has errors, and never overwrites a manifest unless given `--replace`.

`vela handoff verify <APP-id>` lists every item changed, added or removed since. It exits 1 when something the senior accepted changed or left the slice, and 0 when the only news is an added item.

A senior who disputes a boundary or contract after handoff, or an owner who disputes a decision made on their behalf, raises a challenge: an open unknown with the senior as owner that blocks the item, and a `**Dissent:**` line on it. The item's state and text stay as they are, so the check fails with E316 until the solution lead answers. To reopen an epic, set it to `reopened`. A `reopened` epic counts as not decided until a Grill decides it again. A Grill decides a `reopened` epic as it decides a `draft` one, and its `## Changes` row reads `| EPC-nnn | reopened | decided | [[<session id>#^cNN]] |`. The red check is deliberate: it blocks the merge wherever vela-check is a required check, so a challenge cannot merge while `main` still reads `decided` with an open blocker. The solution lead answers on the challenge branch, by resolving the unknown with a Grill or by setting the item back, and then the check turns green. START's "Answer a challenge" path opens that answer session on the branch, and close pushes to it and comments on the challenge PR instead of opening a second one.
