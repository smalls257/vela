---
name: boundary
description: Boundary session for an initiative vault. Turns a decided direction into apps. Offers 2 or 3 ways to cut it into apps, then reads back one boundary sheet per app (what it does and does not do, its containers, the contracts it provides and consumes, how it behaves on failure, its concern cells), writes the confirmed lines as app, contract and runtime pages at assumption, and runs a review checkpoint on the new apps and contracts. Use when the direction is decided and no app page says who builds what.
argument-hint: "[the decided item, or an app]"
disable-model-invocation: true
---

# Boundary

Turn a decided direction into apps a team senior can take. Until an app page exists, the catalogue's app and contract questions are owed by nothing, `planner status` has nothing to show, and epics and handoff have nothing to work on. Boundary never decides: every page it writes is an `assumption` until a Grill.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (if the host leaves `${CLAUDE_PLUGIN_ROOT}` unexpanded, use the order in `${CLAUDE_PLUGIN_ROOT}/references/START.md` under "Where the planner runs from"). The page formats are `CONVENTIONS.md`: "Frontmatter", "IDs", "Fact bullets" for contracts, "Fact tables" for containers, "Concern cells and waivers", and the ladder under "Areas and stages".

## 1. Start

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `boundary`. Read the Boundary row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.

Read the direction: `04-solution-strategy.md` and every page it links for the picked option, `03-context-and-scope.md` for the systems today and the apps in and out of scope, the existing building-blocks pages, `06-runtime/06-flows.md`, the concern pages, and the open unknowns and risks that block any of them. If the direction is not `decided`, say so and name what is still open: an app cut on an undecided direction may be cut again. Go on only if the user says to, and record that as an override as `START.md` says.

## 2. Offer the cuts

Offer 2 or 3 ways to cut the direction into apps, never one and never more than three. A cut names every app it touches, each with its `change` (`new`, `changed`, `integrated`, `unchanged` or `retired`), and says in a line or two:

- which app owns each job the direction needs, and which job no app owns yet;
- what it makes easy and what it makes hard: an extra service to run, a link held in two places, a team with no owner;
- which decided item, source or unknown each claim rests on.

Capture each cut as a `[thought] (claude)` line. Say which cut you prefer and why. Capture the user's reaction to each and the cut they pick. A rejected cut gets a capture with its reason. If they reject them all, capture why and offer new cuts.

Write the picked cut on `05-building-blocks/05-building-blocks.md` under `## <the picked cut>`: the apps it names, each with its `change`, and a `- **Options considered:**` bullet, `<picked cut> (picked); <cut>: rejected, <reason>; ...`.

Then ask for the domains, once, for every app of the picked cut together, not one by one on the sheets. Say: "Here are the apps in this cut. What do your people call the areas of the business they sit in? For example Channels, Payments, Learning. Give me a name per app, and tell me where two apps are really one area." Propose the names from `03-context-and-scope.md`, the glossary and the domains already on other pages of the vault, offered first so spellings converge; never invent an area your people do not use. Each name the user confirms is written as `domain: <name>` in that app's frontmatter in section 4, and on a capability page when the user names one for it. An app the user gives no area keeps none, and that skip is recorded as an override, never blocked.

Then write a stub for every app of the picked cut whose `change` is `new` or `changed`, so every later link has a page to point at. A stub is `05-building-blocks/<slug>-building-blocks.md` with the frontmatter in section 4 at `state: inkling`, and, under its title, exactly the line `Its boundary sheet is still to be read back.`, which section 4 replaces. Give it an `unexamined` row on each concern page. `planner next` sends a stub with no containers table back to Boundary, so an app this session does not reach is never lost. Mark the capture of the picked cut at once, `→ keep: [[05-building-blocks#<the picked cut>|cut]] (assumption)`, add one `## Changes` row per stub, `| APP-<slug> | - | inkling | [[<id>#^cNN]] |`, run `planner check`, and commit the checkpoint.

## 3. Read back one boundary sheet per app

Take the stubs one at a time. For each, show its sheet as a numbered list:

1. **Does:** what the app decides or keeps, in the domain's words, and the domain the user named for it.
2. **Does not:** the jobs that stay elsewhere, each naming the app or party that keeps it.
3. **Containers:** each main part and its job.
4. **Provides:** each contract, as `CON-nnn <name>`, with what crosses the boundary in each direction and each consumer.
5. **Consumes:** each contract it relies on, provided by another app or an outside provider. For each outside party or third-party contract, ask: "Is there an API spec or docs for <party>? A link is enough." The user may skip.
6. **On failure:** what the app and each consumer do when it, or something it consumes, is down or slow.
7. **Capabilities:** each business capability the app delivers or changes, in the domain's words, such as "teach a stock trade", with `new`, `extend`, `replace`, `narrow` or `retire`.
8. **Flows:** each end-to-end journey the app takes part in, such as "a reader practises a trade": its steps in order, each naming the app and the contract or capability it uses. For each step that hands something between two lanes, read back who sends and who receives, with your guess, such as "Step 3: TickerTalk sends Coach the reader ID, over Reader identity. Is that the direction? Tell me if Coach starts it." A step with no hand-over, such as the reader opting in, needs no sender.
9. **Concerns:** one line per concern page: `unknown` with the question that must be answered first, `unchanged` when a changed app's existing practice holds, `n/a` with why, or `unexamined`. Never `addressed`, because only a Grill decides one.
10. **Where it lives:** ask "Where does this app's code and its team's wiki live? Paste the links, or say skip." A link is only what the user gives you. Never guess an address from the app's name, and a skip is not recorded.

Label every line with what it rests on: a `SRC-nn`, a decided item and the Grill that decided it, the user's own words, or `(claude)` for your proposal. A line with nothing under it is a proposal, and it says so. Write nothing until the user has given an explicit yes to that line. Silence, or "looks fine" with no yes per line, does not count: ask again. A correction replaces the line, and the corrected line needs its own yes. A line the user cannot answer becomes an unknown on `11-unknowns-and-risks.md`, `### UNK-nnn <short name>`, with `**Question:**`, an `**Owner:**` handle, `**State:** open`, an `**Ask by:**` date and `**Blocks:**` linking what it blocks, written in the same checkpoint as the line that links it. When the owner is not the person who would actually know, ask once: "Who would actually know this? If that is not the owner, give me a name or a role, like outside counsel." Write the answer as `**Ask:** @handle` or `**Ask:** outside counsel`, and leave the line out when the owner holds the answer.

## 4. Write the confirmed lines

After each sheet, write what was confirmed and commit a checkpoint. The required fields for each page type are in the Frontmatter table of `CONVENTIONS.md`; a missing one is E103.

- **The app page:** fill the stub. `id: APP-<slug>`, the slug the file name starts with, `type: app-building-blocks`, `title`, `state: assumption`, the app's `change`, its `domain` as the user named it in section 2, `owner` (the handle of the team that will build it, or the user's handle until one is named), `authored: authored`, and `sources`. When the user gave where the code and wiki live, add `links: {Repo: <url>, Wiki: <url>}` with the labels they used and exactly their URLs, or a key where `.planner.yaml` has a `link_templates` entry for the label ("Links out of the vault" in `CONVENTIONS.md`). No answer, no `links:` line. `sources` lists every `SRC-nn` the lines rest on and, for lines resting on a decided item or the user's words, the session id of the Grill or of this session, so the page never lists none. Set `stage` by the ladder in `CONVENTIONS.md`, never higher than its entry list allows: `target` once the page cites a source that is not a dump, `baseline` before that. "Does" and "does not" become its opening paragraphs. An app that already had a page before this session keeps it: change only the lines the user confirmed.
- **Containers:** the table `| Container | Job | Contracts served or used | Proposed by | State |`, every State `assumption`.
- **Contracts it provides:** under `## Contracts this app provides`, one `### CON-nnn <name>` each, with every required bullet: `**Crosses the boundary:**`, `**Consumers:**` linking each consumer's page, `**Change policy:**`, `**Change:**` and `**State:** assumption`. New IDs take the next free number: grep the vault for the existing IDs of that kind, and read the `## Changes` tables of the records on `git branch --list 'session/*'` and `git branch -r --list 'origin/session/*'`, because another open session may already hold the next one.
- **Contracts it consumes:** add the app to the `**Consumers:**` bullet of each contract it consumes, on the provider's page. A provider outside the initiative with no page gets its contract on this app's page with a `**Provider:**` bullet. A link the user gave for an outside party or a contract goes in a `- **Links:** [API spec](<url>)` bullet on that party or contract, and nothing is written when they skipped. An `integrated` or `unchanged` app in the initiative with no page gets a slim page as `CONVENTIONS.md` says under "Pages", no `stage`, holding only the contract it provides, at `fact` with its `**Source:**` when a source describes it, or at `assumption`.
- **What was weighed:** a `- **Options considered:**` bullet, `<the picked cut> (picked); <cut>: rejected, <reason>; ...`, on the app page, on its runtime page and under each `### CON-nnn` it provides. `planner next` and the Grill's GATE-2 read it on the item itself: without it the app goes back to Shape.
- **The runtime page:** `06-runtime/apps/<slug>-runtime.md` with `id: RUN-<slug>`, `type: app-runtime`, `title`, `state: assumption`, the same `owner`, `authored: authored` and `sources`, and the confirmed failure line under `## On failure`.
- **Concern cells:** replace the app's `unexamined` row on each concern page with the confirmed state. A line with no yes keeps `unexamined`: it claims nothing. An `unknown` cell links its unknown.
- **Capabilities:** link each capability the app delivers from the app page, using the page `/planner:requirements` wrote. Only when no page exists, write each confirmed capability as `capabilities/CAP-nnn-<slug>.md`, with `id`, `type: capability`, `title`, `state: assumption`, `owner`, `authored: authored`, `origin: proposed`, its `change`, and opening prose saying what the business can do with it. Link it from the app page and from `04a-capability-delta.md`, one line each. A capability that already has a page gets only the link.
- **Flows:** each confirmed journey as `06-runtime/flows/FLO-nnn-<slug>.md`, with `id`, `type: flow`, `title`, `state: assumption`, `owner`, `authored: authored` and `sources`, opening prose saying who does what and why, then `## Steps`, a numbered list, one line per step, linking the capability or contract it uses. A step that hands something between two lanes starts with its confirmed sender and receiver, `[[tickertalk-building-blocks|TickerTalk]] → [[coach-building-blocks|Coach]]: sends the opaque reader ID over [[tickertalk-building-blocks#CON-005 Reader identity|Reader identity]].` (`CONVENTIONS.md`, "Flow steps"); the arrow names both ends, so no reader has to guess the direction from the verb. An outside party is named by its name or its party page. A journey that already has a page gets only the lines the user confirmed. Link each flow from the runtime page of every app it names, and from `06-runtime/06-flows.md`.
- **Scope:** the app in the apps-in-scope list on `03-context-and-scope.md`, linking its page.

Each sheet gets one capture line per item with an ID that changed (the app, its runtime page, each contract, each unknown), marked at once, `→ keep: [[<page>#<heading>|<ID>]] (assumption)`, or `(open)` for an unknown, and one `## Changes` row each, `| <ID> | <from> | <to> | [[<id>#^cNN]] |`. Containers and concern cells have no ID, so they go in their app's capture. This is an exception to leaving marks off until close, as Discover does for facts. Close leaves these alone.

Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner render` and `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check`, fix every error the new pages cause, and commit the checkpoint with every file render reported, by exact path.

## 5. Review the new apps and contracts

Once every sheet is written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the pages are written" and the new app, contract and runtime pages as its focus. Each new app and contract is a subject now, so the catalogue owes its app and contract questions: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --subject <ID>` for each and show the copies it owes. Show the lead the digest as REVIEW section 5 says, and capture what they take.

## 6. Finish

Run `git status` and confirm nothing under `.inbox/` is staged. Tell the user: "Run `/planner:close` to finish the session and open the PR. Then run `/planner:grill <APP-id>` to decide each app's page and its contracts."
