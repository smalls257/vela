---
name: boundary
description: Cut a decided direction into apps, read back one boundary sheet per app, and write the confirmed lines at assumption. Use when the direction is decided and no app page says who builds what.
argument-hint: "[the decided item, or an app]"
disable-model-invocation: true
---

# Boundary

Turn a decided direction into apps a team senior can take. Until an app page exists, the catalogue's app and contract questions are owed by nothing, `planner status` has nothing to show, and epics and handoff have nothing to work on. Boundary never decides: every page it writes is an `assumption` until a Grill.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). The page formats are `CONVENTIONS.md`: "Frontmatter", "IDs", "Fact bullets" for contracts, "Fact tables" for containers, "Concern cells and waivers", and the ladder under "Areas and stages".

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

Offer 2 or 3 ways to cut the direction into apps, never one and never more than three. A cut names every app it touches, each with its `change` (`new`, `changed`, `integrated`, `unchanged` or `retired`), and says in a line or two:

- which app owns each job the direction needs, and which job no app owns yet;
- what it makes easy and what it makes hard: an extra service to run, a link held in two places, a team with no owner;
- which decided item, source or unknown each claim rests on.

Test each cut against the functional requirements and say it in a line per cut: which requirements an app would carry whole, which would be split across apps (and so need a contract), and which no app in the cut would carry. A cut that leaves a requirement with no app, or splits one with no contract to carry the crossing, says so as a cost. If the vault has no functional requirements yet, say that, and offer `/planner:requirements` first.

Capture each cut as a `[thought] (claude)` line. Say which cut you prefer and why. Capture the user's reaction to each and the cut they pick. A rejected cut gets a capture with its reason. If they reject them all, capture why and offer new cuts.

Write the picked cut on `05-building-blocks/05-building-blocks.md` under `## <the picked cut>`: the apps it names, each with its `change`, and a `- **Options considered:**` bullet, `<picked cut> (picked); <cut>: rejected, <reason>; ...`.

Then ask for the domains, once, for every app of the picked cut together, not one by one on the sheets: what do the lead's people call the areas of the business each app sits in (Channels, Payments and Learning, say), and are any two apps really one area? Propose the names from `03-context-and-scope.md`, the glossary and the domains already on other pages of the vault, offered first so spellings converge; never invent an area your people do not use. Each name the user confirms is written as `domain: <name>` in that app's frontmatter in section 4, and on a capability page when the user names one for it. An app the user gives no area keeps none, and that skip is recorded as an override, never blocked.

Then write a stub for every app of the picked cut whose `change` is `new` or `changed`, so every later link has a page to point at. A stub is `05-building-blocks/<slug>-building-blocks.md` with the frontmatter in section 4 at `state: inkling`, and, under its title, exactly the line `Its boundary sheet is still to be read back.`, which section 4 replaces. Give it an `unexamined` row on each concern page. `planner next` sends a stub with no containers table back to Boundary, so an app this session does not reach is never lost. Mark the capture of the picked cut at once, `→ keep: [[05-building-blocks#<the picked cut>|cut]] (assumption)`, add one `## Changes` row per stub, `| APP-<slug> | - | inkling | [[<id>#^cNN]] |`, run `planner check`, and commit the checkpoint.

## 3. Read back one boundary sheet per app

Draw the tracer candidate's flows first. The tracer is the first thin path through the apps (`CONVENTIONS.md` defines it under "Releases"; say what it is the first time you mention it). Before the first sheet, ask what a person would do if one thin path went through all of these first. Offer the journey that crosses the most of the cut's apps, from the user's words and the sources, and read its steps back (item 8 below) before any other flow, so its flow pages exist when `/planner:releases` chooses the tracer.

Record the answer so releases does not ask again: a capture of the path in the lead's words, marked at once `→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)`, and the path as the opening sentence of that flow page ("the first thin path: ..."). A user with no candidate yet is not held up: say releases will ask once, and carry on.

Take the stubs one at a time. For each, show its sheet as a numbered list:

1. **Does:** what the app decides or keeps, in the domain's words, and the domain the user named for it.
2. **Does not:** the jobs that stay elsewhere, each naming the app or party that keeps it.
3. **Containers:** each main part and its job.
4. **Provides:** each contract by its name, with what crosses the boundary in each direction and each consumer.
5. **Consumes:** each contract it relies on, provided by another app or an outside provider. For each outside party or third-party contract, ask whether there is an API spec or docs for it; a link is enough, and the user may skip.
6. **On failure:** what the app and each consumer do when it, or something it consumes, is down or slow.
7. **Capabilities:** each business capability the app delivers or changes, in the domain's words, such as "teach a stock trade", with `new`, `extend`, `replace`, `narrow` or `retire`.
8. **Flows:** each end-to-end journey the app takes part in, such as "a reader practises a trade": its steps in order, each naming the app and the contract or capability it uses. For each step that hands something between two lanes, read back who sends and who receives, with your guess, such as "Step 3: the Booking app sends the Payments app the order ID, over Order identity. Is that the direction? Tell me if Payments starts it." A step with no hand-over, such as the reader opting in, needs no sender.
9. **Concerns:** one line per concern page: `unknown` with the question that must be answered first, `unchanged` when a changed app's existing practice holds, `n/a` with why, or `unexamined`. Never `addressed`, because only a Grill decides one.
10. **Where it lives:** ask where this app's code and its team's wiki live, and for the links or a skip. A link is only what the user gives you. Never guess an address from the app's name, and a skip is not recorded.

Label every line with what it rests on: a source, a decided item and the Grill that decided it, the user's own words, or `(claude)` for your proposal. A line with nothing under it is a proposal, and it says so. Say each app, contract and flow by its plain name when you show a sheet. Read the sheet back in two groups, "what it does and doesn't" (items 1 to 3) and "how it connects" (items 4 to 10), and write a line only after the yes `START.md` defines; a yes to a group counts for the lines in it. A correction replaces the line, and the corrected line needs its own yes. A line the user cannot answer becomes an unknown on `11-unknowns-and-risks.md`, `### UNK-nnn <short name>`, with `**Question:**`, an `**Owner:**` handle, `**State:** open`, an `**Ask by:**` date and `**Blocks:**` linking what it blocks, written in the same checkpoint as the line that links it. Write who would actually know as `**Ask:**`, as `MODES.md` says under "Unknowns".

## 4. Write the confirmed lines

After each sheet, write what was confirmed and commit a checkpoint. `${CLAUDE_PLUGIN_ROOT}/skills/boundary/PAGES.md` lists what each page holds: the app page, its containers, the contracts it provides and consumes, what was weighed, the runtime page, the concern cells, capabilities, flows and scope. The required fields are in the Frontmatter table of `CONVENTIONS.md`, and `planner check` reports a missing one. Five things are easy to get wrong:

- Every page this session writes is an `assumption`, never `decided`, and a concern cell is never `addressed`: only a Grill decides one.
- A contract's provider outside the initiative is a link to the outside party's page, never a sentence about who supplies it.
- A hand-over step in a flow starts with its sender and receiver and an arrow (`CONVENTIONS.md`, "Flow steps"), so no reader guesses the direction.
- A skipped answer (a link, a domain) is not recorded, and a line with no yes keeps `unexamined`: it claims nothing.
- New IDs come from `planner next-id <PREFIX>`, so an open session branch never hands out the same number twice.

Each sheet gets one capture line per item with an ID that changed (the app, its runtime page, each contract, each unknown), marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`, or `(open)` for an unknown, and one `## Changes` row each, `| <ID> | <from> | <to> | [[<id>#^cNN]] |`. Containers and concern cells have no ID, so they go in their app's capture. This is an exception to leaving marks off until close, as Discover does for facts. Close leaves these alone.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render` and `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check`, fix every error the new pages cause, and commit the checkpoint with every file render reported, by exact path.

## 5. Review the new apps and contracts

Once every sheet is written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pages are written" and the new app, contract and runtime pages as its focus. Each new app and contract is a subject now, so the catalogue owes its app and contract questions: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --subject <ID>` for each and show the copies it owes. Show the digest as REVIEW says and capture what they take.

## 6. Finish

When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session". Then the next step is a Grill on each app's page and its contracts; say the one line the lead types, `/planner:grill <APP-id>`.
