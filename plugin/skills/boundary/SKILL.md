---
name: boundary
description: "Cut a decided direction into apps: one boundary sheet per app, a case table per contract, written as not decided yet. Offer it when someone asks what the apps are or where one ends; start it only on a yes."
argument-hint: "[the decided item, or an app]"
---

# Boundary

Turn a decided direction into apps a team lead can take; epics and handoff need an app page. Unless the lead settles an item, what it writes is "not decided yet", and a concern cell is never `addressed`.

Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `boundary`, and read the Boundary row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`. Page formats: `vela conventions "Fact bullets"` for contracts and case tables, `vela conventions "Fact tables"` for containers, `vela conventions "Concern cells and waivers"`, and `vela conventions "Flow check"` for the sequence diagram.

Spell names in American English, capitalized ones too ("Route Optimizer"). A read-back by name:

> Not this: "APP-dock-service provides CON-003 to APP-fleet-console, at assumption; UNK-051 blocks it."
>
> This: "The dock service gives the fleet console its list of broken docks. That's not decided yet, and it waits on one open question: who signs off the repair contract."

## 1. Read the direction

Read the picked option on `04-solution-strategy.md` and what it links, the context and scope, building blocks, flows, concerns, functional requirements and the open questions on them. If the direction isn't decided, say what is open (apps cut on it may be cut again); go on only as an override.

## 2. Find the seams, then offer the cuts

Once, before drawing the apps, run `vela questions --existence --for-lead`, read it as one turn, and capture each of the six answers on its own line.

Before any cut, ask how the product comes apart, in the lead's own words, a question or two at a time. What will someone stand up, own, release or switch off on its own? Don't let the shape's wording (a report, a reminder, "one helper") answer it for them. Ask:

- "Which parts run on a person's own device, which run somewhere shared that your people operate, and which does an administrator or support person open?"
- "Would different teams build or run any of these, or would any ship on its own schedule?"
- "Could any part be thrown away and rebuilt without losing something people rely on, such as who agreed to what, or what each person may see?"
- "Who keeps the record of who consented, who signed in, and what access was granted? Is that a part of one of the above, or a thing of its own?"

Every part they name ends up in the cuts, as an app or as "not an app" with its reason; a part only the sources name is offered as `(claude)`, with the source. Offer consent and identity as their own app when a source shows a different owner, lifecycle or approval. A lead who says it is one thing gets the single-app cut first; never force a split they reject.

Offer the cut the lead described and each real alternative the plan needs, never padding to a number. Each names every app it touches and what happens to it, in words (new, changed, connected to as it is, left alone, retired); which app owns each job and which job no app owns yet; what it makes easy and hard; and what each claim rests on. Test each cut against the functional requirements with `vela boundary cover --cut .vela/cuts.json --for-lead` and relay what each carries whole, splits or leaves with no app; the trade-offs are yours. Say which cut you prefer and why, capture each cut, the reactions, the pick and each rejected cut's reason, and write the pick with `vela add cut --for-lead`. If they reject them all, capture why and offer new cuts.

Then ask once, for all apps together, what the lead's people call the area of the business each sits in, and whether any two are really one area. Offer names the plan already uses; never invent one. An app given no area keeps none, as an override. Stub every new or changed app with `vela add app-stub --for-lead`, with the domain they named and the pick's capture.

## 3. Read back one boundary sheet per app

**Draw the tracer candidate's flows first.** Say what "tracer" and "slice" mean, from `vela terms`, the first time. Before the first sheet, offer the journey that crosses the most apps and read its steps back first, so its pages exist when Releases chooses the tracer. Record the answer so releases does not ask again: capture the path in the lead's words, marked at once `→ keep: [[<first flow page>#Steps|<the flow's name>]] (assumption)`, and open the flow page with "We build this journey first, as the first thin path: ..." (Releases finds it by those words). With no candidate yet, Releases will ask. Draw its sequence diagram once its steps and case tables are confirmed.

Group what makes sense by default with a `box`: channels that follow the same steps (an opening `alt` names them) and lookups that only answer the core app. Never group the app the flow is about, and don't group lanes just to save width. Say it in one plain line.

Take the stubs one at a time, each sheet a numbered list:

1. **Does:** what the app decides or keeps, in the domain's words, and its domain.
2. **Doesn't do:** the jobs that stay elsewhere, each naming who keeps it.
3. **Main parts:** each container and its job.
4. **What it offers other apps:** each contract by name, what goes each way, and who uses it.
5. **What it needs from others:** each contract it relies on. For an outside party, ask for an API spec or docs link, or a skip, and add a link they give to the Library with `vela library add`, no yes.
6. **When something fails:** what the app and each consumer do when it, or something it needs, is down or slow.
7. **Capabilities:** each business capability it delivers or changes, in the domain's words, and whether that is new, extended, replaced, narrowed or retired.
8. **Journeys:** each end-to-end journey it takes part in, its steps in order, each naming the app and the contract or capability it uses. For a step that hands something between two lanes, read back who sends and who receives, with your guess: "Step 3: Booking sends Payments the order ID, through Order identity. Does Booking start that, or does Payments ask for it?"
9. **Concerns:** one line per concern page, in words: a question to answer first, the existing practice holds, doesn't apply and why, or nobody has looked yet (no row). Never `addressed`.
10. **Where it lives:** where its code and its team's wiki live, for the links or a skip. A link is only what the lead gives; never guess one from the app's name. The page's `links:` stay as they are.

**A case table for each contract in item 4**: every way the provider can answer. Draft the rows from what the contract, the sources and the failure lines already say, each `(claude)`, and invent nothing they don't support. Ask one question per open case, with your recommendation: "When the stock check can't find the item, what does Stock say back? Recommended: Stock says the item is unknown and names it." Ask the same way whether it can time out, how often the caller retries, and what proves the caller's identity. A row with no yes is left out; a contract with no table is said as "Nobody has written down every answer Order identity can give yet", never filled with a guess. After writing a case table, run `vela check-slice --changed --for-lead`, say which slices it checked and why, and settle each finding with its owners as a case row, a branch or an open question.

**A spec for each contract in item 4**, once its table is written: is it written down as a spec (OpenAPI, AsyncAPI, WSDL)? One that is goes to the Library after a yes. For one that isn't, ask who writes it and by when, with your recommendation, and file the answer with `vela add unknown --for-lead`, with no `**Blocks:**` line: a contract can be decided before its spec exists. "No spec" is a fine answer too, and writes nothing.

Label every line with what it rests on: a source, a decided item, the lead's own words, or `(claude)`. Read the sheet back in two groups, items 1 to 3 and 4 to 10; a correction needs its own yes. When `vela next` sent you here for the requirements and shares, write them on the sheet and read them back with it. A line nobody can answer becomes an open question (`MODES.md`, "Unknowns").

## 4. Write the confirmed lines

After each sheet, write what was confirmed, as `${CLAUDE_PLUGIN_ROOT}/skills/boundary/PAGES.md` says: `vela add contract --for-lead` for each contract the app provides, then its confirmed case table; `vela add unknown --for-lead` for each open question, in the same checkpoint as the line that links it; the rest by hand. Mark each capture through `vela apply` (`--schema marks`) as `(assumption)`. No command writes the `## Changes` row for an app or runtime page yet, so add each to the session's notes as `| <ID> | <from> | <to> | [[<id>#^cNN]] |`.

Ask once per sheet: "Write these as decided, or keep them as not decided yet?" On "decided", run `vela decide <ID> --yes ^cM --for-lead` for each; `^cM` is the capture of the lead's answer "decided" to this question, not the earlier yes to the lines. A hedge keeps them not decided yet, and so does an item the gate names for a contract or app page: say so once.

Then `vela render`, `vela check --for-lead` and `vela close stage --checkpoint --for-lead`. Draft the paragraph each filed item owes, as `START.md` says under "Draft the paragraph when the item is filed".

## 5. Review, then finish

Once every sheet is written, run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md` "after the pages are written", with the new app, contract and runtime pages as its focus, and `vela questions --subject <ID>` for each new app and contract. Show the digest; capture what the lead takes.

When the lead is done, close as `START.md` says under "Closing a session". Next, settle each app and its contracts, or grill them: name the line, such as `/vela:grill Desktop agent`.
