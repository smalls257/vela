---
name: boundary
description: Cut a decided direction into apps, read back one boundary sheet per app, and write the confirmed lines at assumption. Use when the direction is decided and no app page says who builds what.
argument-hint: "[the decided item, or an app]"
disable-model-invocation: true
---

# Boundary

Turn a decided direction into apps a team senior can take. Until an app page exists, the catalog's app and contract questions are owed by nothing, `vela status` has nothing to show, and epics and handoff have nothing to work on. Boundary never decides. Every page this session writes is an `assumption`, never `decided`, and a concern cell is never `addressed`: only a grill decides one. The commands refuse a `decided` contract; the pages you fill by hand hold to the same rule.

Vela is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). The page formats are in `CONVENTIONS.md`, read one section at a time with `vela conventions "<section>"`: "Frontmatter", "IDs", "Fact bullets" for contracts, "Fact tables" for containers, "Concern cells and waivers", and the ladder under "Areas and stages".

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `boundary`. Read the Boundary row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read the direction: `04-solution-strategy.md` and every page it links for the picked option, `03-context-and-scope.md` for the systems today and the apps in and out of scope, the existing building-blocks pages, `06-runtime/06-flows.md`, the concern pages, the capability pages' functional requirements, and the open unknowns and risks that block any of them. If the direction is not `decided`, say so and name what is still open: an app cut on an undecided direction may be cut again. Go on only if the user says to, and record that as an override as `START.md` says.

## 2. Find the seams, then offer the cuts

Before any cut, ask how the product comes apart, in the user's own words, a question or two at a time. This is the question a business analyst asks before drawing a context diagram: what are the separate things someone will stand up, own, release or switch off? Do not let the shape's wording (a note, a digest, "one helper") answer it for them. Ask:

- "Which parts run on a person's own device, which run somewhere shared that your people operate, and which does an administrator or support person open?"
- "Would different teams build or run any of these, or would any ship on its own schedule?"
- "Could any part be thrown away and rebuilt without losing something people rely on, such as who agreed to what, or what each person may see?"
- "Who keeps the record of who consented, who signed in, and what access was granted? Is that a part of one of the above, or a thing of its own?"

Capture each answer as the user's words. Every part they name ends up in the cuts: as an app, or as an explicit "not an app" with its reason (inside another app, an outside party, later). A part the user did not name but the sources do (a service in the one-pager, an admin step in the tenant note, a consent or identity owner) is offered by you as `(claude)`, with the source, and the user keeps or drops it. Consent and identity are offered as a separate app whenever a source shows a different owner, a different lifecycle, or an approval outside the product team, not hidden as a concern or a "leave it without an app" line. The cuts then differ in where the seams go, not only in whether a cloud exists. A user who says it is one thing gets the single-app cut first, with their reason recorded; never force a split the user rejects.

Offer 2 or 3 ways to cut the direction into apps, never one and never more than three. A cut names every app it touches, each with what happens to it, said in words to the lead: a new app, an app we change, one we connect to as it is, one we leave alone, or one we retire (written `new`, `changed`, `integrated`, `unchanged` or `retired`). It says in a line or two:

- which app owns each job the direction needs, and which job no app owns yet;
- what it makes easy and what it makes hard: an extra service to run, a link held in two places, a team with no owner;
- which decided item, source or open question each claim rests on.

Test each cut against the functional requirements. Write every cut to one file, `.vela/cuts.json`, in the shape `vela boundary cover --help` prints, and run `vela boundary cover --cut .vela/cuts.json --for-lead`. Relay what it says per cut: the requirements one app carries whole, the ones split across apps (each crossing needs a contract), and the ones no app carries. The count is the command's; the trade-offs are yours to say, a line per cut. A cut that leaves a requirement with no app, or splits one with no contract to carry it, says so as a cost. If the plan has no functional requirements yet, say that, and offer `/vela:requirements` first.

Capture each cut as a `[thought] (claude)` line with `vela record add`. Say which cut you prefer and why. Capture the user's reaction to each and the cut they pick. A rejected cut gets a capture with its reason. If they reject them all, capture why and offer new cuts.

Write the pick with `vela add cut --name "<the picked cut>" --apps "<app name>=<change>" --rejected "<cut>: <reason>" --capture ^cNN --for-lead`, one `--apps` per app and one `--rejected` per cut that lost. It writes the cut on the building-blocks page with what was weighed, and marks the pick's capture `→ keep: [[05-building-blocks#<the picked cut>|cut]] (assumption)`.

Then ask for the domains, once, for every app of the picked cut together, not one by one on the sheets: what do the lead's people call the areas of the business each app sits in (Channels, Payments and Learning, say), and are any two apps really one area? Propose the names from `03-context-and-scope.md`, the glossary and the domains already on other pages, offered first so spellings converge; never invent an area your people don't use. Each name the user confirms goes on the app's stub and on a capability page when the user names one for it. An app the user gives no area keeps none, and that skip is recorded as an override, never blocked.

Then stub every app of the picked cut that is new or changed, so every later link has a page to point at: `vela add app-stub --slug <slug> --name "<the app's name>" --change <change> --owner <handle> --domain "<its domain>" --capture ^cNN --for-lead`, with `--domain` only when the user named one. It writes the page, a row on each concern page saying nobody has looked yet, and the Changes row; `vela next` sends a stub back to Boundary, so an app this session doesn't reach is never lost. Then checkpoint as section 4 says.

## 3. Read back one boundary sheet per app

Draw the tracer candidate's flows first. The tracer is the first thin path through the apps (`vela conventions "Releases"` defines it; say what it is the first time you mention it). Before the first sheet, ask what a person would do if one thin path went through all of these first. Offer the journey that crosses the most of the cut's apps, from the user's words and the sources, and read its steps back (item 8 below) before any other flow, so its flow pages exist when `/vela:releases` chooses the tracer.

Record the answer so releases does not ask again: a capture of the path in the lead's words, marked at once `→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)`, and the path as the opening sentence of that flow page ("the first thin path: ..."). A user with no candidate yet is not held up: say releases will ask once, and carry on.

When a flow's steps and its contracts' case tables are confirmed, draw it as the strict sequence diagram (`vela conventions "Flow check"`) and run `vela check-slice FLO-nnn`. Read each finding to the lead in its own words, with the apps that own it, and settle it there as a case row, a branch or an unknown; don't write a finding into the page yourself.

Take the stubs one at a time. For each, show its sheet as a numbered list:

1. **Does:** what the app decides or keeps, in the domain's words, and the domain the user named for it.
2. **Does not:** the jobs that stay elsewhere, each naming the app or party that keeps it.
3. **Containers:** each main part and its job.
4. **Provides:** each contract by its name, with what crosses the boundary in each direction and each consumer.
5. **Consumes:** each contract it relies on, provided by another app or an outside provider. For each outside party or third-party contract, ask whether there is an API spec or docs for it; a link is enough, and the user may skip.
6. **On failure:** what the app and each consumer do when it, or something it consumes, is down or slow.
7. **Capabilities:** each business capability the app delivers or changes, in the domain's words, such as "teach a stock trade", with `new`, `extend`, `replace`, `narrow` or `retire`.
8. **Flows:** each end-to-end journey the app takes part in, such as "a reader practices a trade": its steps in order, each naming the app and the contract or capability it uses. For each step that hands something between two lanes, read back who sends and who receives, with your guess, such as "Step 3: the Booking app sends the Payments app the order ID, over Order identity. Is that the direction? Tell me if Payments starts it." A step with no hand-over, such as the reader opting in, needs no sender.
9. **Concerns:** one line per concern page: `unknown` with the question that must be answered first, `unchanged` when a changed app's existing practice holds, `n/a` with why, or `unexamined`. Never `addressed`, because only a Grill decides one.
10. **Where it lives:** ask where this app's code and its team's wiki live, and for the links or a skip. A link is only what the user gives you. Never guess an address from the app's name, and a skip is not recorded.

**The case table for each contract in item 4.** A contract is not read back as one sentence about what crosses; it gets a table of every way the provider can answer (`vela conventions "Fact bullets"`: the case table). Draft it yourself from what the contract's text, the sources and the runtime failure lines already say, mark each row `(claude)`, and show the rows to the lead. The lead confirms; you invent nothing the text does not support, and a case you cannot support is asked, not guessed. Ask one question per open case, each with your recommendation: "When the stock check can't find the item, what does Stock say back? Recommended: a 409 that names the item, because Shop has to show the customer why." Ask the same way whether the contract can time out and how often the caller retries, and what proves the caller's identity. A row with no yes is left out, and the contract's missing table stays a warning for the next session to settle; it is never filled with a guess.

Label every line with what it rests on: a source, a decided item and the Grill that decided it, the user's own words, or `(claude)` for your proposal. A line with nothing under it is a proposal, and it says so. Say each app, contract and flow by its plain name when you show a sheet. Read the sheet back in two groups, "what it does and doesn't" (items 1 to 3) and "how it connects" (items 4 to 10), and write a line only after the yes `START.md` defines; a yes to a group counts for the lines in it. A correction replaces the line, and the corrected line needs its own yes. A line the user cannot answer becomes an unknown (`vela add unknown`, section 4): ask who would actually know, as `MODES.md` says under "Unknowns", and give that as `--ask`.

## 4. Write the confirmed lines

After each sheet, write what was confirmed and checkpoint. `${CLAUDE_PLUGIN_ROOT}/skills/boundary/PAGES.md` lists what each page holds: the app page, its containers, the contracts it provides and consumes, what was weighed, the runtime page, the concern cells, capabilities, flows and scope. Commands write the templated parts, number every new ID past every open branch, and mark the capture:

- Each contract the app provides: `vela add contract --provider APP-<slug> --name "<name>" --crosses "<what goes each way>" --consumers APP-<slug> --change-policy "<how it may change>" --change new --capture ^cNN --for-lead`, one `--consumers` per consumer. It writes the required bullets on the provider's page, the Changes row and the keep mark, and refuses `decided`. Add the case table the lead confirmed under it.
- Each unknown: `vela add unknown --name "<short name>" --question "<the question>" --owner <handle> --ask "<who would know>" --blocks <ID> --capture ^cNN --for-lead`, in the same checkpoint as the line that links it.
- The rest you fill by hand, as PAGES says: the stub becomes the app page, then its containers, runtime page, concern cells, capabilities and flows. Mark each of their captures with `vela apply` on a `marks` file (`vela apply --schema marks` prints its fields), `→ keep: [[<page>#<heading>|<ID>]] (assumption)`. No command writes the `## Changes` row for an app page or a runtime page yet, so add one each, `| <ID> | <from> | <to> | [[<id>#^cNN]] |`. Containers and concern cells have no ID, so they go in their app's capture. This is an exception to leaving marks off until close, as Discover does for facts, and close leaves these alone.

When a command refuses, relay its plain reason and do what it says. When a command can't express what the lead wants, say so and stop.

The checkpoint: run `vela render`, then `vela check --for-lead` and fix every error the new pages cause, then `vela close stage --checkpoint --for-lead`, which commits the session's files by exact path.

## 5. Review the new apps and contracts

Once every sheet is written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pages are written" and the new app, contract and runtime pages as its focus: `vela reviewers prepare --checkpoint "after the pages are written" --focus <those pages> --for-lead`. Each new app and contract is a subject now, so the catalog owes its app and contract questions: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela questions --subject <ID>` for each and show the copies it owes. Show the digest as REVIEW says and capture what they take.

## 6. Finish

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then the next step is a Grill on each app's page and its contracts; say the one line the lead types, `/vela:grill <APP-id>`.
