# Modes

Each mode skill holds only what is particular to it. This table is what every mode shares: when it ends, what Claude must do, and what it must not. When a mode ends, or the lead says they are done, `START.md` says under "Closing a session" how close starts: on the lead's word, never on its own. The eval cases grade the last column. Each "must not" is the default when nobody says otherwise. The user may override any of them, and Claude then records the override as `START.md` says under "The user may override any rule".

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
| Challenge (`challenge`) | the challenge is an open unknown and its PR is open, or the senior stops | quote the senior's words; write one open unknown the senior owns that blocks the item, and one `**Dissent:**` line on the item | change the item's state or text, decide anything, or argue the item's side |
| Answer (`answer`) | the challenged item is decided again, set back, or its unknown resolved, or the lead stops | work on the challenge's own branch; decide only inside a Grill part, with `grill` added to `modes` | open a second PR, or decide anything outside a Grill |

## Team skills

These two run in the team's clone of the vault, after a design is complete, and write no session record. Neither is a session mode: a vault session's `modes` list never holds them.

- **Breakdown** (`/vela:breakdown`) ends when the plan is complete or complete-with-gaps, or the person stops. Claude starts the first story from the team's piece of the tracer flow, quotes each story's criteria word for word from the vault, and says for each story whether it fits before the next release date, or that it cannot tell and why. It does not invent a criterion, plan around a person the design or the vault does not name, or split, merge or reorder agreed stories without a yes.
- **Tickets** (`/vela:tickets`) ends when the output file is written and the summary said. Claude checks the plan against the vault before writing anything, asks which output the person wants, and stops after the summary. It creates or changes nothing in an outside system without an explicit yes.

## Who writes what, and when

| Mode | During the session | At close |
|---|---|---|
| `dump` | captures only, and the `## Reviews` of its checkpoint | promoted items at `inkling`, unknowns with owner and ask-by, question ledger rows |
| `discover` | `sources.md` rows; facts after each correction round, with sources, and the parties and stored value they name | prose, question ledger rows |
| `shape` | captures only, and the `## Reviews` of its checkpoint | `assumption` items with `**Options considered:**`, question ledger rows |
| `boundary` | a stub page and `unexamined` concern rows for each app of the picked cut; then, after each sheet's yeses, the app page, its containers and contracts, its runtime page, its capability and flow pages, its concern cells and the unknowns they link, at `assumption`, with a checkpoint commit | prose, question ledger rows |
| `grill` | each decided item as its branch closes, with a checkpoint commit | prose, read-back, question ledger rows, decision records for decided pages, glossary terms |
| `epics` | `draft` epic pages, bullets and criteria only; `decided` only inside its Grill part | epic description paragraphs |
| `requirements` | capability pages it needs; requirements on them at `assumption`, each with a checkpoint commit; unknowns | prose |
| `allocate` | rows in each app's `## Requirements allocated` table at `assumption`, and any missing contract it proposed, with a checkpoint commit; unknowns | prose |
| `releases` | `04b-releases.md`: each release's heading, Target, State and rows at `assumption`, with a checkpoint commit; unknowns | prose |
| `challenge` | the unknown and the `**Dissent:**` line, then its own PR | nothing: a challenge closes its own record |
| `answer` | what its Grill decides, or the item set back, on the challenge's branch | a push to that branch and a comment on the challenge PR, never a new PR |
| `breakdown` | `docs/plan/<slug>-breakdown.md` and `docs/plan/<slug>-audit.md` in the team's vault clone, on the design's branch, with a commit per agreed story (no session record) | nothing |
| `tickets` | `docs/work/tickets.md`, or `docs/work/tickets.csv` with its README, once the person picks | nothing |

No mode writes inside a generated block. `vela render` fills them. Close runs it, and so does `epics`, mid-session, to read its frontier. Whoever runs it stages every file it reports, by exact path.

## Team-side sessions

Once an app is handed off, its team designs it. `/vela:design --app APP-x` runs from the vault root with the app's senior, opens no session record and writes no vault page: it writes `docs/tech-design/<slug>.md`, its ADRs under `docs/adr/` and `CONTEXT.md` on a `design/<slug>` branch, and opens a pull request at the end. A gap it finds in the vault goes back through `/vela:challenge`. `vela next` adds a team-side line for each handed-off app with no design doc yet.

## Where to start

`vela next` names the one app and mode to work on next, and `vela status` shows every app's stage, certainty mix and oldest open unknown. START runs `vela next`. While no app page exists, it suggests a Dump or a Discover, or a Boundary once `04-solution-strategy.md` is `decided`. Both follow the rules in `vela conventions "Progress and next step"`.

## Unknowns

Any question nobody present can answer becomes an unknown on `11-unknowns-and-risks.md`. Take its number from `vela next-id UNK` before you name it to the lead or write it, because an open session branch may already hold the number you would guess; the same command numbers a `CON` or an `EPC`, and `vela check` fails with E208 when two headings share an ID. It has `**Owner:**` starting with a handle, `**Ask by:**` and `**Blocks:**`. When the owner is not the person who holds the answer, add `**Ask:**` with that person's handle or role, rather than a parenthesis after the owner. The moment is concrete: when the lead cannot answer a line, ask who would actually know, and if that is not the owner, for a name or a role (outside counsel, say). Put it in your own words. Boundary, Requirements, Allocate, Releases and Epics each do this; leave the line out when the owner holds the answer.

- **Ask the lead first.** Before an unknown waits on anyone else, ask the lead whether they know the answer now, and how they know it. A first-hand answer gets its own row in `sources.md` and is captured with its source. A document they can name goes to Discover.
- **Ask what they might not know they need.** In Discover, Shape and Grill, once before the session ends, ask three things in plain words, in your own phrasing: who has to agree or be consulted before this goes live (employee representatives, legal, security, data protection, a client or partner whose contract it touches, as examples); what someone who has launched something like this would check that we have not; and who outside the room is affected and has not been named. A business analyst asks this at the end of every stakeholder round, because the lead cannot name a requirement nobody has told them about. Each answer is a capture. Each "honestly not sure" becomes an unknown with an owner and an ask-by date. Do not supply the answer yourself from general knowledge: a gap you name stays a question for the lead until a source or a person settles it. You may use what you know of the domain to ask, never to answer. "In Germany a system that can monitor staff normally needs the works council's agreement, not only its reading. Has anyone checked which this is?" is a question; "the council has a veto" written on a page is not. Ask the two or three such questions the initiative most obviously raises, once, in plain words, and write each as an unknown with a person to ask if the lead does not know. Say the knowledge is yours ("as far as I know") so it is never mistaken for a source.
- **The page keeps its shape.** `11-unknowns-and-risks.md` is a list page: `house-voice` ("Pages that are mostly a list") says how it opens and how it groups. Each line is the plain name, who is asked and by when, and what it holds up. A new unknown joins its group; the opening is not extended to mention it.
- **The lead does the asking.** The unknown's owner and ask-by date are the record of who is asked and by when. Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to. A research task Claude does now with a source may still be offered.
- **An answered unknown is resolved.** When a session learns the answer to an open unknown, from a source it reads or from the lead first-hand with its own row in `sources.md`, write it resolved, as `vela conventions "Fact bullets"` says: `**State:** resolved`, an `**Outcome:**` that says the answer with its source linked on the words, `**Resolved in:**` linking this session, and no `**Ask by:**`. Change what it blocked only as the item's own mode allows: a Grill decides, and Discover writes the fact. An unknown answered in part stays open, with the part that is known in `**Notes:**`.
- **A blocked session ends.** When an open unknown or a failed gate leaves nothing the session can work on, say once what is blocked and by what, and offer the override (`START.md`, "The user may override any rule"), another mode, or stopping. If the lead takes none, stop: say what is recorded and which command to run when the answer comes. Never fill a blocked session with other work.

When two sources or two people disagree, write an unknown that names both. Do not pick one.

## Owed questions

What a session must ask comes from code, not from this file. `vela questions` lists the copies the question catalog owes, and a review checkpoint adds what one focused reviewer per focus area finds, as `REVIEW.md` says. Dump runs one after its pre-mortem, Discover after its read-back, Shape before it shows its options, Requirements once a capability's requirements are written, Boundary once its app pages are written, Allocate once its rows are written, and a Grill on its agenda. No question is dropped and none is owed a quota: the digest ranks them, the lead is shown at most three at a time, once per session (`REVIEW.md`, section 5), and the rest stay open and visible in the ledger. Between checkpoints, ask whatever the work needs.
