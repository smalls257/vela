# Modes

What every mode shares: when it ends, what Claude must do, and what it must not. Close starts only on the lead's word. Each "must not" is a default. The user may override any of them, as `START.md` says.

| Mode | Ends when | Claude must | Claude must not |
|---|---|---|---|
| Dump & Diverge (`dump`) | the user stops, or after the pre-mortem and its review checkpoint | build on each idea; label its own ideas `(claude)` and its wild ones `[wild]` | push back, judge, or write to any page before close, except an item the lead settles |
| Discover (`discover`) | every ranked source is read and the user has corrected "here's what I think exists" | show its reading as a numbered list before writing anything; cite a `SRC-nn` for every fact | state anything from general knowledge as a fact, or copy document text into the vault |
| Shape (`shape`) | the user picks an option, or rejects them all | offer 2 or 3 options with trade-offs; record each rejected one with its reason | offer one option or more than three |
| Boundary (`boundary`) | every app of the picked cut has its sheet written or its open lines listed, or the user stops | offer the lead's cut, and one alternative only when there is a real one; read back one sheet per app as a numbered list and write only the lines with an explicit yes; label each line with what it rests on | write a concern cell as `addressed`, or write a line nobody said yes to |
| Grill (`grill`) | the agenda is empty, or the user stops | ask one question at a time with a recommended answer; keep the recommendation under pushback until the user gives a reason | answer its own questions, decide without the owner unless the user decides on the owner's behalf, or batch writes |
| Epics (`epics`) | every chosen team's gaps are closed or listed, or the user stops | read the `traceability` block; offer 2 or 3 cuts; draft criteria at a contract or flow boundary; ask for an explicit yes per criterion, then a read-back; run `check --gate epics`; say whether the team's first epic is on release one's tracer | write a requirement into an epic, name a component or technology in a criterion, or write `decided` without a yes on every criterion |
| Requirements (`requirements`) | every capability in scope has its requirements written or its open lines listed, or the user stops | stay at the "what" and name no app; read back each requirement and its acceptance criteria and write only what has an explicit yes | write `fact`, name an app, or write under `docs/requirements/` |
| Allocate (`allocate`) | every requirement in scope is carried or its gap is an unknown, or the user stops | read back each requirement's shares and the contracts they cross; write only lines with an explicit yes; propose a missing contract at `assumption` | allocate inside one app, or reword a requirement to fit |
| Releases (`releases`) | every requirement at `assumption` or later is on a release or marked "later, no date", or the user stops | ask one question at a time with a recommended answer; say each release's date and who sees it; start from the first thin path boundary recorded, offer the tracer from the flows with a recommendation, and record what it leaves out; write only what has an explicit yes | invent a date, or write a requirement on a release the user did not place it on |
| Challenge (`challenge`) | the challenge is an open unknown and its PR is open, or the team lead stops | quote the team lead's words; write one open unknown the team lead owns that blocks the item, and one `**Dissent:**` line on the item | change the item's state or text, decide anything, or argue the item's side |
| Answer (`answer`) | the challenged item is decided again, set back, or its unknown resolved, or the lead stops | work on the challenge's own branch | open a second PR |

Shape, Allocate, Requirements and Releases run when `vela next` names them.

No mode writes inside a generated block. Close runs `vela render`, and so does `epics` mid-session.

## Unknowns

A question nobody present can answer becomes an unknown, written with `vela add unknown`. The owner is the lead, who chases it.

- **Ask the lead first.** Ask whether they know the answer now, and how. A first-hand answer gets its own row in `sources.md` and is captured with it; a document they can name goes to Discover.
- **Then ask who would actually know.** Someone other than the lead goes on `--ask` as a handle or a role spelled out ("the data protection officer", not "DPO"). When the lead isn't sure who or by when, propose one of each and ask, with the reason for the date: "I'd ask the operations manager before March 1, because the pilot starts two weeks later. OK?" (an override's end date too). Capture the answer, and file `--ask-by` only with that capture behind it; with no date agreed, leave it off and say so. If they stay unsure who, leave `--ask` off.
- **Ask what they might not know they need.** In Discover, Shape and a grill, once before the session ends, ask in your own words who has to agree or be consulted before this goes live (employee representatives, legal, security, data protection, a client or partner whose contract it touches) and what someone who has launched something like this would check. Who is affected but not yet in the room (OPS-06) and anything regulated or licensed (REG-02) are the catalog's questions: ask them there, once, never again here. Each answer is a capture; each "honestly not sure" is an unknown. Use what you know of the domain to ask, never to answer, and say the knowledge is yours ("as far as I know"). "In many cities a dock on the pavement needs a street-works permit, not only a nod from the council. Has anyone checked which these need?" is a question; "the council must issue a permit" written on a page is not.
- **The lead does the asking.** Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to.
- **An answered unknown is resolved** with a `resolve` decision through `vela apply`; what it blocked changes only as that item's mode allows. Answered in part, it stays open.
- **A blocked session ends.** When an open unknown or a failed gate leaves nothing the session can work on, say once what is blocked and by what, and offer the override, another mode, or stopping. If the lead takes none, say what's recorded and what to run when the answer comes, and stop. Never fill a blocked session with other work.

When two sources or two people disagree, write an unknown that names both. Don't pick one.

## Owed questions

`vela questions` lists what the catalog owes and each skill's review checkpoint (`REVIEW.md`) adds what the reviewers find. No question is owed a quota. Between checkpoints, ask whatever the work needs.
