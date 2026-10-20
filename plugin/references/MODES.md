# Modes

Each mode skill holds only what is particular to it. This table is what every mode shares: when it ends, what Claude must do, and what it must not. When a mode ends, or the lead says they are done, `START.md` says under "Closing a session" how close starts: on the lead's word, never on its own. The eval cases grade the last column. Each "must not" is a default. The user may override any of them, as `START.md` says under "The user may override any rule".

| Mode | Ends when | Claude must | Claude must not |
|---|---|---|---|
| Dump & Diverge (`dump`) | the user stops, or after the pre-mortem and its review checkpoint | build on each idea; label its own ideas `(claude)` and its wild ones `[wild]` | push back, judge, or write to any page before close |
| Discover (`discover`) | every ranked source is read and the user has corrected "here's what I think exists" | show its reading as a numbered list before writing anything; cite a `SRC-nn` for every fact | state anything from general knowledge as a fact, or copy document text into the vault |
| Shape (`shape`) | the user picks an option, or rejects them all | offer 2 or 3 options with trade-offs; record each rejected one with its reason | offer one option or more than three; write `decided` |
| Boundary (`boundary`) | every app of the picked cut has its sheet written or its open lines listed, or the user stops | offer 2 or 3 cuts into apps; read back one sheet per app as a numbered list and write only the lines with an explicit yes; label each line with what it rests on | write `decided` or a concern cell as `addressed`, offer one cut or more than three, or write a line nobody said yes to |
| Grill (`grill`) | the agenda is empty, or the user stops | ask one question at a time with a recommended answer; keep the recommendation under pushback until the user gives a reason | answer its own questions, decide without the owner unless the user decides on the owner's behalf, or batch writes |
| Epics (`epics`) | every chosen team's gaps are closed or listed, or the user stops | read the `traceability` block; offer 2 or 3 cuts; draft criteria at a contract or flow boundary; ask for an explicit yes per criterion, then a read-back; run `check --gate epics`; say whether the team's first epic is on release one's tracer | write a requirement into an epic, name a component or technology in a criterion, or write `decided` without a yes on every criterion |
| Requirements (`requirements`) | every capability in scope has its requirements written or its open lines listed, or the user stops | stay at the "what" and name no app; read back each requirement and its acceptance criteria and write only what has an explicit yes | write `decided` or `fact`, name an app, or write under `docs/requirements/` |
| Allocate (`allocate`) | every requirement in scope is carried or its gap is an unknown, or the user stops | read back each requirement's shares and the contracts they cross; write only lines with an explicit yes; propose a missing contract at `assumption` | write `decided`, allocate inside one app, or reword a requirement to fit |
| Releases (`releases`) | every requirement at `assumption` or later is on a release or marked "later, no date", or the user stops | ask one question at a time with a recommended answer; say each release's date and who sees it; start from the first thin path boundary recorded, offer the tracer from the flows with a recommendation, and record what it leaves out; write only what has an explicit yes | write `decided`, invent a date, or write a requirement on a release the user did not place it on |
| Challenge (`challenge`) | the challenge is an open unknown and its PR is open, or the team lead stops | quote the team lead's words; write one open unknown the team lead owns that blocks the item, and one `**Dissent:**` line on the item | change the item's state or text, decide anything, or argue the item's side |
| Answer (`answer`) | the challenged item is decided again, set back, or its unknown resolved, or the lead stops | work on the challenge's own branch; decide only inside a grill part, with `grill` added to `modes` | open a second PR, or decide anything outside a grill |

## Team skills

These two run in the team's clone after a design is complete. Neither is a session mode, and neither writes a session record.

- **Breakdown** (`/vela:breakdown`) ends when the plan is complete or complete-with-gaps, or the person stops. Claude starts the first story from the team's piece of the tracer flow, quotes each story's criteria word for word from the vault, and says for each story whether it fits before the next release date, or that it cannot tell and why. It does not invent a criterion, plan around a person the design or the vault does not name, or split, merge or reorder agreed stories without a yes.
- **Tickets** (`/vela:tickets`) ends when the output file is written and the summary said. Claude checks the plan against the vault before writing anything, asks which output the person wants, and stops after the summary. It creates or changes nothing in an outside system without an explicit yes.

## Who writes what, and when

| Mode | During the session | At close |
|---|---|---|
| `dump` | captures only, and the `## Reviews` of its checkpoint | promoted items at `inkling`, unknowns with owner, question ledger rows |
| `discover` | `sources.md` rows; facts after each correction round, with sources, and the parties and stored value they name | prose, question ledger rows |
| `shape` | captures only, and the `## Reviews` of its checkpoint | `assumption` items with `**Options considered:**`, question ledger rows |
| `boundary` | a stub page for each app of the picked cut, marked `stub: boundary` in its frontmatter, with no concern row (no row already means nobody has looked); then, after each sheet's yeses, the app page, its containers and contracts, its runtime page, its capability and flow pages, its concern cells and the unknowns they link, at `assumption`, with a checkpoint commit | prose, question ledger rows |
| `grill` | each decided item as its branch closes, with a checkpoint commit | prose, read-back, question ledger rows, decision records for decided pages, glossary terms |
| `epics` | `draft` epic pages, bullets and criteria only; `decided` only inside its grill part | epic description paragraphs |
| `requirements` | capability pages it needs; requirements on them at `assumption`, each with a checkpoint commit; unknowns | prose |
| `allocate` | rows in each app's `## Requirements allocated` table at `assumption`, and any missing contract it proposed, with a checkpoint commit; unknowns | prose |
| `releases` | `04b-releases.md`: each release's heading, Target, State and rows at `assumption`, with a checkpoint commit; unknowns | prose |
| `challenge` | the unknown and the `**Dissent:**` line, then its own PR | nothing: a challenge closes its own record |
| `answer` | what its grill decides, or the item set back, on the challenge's branch | a push to that branch and a comment on the challenge PR, never a new PR |

When the lead says a plain yes to a pick in a session that can't decide (`dump`, `discover`, `shape`, `boundary`, `requirements`, `allocate`, `releases`), run `vela decide` on it anyway: it answers that this session can't decide, marks the item ready to decide, and says to offer the lead a short grill on it now. Do as it says; never leave the yes as an assumption nobody sees again.

No mode writes inside a generated block. `vela render` fills them. Close runs it, and so does `epics`, mid-session, to read its frontier. Whoever runs it stages every file it reports, by exact path.

## Team-side sessions

Once an app is handed off, its team designs it. `/vela:design --app APP-x` runs from the vault root with the app's team lead, opens no session record and writes no vault page: it writes `docs/tech-design/<slug>.md`, its ADRs under `docs/adr/` and `CONTEXT.md` on its own branch, and opens a pull request at the end. A gap it finds in the plan goes back through `/vela:challenge`.

## Where to start

`vela next` names the one app and mode to work on next, and `vela status` shows every app's stage, certainty mix and oldest open unknown. START offers the next step from `vela session brief`. It's a suggestion, never a decision.

## Unknowns

Any question nobody present can answer becomes an unknown: write it with `vela add unknown`, which numbers it and links what it holds up. It never picks an ask-by date. The owner is the lead who chases it. When the lead can't answer a line, ask who would actually know, in your own words; if that isn't the owner, it goes on `--ask` as a handle or a role spelled out ("the data protection officer", not "DPO"). Boundary, Requirements, Allocate, Releases and Epics each do this.

- **Propose who and by when, then ask.** The same goes for an override's end date and any owner the lead didn't name. When the lead isn't sure who would know or by when it needs an answer, propose one of each and ask, with the reason for the date, in the conversation voice: a role, and a date with why ("I'd ask the operations manager by 1 March, because the pilot starts two weeks later. OK?"). Capture the lead's answer. File `--ask-by` only with that capture behind it (`--capture`): the lead's own date, or their yes to yours. `vela add unknown` won't file a date the lead's words don't back, and it never picks one, so with no date agreed the entry has no `Ask by` line and the page says nobody has set one. Say so plainly and move on. `--owner` stays the lead's own handle, which the command fills in; never name anyone else there. If they stay unsure about who would know, leave `--ask` off, so the page names nobody to ask yet.
- **Ask the lead first.** Before an unknown waits on anyone else, ask the lead whether they know the answer now, and how they know it. A first-hand answer gets its own row in `sources.md` and is captured with its source. A document they can name goes to Discover.
- **Ask what they might not know they need.** In Discover, Shape and a grill, once before the session ends, ask three things in plain words, in your own phrasing: who has to agree or be consulted before this goes live (employee representatives, legal, security, data protection, a client or partner whose contract it touches); what someone who has launched something like this would check that we haven't; and who outside the room is affected and hasn't been named. Each answer is a capture; each "honestly not sure" becomes an unknown. You may use what you know of the domain to ask, never to answer, and say the knowledge is yours ("as far as I know"). "In many cities a dock on the pavement needs a street-works permit, not only a nod from the council. Has anyone checked which these need?" is a question; "the council must issue a permit" written on a page is not.
- **The page keeps its shape.** `11-unknowns-and-risks.md` is a list page (`house-voice`, "Pages that are mostly a list"): each line is the plain name, who is asked and by when, and what it holds up. A new unknown joins its group; the opening isn't extended to mention it.
- **The lead does the asking.** Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to. A research task Claude does now with a source may still be offered.
- **An answered unknown is resolved.** When a session learns the answer, from a source it reads or from the lead first-hand with its own row in `sources.md`, record it with a `resolve` decision through `vela apply`. Change what it blocked only as the item's own mode allows: a grill decides, and Discover writes the fact. An unknown answered in part stays open, with the known part in its notes.
- **A blocked session ends.** When an open unknown or a failed gate leaves nothing the session can work on, say once what is blocked and by what, and offer the override, another mode, or stopping. If the lead takes none, stop: say what's recorded and what to run when the answer comes. Never fill a blocked session with other work.

When two sources or two people disagree, write an unknown that names both. Don't pick one.

## Owed questions

What a session must ask comes from code: `vela questions` lists what the question catalog owes, and a review checkpoint (`REVIEW.md`) adds what one focused reviewer per area finds. Dump runs one after its pre-mortem, Discover after its read-back, Shape before it shows its options, Requirements once a capability's requirements are written, Boundary once its app pages are written, Allocate once its rows are written, and a grill on its agenda. No question is dropped and none is owed a quota: the lead is shown at most three at a time, once per session, and the rest stay open in the ledger. Between checkpoints, ask whatever the work needs.
