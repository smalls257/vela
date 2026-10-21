---
name: house-voice
description: "Draft or redraft plan prose in the house voice, from the vault's own examples. Offer it when someone wants a paragraph written or reworded to sound like the plan; start it only on a yes."
argument-hint: "[page or paragraph to draft]"
---

# House voice

Prose in this vault has one voice. Draft it from the example passages and the default voice below, not from rules alone. Prose is drafted only here, so every paragraph meets them.

## Load the examples

If the vault has `voice/VOICE.md`, read it first. It holds the owner's own rules, in their words, and wins over the default voice, the rules below and the examples where they disagree. The owner may override any default. Run by hand, outside close, you also talk to the owner: read `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` too, as `START.md` step 6 says, before your first question.

Then run `vela voice examples --page <page> --json` for the page you are drafting. Read every example of that type it lists, in the order it lists them, before you write a word. The order is fixed so two drafts of one page start from the same context: active examples in file-name order, local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example. A structured page lists none: it holds no voiced prose. When the command can't resolve the page, read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/TYPES.md` and run it with `--type` instead.

An `owner` or `owner-edit` example is the owner's own writing; once `/vela:voice-seed` adds two of a type, that type's public seed retires. Until then a type's examples are public seeds. Take from a seed what a page of its type covers and in what order, and take the sentences from the default voice below.

When the command says the type has fewer than two active examples across both folders, say "No examples for <type>: drafted without examples" in the PR body, and draft from the defaults at the end of this file.

Never read `voice/corpus/`. It is gitignored and stays out of every draft.

## What is never voiced

These keep the exact words they were written in. Do not restyle them:

- fact bullets, such as `**Owner:**` or `**Tested by:**`;
- tables, and a contract's case table above all: its rows are read by the checker, so a row's words are the lead's, confirmed one by one;
- acceptance criteria, and the `- Trace:` line under each;
- `**Decision:**` and `**Dissent:**` lines;
- generated blocks;
- a person's words lifted from a capture;
- a sentence another page quotes as evidence: a reviewer question's `quote:` or a `source:` quote names its page, and `vela check` looks for those exact words there. Leave the sentence as it is, or rewrite it and change the quote in the same edit to the new words, which must carry the same fact. E802 from `vela check` means a quote lost its words.

## Prose that is already merged

Merged prose belongs to the people who edited it. When a session changes a fact in a merged paragraph, change only that fact and the fewest words grammar needs. If the change makes the paragraph wrong as a whole, rewrite it, but first run `vela prose replace --page 05-building-blocks/till.md --line 12` with the page and any line of the paragraph: it copies the old paragraph byte for byte into the session record under `## Replaced prose`, with the page and the date, so whoever wrote it can find it. Never copy it by hand. Say so under **Prose drafted** in the pull request body. A page never carries two openings, and never a note to a reader about which paragraph to delete: those are editing notes, and a page with one ships as a draft.

## The default voice

Until the owner has examples of their own, pages read like a senior colleague explaining the plan across a desk to someone on the team who wasn't in the sessions. That reader knows the company and everyday words; they don't know this plan's own names. A line in the owner's `voice/VOICE.md` wins over any line here, and their `owner` and `owner-edit` examples win too. The vault's `voice/DEFAULT.md` says the same for the owner to read; this section is the one that drafts follow.

Explain what that reader would stop to ask, and nothing they already know. The opening paragraph of a page does most of the explaining, so it may run longer than the paragraph it replaces. The paragraphs and items below lean on it and stay short: a redraft of one comes out no longer than what it replaces, and usually shorter.

- **Introduce this plan's names the first time a page uses them:** the product ("Dockside, the bike-share app for the Riverside docks"), a screen ("the repair queue, which lists the bikes riders reported"), a person by full name or role and what they do ("Mira Castell, who runs the dock operations team"). Say what a short run of abstract nouns stands for: "paying by card at the dock, a rider account, and a way to report a broken bike", not "payment, accounts and repair". Don't gloss an everyday or company word ("opted in", "the finance committee", "the payment card"), don't unpack a plain phrase ("the timeline is tight"), and don't introduce the lead to their own role.
- **Say "we" for the team and the role for one person:** "we haven't checked this yet", "the solution lead picked it".
- **Contract the way people talk, negatives too:** hasn't, won't, can't.
- **Short sentences carry the facts, one point each with at most one addition:** an aside, a reason, a "so", or a list. A second addition starts a new sentence. Not "The pilot lead counted 40 percent of trips starting at the station docks, but we only believe that figure, because nobody has seen the count"; instead "The pilot lead counted 40 percent of trips starting at the station docks. We only believe that figure, because nobody has seen the count." Put the cause before what follows from it: "Operations wants docks on the pavement and the council's planners want them off it. The transport committee is the one to ask."
- **Say a point's state with its verb, once:** "we're assuming the first release is a pilot", "the transport committee votes on it by December 1", "the city lawyer hasn't been asked yet". When the verb carries the state, add nothing. Never tag it on as its own sentence or clause: not "That isn't decided.", ", which hasn't been decided,", "and that is still open" or "no date is given".
- **Use the plain word, never vela's own, even where the record uses it:** "holds up", not "gates"; "a session to test it", not "a grill"; "what it must do" or "the acceptance criteria", not "the checks".
- **Answer the reader's next question in the next sentence, but only with a reason someone recorded.** With none, write "the reason isn't recorded yet". Say it as a statement, not as a question put to the reader.
- **Let a period do the work** of a formal linking word, and open on the point, never on a phrase that clears the throat.
- **End an open list with a next step someone recorded,** not a summary of it. With none, say what's open and who's been asked. On a concern page an app with no row already reads as not looked at: leave an unexamined Why cell blank and an empty Strategy empty.
- **Never hedge a point the record marks decided.** For an absence write "not recorded as agreed", never "nobody has…" or "no team owns…" as fact.
- **Sound sure only about what someone said or a source shows.** What you know yourself goes in as worth checking ("worth checking whether…") or as a question to the lead, never as a fact. A consequence ("if X, then Y") is written only if someone said it; otherwise it's a question for the lead. A number or date needs a source; otherwise write "no figure given yet". A what-if is framed as one ("suppose", "if") and uses only what the plan or the lead has said; it never reports a new event or what someone else said as having happened.
- **Be warm by being direct.** No jokes.
- **"You" is the person reading the page.** Name a person who uses the system by their role.

This is the shape to match, on an invented initiative. The opening explains; the item under it leans on the opening and stays short:

> Two releases are planned. The first is a pilot at the Riverside docks, starting Wednesday, March 3, 2027, where riders will unlock and return bikes, along with what that needs: paying by card at the dock, a rider account, and a way to report a broken bike. The pilot is still an assumption, not a decision, and two open questions could move the date. Paying by phone waits for the second release, which has no date yet.
>
> The card processor has to certify the dock reader before the pilot. We don't know how long that takes, so the payments team is asking by November 6. The pilot lead says the timeline is tight, so this holds up the March 3 date.

A list or a table is fine when there's more to take in than a paragraph holds (rule 7 below). These are the numbers a page lands inside, read over the whole page, since one short paragraph is too small to measure:

| Measure | Target |
|---|---|
| Median sentence length | 10 to 16 words |
| Three sentences in four | 22 words or fewer |
| Contractions | 2 to 6 per 100 words |
| "We" and "you" together | 1 to 6 per 100 words |
| Passive sentences | 15 in 100 at most |
| Formal linking words | 1 per 1,000 words at most |
| Latin-rooted content words | 8% at most |
| Reading grade (Flesch-Kincaid) | 8.5 at most |

## The rules

The examples are what to match. These rules are what to do where they are thin. Close and epics point here for page prose.

1. **Write like a senior technical writer explaining the system to a colleague.** Plain, spoken sentences in the active voice. Use negatives where a person would ("the agent doesn't send anything off the laptop"), and don't twist them into positives.
2. **Open with what the system does for people, then what is still open.** The first paragraph is two or three short sentences with few links; `vela check` says when an opening runs long. It names threads, not items; the blocks and tables below list the items.
3. **Every sentence has a character.** The subject is a person, a team, an app, a document or a date: "Mira Castell hasn't confirmed the 70% figure". Where a subject is "it", "this" or "there", find who acts and make that the subject. The subject may be the app: "Booking holds the seat for ten minutes".
4. **Give each point its true state, once.** Say whether it is assumed, decided or open with the verb of the sentence about it, worded the way you would say it to a colleague. Never make it sound more certain than the record, and don't reach for the same phrase on every page. On a capability page and in a requirement, the paragraph says what the system will do, because it is planned, not built: "The Rider app will unlock a bike at any dock", not "unlocks", which says it already does, and not "the business can have".
5. **For anything open, say who settles it and by when,** in words, not codes: "the payments team needs to confirm this by November 6". "The lead believes most trips start at the station docks, and the pilot lead hasn't confirmed it" is a hedge a reader can use.
6. **One topic a paragraph, ending on the last fact worth knowing.** A second topic starts a second paragraph, and `vela check` flags one that runs long. Start a sentence with what the last one left and end it on the new thing. The page type's own closing section, such as `## Out of scope`, is the only ending.
7. **Ask the reader to hold only a few new things at once.** A paragraph that brings in more names, numbers or open points than a reader can hold groups them ("three things hold up the first release") or moves them to a list or a table. People hold only a handful of things in mind at once (Cowan); grouping is what keeps a long record readable.
8. **Point at a block or a table, and leave its numbers there.** Write "the open questions are listed below", and let the generated block carry the count.
9. **A criterion reads aloud.** It names things by their names and could be read to a tester over the phone. Its IDs sit on the `- Trace:` line under it, and a bracketed aside becomes a clause that says who says it.
10. **Write about the system and the people, not about the record.** Not "we've written down", "the vault says" or "this page records". How a decision was reached, and which session added what, is the page's `## History`.
11. **Keep the owner's words and the record's facts.** Who said what, and every state, number, date and negation, stay as the record has them, even when a smoother sentence is tempting. Keep the state, not the record's word for it: a verb that says it ("we're assuming", "the city lawyer hasn't been asked") keeps it, and a word of vela's own in the record ("gates", "grill", "checks") is said in plain words. A merged paragraph changes only the fact that changed; voicecheck says so when one is gone.
12. **Spell in American English.** Behavior, organization, color, license, canceled. The owner may override it in `voice/VOICE.md`.
13. **Write dates in American order.** "October 14" in the current year, "October 14, 2026" in any other, and "Tuesday, February 2, 2027" with a weekday. Dates in frontmatter, tables of record and IDs stay ISO (2026-10-14).

Write paragraphs where the page asks for prose: a run of bullets that are not fact bullets is a paragraph waiting to be written. Name things in the sentence and keep their IDs on a `- Trace:` line. Facts come from somewhere. Every number, date and ID in a draft comes from a capture, a source or a page; where you cannot point to it, leave it out. Spell an abbreviation out at its first use on the page, put a link on the words that rely on a source or point at an item, and link every ID as `vela conventions "Pages"` says.

## Pages that are mostly a list

Unknowns and risks, concerns, decisions, sources and any page that is mostly a list have two parts, and the opening never does the second part's job.

1. **An opening that counts and points.** Two or three plain sentences: how many are open, which few hold the rest up, and the most urgent with its date. "28 questions are open. Five hold up the first release; the most urgent is who owns the dock repair contract, due October 23." It names about three items at most and sends the reader to the list below.
   This opening, from an unknowns page, is the shape to match. One call holds most of the page up, so it comes first; the documents nobody is writing are one sentence; the newest question closes it with a pointer to the list:

   > One open call holds up most of this page: who settles whether docks may stand on the pavement. Most other questions wait on it, or on what the card processor will certify. Three documents have an owner and a date but nobody writing them yet. The newest question is whether the transport committee votes on the pilot; everything else is listed below, grouped by what it holds up.

2. **The items as a grouped list.** Group by what they hold up (the first release, the card-at-the-dock requirements, the security review), about seven to a group. Each line reads: the plain name, who to ask and by when, what it holds up. Anything past seven in a group goes under `## Also open (n)`, which the viewer folds.

## Size

`vela close drafts --json` counts the paragraphs a session owes and says when there are more than about 20 prose paragraphs, too many to review as one. Then ask the lead, with the count and the groups it prints: "<n> paragraphs changed. Send them for review as one batch, or split them by section (apps, flows, the rest)?"

## When examples are thin

Follow the default voice and the rules above, rule 1 first. Name the system, the number and the date, say what happens and why, and use tables for facts and prose for reasons.
