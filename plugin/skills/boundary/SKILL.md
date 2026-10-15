---
name: boundary
description: "Cut a decided direction into apps: read back one boundary sheet per app, with a case table for each contract, and write it at assumption."
argument-hint: "[the decided item, or an app]"
disable-model-invocation: true
---

# Boundary

Turn a decided direction into apps a team lead can take. Until an app page exists, epics and handoff have nothing to work on. Boundary never decides. Every page this session writes is an `assumption`, never `decided`, and a concern cell is never `addressed`: only a grill decides one.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from"). Read a page format one section at a time with `vela conventions "<section>"`: "Frontmatter", "Fact bullets" for contracts, "Fact tables" for containers, "Concern cells and waivers", "Areas and stages" for the ladder. Relay each `--for-lead` output's plain lines; reason over `--json`. When a command turns an item down, relay its reason and do what it says. When a command can't express what the lead wants, say so and stop.

**How you talk to the lead.** Answer first, then at most about four things to judge, one question at a time, each with a recommendation that holds under pushback (`CONVERSATION-VOICE.md`, rule 7). Name things, in your own sentences as well as in what a command prints: an ID only where the lead has to act on it. States in words: "just an idea" (`inkling`), "not decided yet" (`assumption`), "confirmed" (`fact`); "the plan", not the vault. Names in American spelling, capitalized ones too ("Summarizer", not "Summariser"): the spelling check skips capitalized words. A read-back by name:

> Not this: "APP-agent provides CON-003 to APP-admin-console, at assumption; UNK-051 blocks it."
>
> This: "The desktop agent gives the admin console its consent list. That's not decided yet, and it waits on one open question: who signs off the data notice. Priya is chasing it by 21 October."

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `boundary`. Read the Boundary row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read the direction: `04-solution-strategy.md` and every page it links for the picked option, `03-context-and-scope.md` for the systems today and the apps in and out of scope, the building-blocks pages, `06-runtime/06-flows.md`, the concern pages, the capability pages' functional requirements, and the open questions and risks that block any of them. If the direction is not `decided`, say so and name what is still open: an app cut on an undecided direction may be cut again. Go on only if the user says to, recorded as an override as `START.md` says.

## 2. Find the seams, then offer the cuts

Before any cut, ask how the product comes apart, in the user's own words, a question or two at a time: the question a business analyst asks before drawing a context diagram. What are the separate things someone will stand up, own, release or switch off? Don't let the shape's wording (a note, a digest, "one helper") answer it for them. Ask:

- "Which parts run on a person's own device, which run somewhere shared that your people operate, and which does an administrator or support person open?"
- "Would different teams build or run any of these, or would any ship on its own schedule?"
- "Could any part be thrown away and rebuilt without losing something people rely on, such as who agreed to what, or what each person may see?"
- "Who keeps the record of who consented, who signed in, and what access was granted? Is that a part of one of the above, or a thing of its own?"

Capture each answer in the user's words. Every part they name ends up in the cuts, as an app or as "not an app" with its reason. A part only the sources name (a service in the one-pager, an admin step in the tenant note, a consent or identity owner) you offer as `(claude)`, with the source, and the user keeps or drops it. Offer consent and identity as an app of their own whenever a source shows a different owner, a different lifecycle, or an approval outside the product team, not hidden as a concern. A user who says it is one thing gets the single-app cut first, with their reason recorded; never force a split they reject.

Offer 2 or 3 ways to cut the direction into apps, never one and never more than three. A cut names every app it touches and what happens to each, said in words: a new app, one we change, one we connect to as it is, one we leave alone, one we retire (written `new`, `changed`, `integrated`, `unchanged`, `retired`). In a line or two it says:

- which app owns each job the direction needs, and which job no app owns yet;
- what it makes easy and what it makes hard: an extra service to run, a link held in two places, a team with no owner;
- which decided item, source or open question each claim rests on.

Test each cut against the functional requirements: write the cuts to `.vela/cuts.json` in the shape `vela boundary cover --help` prints, run `vela boundary cover --cut .vela/cuts.json --for-lead`, and relay which requirements each cut carries whole, splits across apps (each split needs a contract) or leaves with no app. The count is the command's; the trade-offs are yours to say, a line per cut. If the plan has no functional requirements yet, say so and offer `/vela:requirements` first.

Capture each cut as a `[thought] (claude)` line (`vela record add`) and say which you prefer and why. Capture the user's reaction to each, the pick, and each rejected cut with its reason. If they reject them all, capture why and offer new cuts. Write the pick with `vela add cut --for-lead`, its apps and the cuts that lost with their reasons (`vela add cut --help`); it marks the pick's capture `→ keep: [[05-building-blocks#<the picked cut>|cut]] (assumption)`.

Then ask for the domains once, for every app together: what do the lead's people call the area of the business each app sits in (Channels, Payments and Learning, say), and are any two apps really one area? Offer names from `03-context-and-scope.md`, the glossary and the domains other pages already use, so spellings converge; never invent an area your people don't use. A confirmed name goes on the app's stub, and on a capability page when the user names one for it. An app given no area keeps none, recorded as an override, never blocked.

Then stub every new or changed app of the cut, so every later link has a page to point at: `vela add app-stub --for-lead` with its name, slug, change, owner, domain and the pick's capture (`vela add app-stub --help`). `vela next` sends a stub back to Boundary, so an app this session doesn't reach is never lost. Checkpoint as section 4 says.

## 3. Read back one boundary sheet per app

Draw the tracer candidate's flows first. The tracer is the first thin path through the apps, the first slice; the first time you say "tracer" or "slice" to the lead, say what it means in the words `vela terms` prints. Before the first sheet, offer the journey that crosses the most of the cut's apps, from the user's words and the sources, and read its steps back (item 8) before any other flow, so its pages exist when the Releases session chooses the tracer.

Record the answer so releases does not ask again: a capture of the path in the lead's words, marked at once (the `--mark` of `vela record add`) `→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)`, and the flow page's opening sentence, "We build this journey first, as the first thin path: ..." (Releases finds the page by "first thin path"). A user with no candidate yet is not held up: say releases will ask once, and carry on.

When a flow's steps and its contracts' case tables are confirmed, draw it as the strict sequence diagram (`vela conventions "Flow check"`).

Take the stubs one at a time. Show each sheet as a numbered list with these plain labels:

1. **Does:** what the app decides or keeps, in the domain's words, and the domain the user named for it.
2. **Doesn't do:** the jobs that stay elsewhere, each naming the app or party that keeps it.
3. **Main parts:** each container and its job.
4. **What it offers other apps:** each contract by its name, what goes each way, and who uses it.
5. **What it needs from others:** each contract it relies on, from another app or an outside provider. For each outside party or third-party contract, ask whether there is an API spec or docs; a link is enough, and the user may skip.
6. **When something fails:** what the app and each consumer do when it, or something it needs, is down or slow.
7. **Capabilities:** each business capability it delivers or changes, in the domain's words ("teach a stock trade"), and whether that is new, extended, replaced, narrowed or retired (`new`, `extend`, `replace`, `narrow`, `retire`).
8. **Journeys:** each end-to-end journey it takes part in ("a reader practices a trade"): its steps in order, each naming the app and the contract or capability it uses. For each step that hands something between two lanes, read back who sends and who receives, with your guess: "Step 3: Booking sends Payments the order ID, through Order identity. Does Booking start that, or does Payments ask for it?" A step with no hand-over, such as the reader opting in, needs no sender.
9. **Concerns:** one line per concern page, in words: a question to answer first (`unknown`), the existing practice holds (`unchanged`, for a changed app), doesn't apply and why (`n/a`), or nobody has looked yet (`unexamined`). Never `addressed`: only a grill decides one.
10. **Where it lives:** ask where its code and its team's wiki live, for the links or a skip. A link is only what the user gives you; never guess one from the app's name, and a skip is not recorded.

**The case table for each contract in item 4.** A contract isn't read back as one sentence about what crosses; it gets a table of every way the provider can answer (`vela conventions "Fact bullets"`). Draft the rows from what the contract's text, the sources and the failure lines already say, mark each `(claude)`, and show them. Invent nothing the text doesn't support: a case you can't support is asked, not guessed. Ask one question per open case, each with your recommendation: "When the stock check can't find the item, what does Stock say back? Recommended: Stock says the item is unknown and names it, so Shop can tell the customer why." Ask the same way whether it can time out, how often the caller retries, and what proves the caller's identity. A row with no yes is left out. A contract with no table stays a warning for the next session, said as "Nobody has written down every answer Order identity can give yet", never filled with a guess.

When you've written or changed a case table, run `vela check-slice --changed --for-lead`. Tell the lead which slices it checked and why, in your own words, and read out each finding with its owners. Settle each there as a case row, a branch or an open question; don't write a finding into the page yourself.

Label every line with what it rests on: a source, a decided item and the grill that decided it, the user's own words, or `(claude)` for your proposal; a line with nothing under it is a proposal and says so. Read the sheet back in two groups, "what it does and doesn't" (items 1 to 3) and "how it connects" (4 to 10), and write a line only after the yes `START.md` defines; a yes to a group counts for the lines in it. A correction replaces the line and needs its own yes. A line the user can't answer becomes an open question: ask who would actually know (`MODES.md`, "Unknowns") and write it as section 4 says.

## 4. Write the confirmed lines

After each sheet, write what was confirmed. `${CLAUDE_PLUGIN_ROOT}/skills/boundary/PAGES.md` says what each page holds. Commands write the templated parts, number each new ID and mark its capture:

- Each contract the app provides: `vela add contract --for-lead`, with its provider, name, what goes each way, consumers, change policy and capture (`vela add contract --help`). It writes the required bullets on the provider's page and won't write `decided`. Add the case table the lead confirmed under it.
- Each open question: `vela add unknown --for-lead`, with its owner, who to ask, what it blocks and its capture, in the same checkpoint as the line that links it.
- The rest you write by hand as PAGES says: the stub becomes the app page, then its containers, runtime page, concern cells, capabilities and flows. Mark each capture with `vela apply` on a `marks` file (`vela apply --schema marks`), `→ keep: [[<page>#<heading>|<ID>]] (assumption)`. No command writes the `## Changes` row for an app page or a runtime page yet, so add each, `| <ID> | <from> | <to> | [[<id>#^cNN]] |`. Containers and concern cells have no ID; they go in their app's capture. These marks are an exception to leaving marks until close, and close leaves them alone.

The checkpoint: `vela render`, then `vela check --for-lead`, fixing every error the new pages cause, then `vela close stage --checkpoint --for-lead`, which commits by exact path.

## 5. Review the new apps and contracts

Once every sheet is written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pages are written" and the new app, contract and runtime pages as its focus: `vela reviewers prepare --checkpoint "after the pages are written" --focus <those pages> --for-lead`. Each new app and contract is now a subject the catalog owes questions about: run `vela questions --subject <ID>` for each and show the copies it owes. Show the digest and capture what they take, as REVIEW says.

## 6. Finish

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". The next step is a grill on each app's page and its contracts; say the line the lead types by the app's name, such as `/vela:grill Desktop agent`.
