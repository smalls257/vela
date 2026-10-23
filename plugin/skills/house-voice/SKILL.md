---
name: house-voice
description: "Draft or redraft plan prose in the house voice, from the vault's own examples. Offer it when someone wants a paragraph written or reworded to sound like the plan; start it only on a yes."
argument-hint: "[page or paragraph to draft]"
---

# House voice

Prose in this vault has one voice. Draft it from the example passages and the default voice below, not from rules alone.

## Load the examples

If the vault has `voice/VOICE.md`, read it first. It holds the owner's own rules, and wins over the default voice below and the examples where they disagree. Run by hand, outside a session, read `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md` too, before your first question.

Then run `vela voice examples --page <page> --json` (`--key <page id or type>` for a page with no file yet). Read every example of that type it lists, in the order it lists them, before you write a word: active examples in file-name order, local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example. An `owner` or `owner-edit` example is the owner's own writing. A public seed shows what a page of its type covers and in what order; take the sentences from the default voice below. With fewer than two active examples across both folders, it says to write "No examples for <type>: drafted without examples" in the PR body; do so, and draft from the default voice. Never read `voice/corpus/`.

## What is never voiced

These keep the words they were written in: fact bullets; tables, a contract's case table above all; acceptance criteria and their `- Trace:` lines; `**Decision:**` and `**Dissent:**` lines; generated blocks; a person's words lifted from a capture; and a sentence another page quotes as evidence (leave it, or rewrite it and change the quote in the same edit to the new words, which carry the same fact).

## Prose that is already merged

Merged prose belongs to the people who edited it. When a fact in it changes, change only that fact and the fewest words grammar needs. If the paragraph is then wrong as a whole, first run `vela prose replace --page 05-building-blocks/till.md --line 12` (any line of the paragraph will do). Never copy it by hand. Say so under **Prose drafted** in the pull request body. A page never carries two openings, or a note to a reader about which paragraph to delete.

## The default voice

Until the owner has examples of their own, pages read like a senior colleague explaining the plan across a desk to someone on the team who wasn't in the sessions: someone who knows the company and everyday words, not this plan's own names. A line in the owner's `voice/VOICE.md` wins over any line here, and so do their own examples.

Explain what that reader would stop to ask, and nothing they already know. The opening paragraph of a page does most of the explaining, so it may run longer than what it replaces; the paragraphs below lean on it, and a redraft of one comes out no longer than what it replaces, and usually shorter.

- **Write like a senior technical writer explaining the system to a colleague:** plain, spoken sentences in the active voice. Use negatives where a person would ("the agent doesn't send anything off the laptop"), and don't twist them into positives. Contract the way people talk: hasn't, won't, can't.
- **Introduce this plan's names the first time a page uses them:** the product ("Dockside, the bike-share app for the Riverside docks"), a screen, a person by name or role and what they do. Say what a run of abstract nouns stands for ("paying by card at the dock, a rider account, and a way to report a broken bike", not "payment, accounts and repair"). Don't gloss everyday or company words, and don't introduce the lead to their own role.
- **Every sentence has a character:** a person, a team, an app, a document or a date. Where the subject is "it", "this" or "there", find who acts. Say "we" for the team and the role for one person; "you" is the reader.
- **Short sentences carry the facts, one point each with at most one addition:** an aside, a reason, a "so", or a list. A second addition starts a new sentence: "The pilot lead counted 40 percent of trips starting at the station docks. We only believe that figure, because nobody has seen the count." Put the cause first. Let a period do a formal linking word's work, and open on the point.
- **Say a point's state with its verb, once.** Never make it sound more certain than the record: "we're assuming the first release is a pilot", "the city lawyer hasn't been asked yet". Never tag it on ("That isn't decided.", "and that is still open"). On a capability page and in a requirement, say what the system will do, because it is planned: "The Rider app will unlock a bike at any dock", not "unlocks" and not "the business can have".
- **Use the plain word, never vela's own, even where the record uses it:** "holds up", not "gates"; "a session to test it", not "a grill"; "the acceptance criteria", not "the checks".
- **For anything open, say who settles it and by when,** in words, not codes: "the payments team needs to confirm this by November 6". Answer the reader's next question in the next sentence only with a reason someone recorded; with none, write "the reason isn't recorded yet". Say it as a statement, not as a question put to the reader. End an open list with a recorded next step, or with what's open and who's been asked.
- **Never hedge a point the record marks decided.** An absence is "not recorded as agreed", never "nobody has…" as fact.
- **Sound sure only about what someone said or a source shows.** What you know yourself is "worth checking", or a question for the lead. A consequence is written only if someone said it. A number or date needs a source, or "no figure given yet". A what-if is framed as one ("suppose", "if"), uses only what the plan or the lead has said, and never reports a new event as having happened.
- **Keep the owner's words and the record's facts.** Who said what, and every state, number, date and negation, stay as the record has them, even when a smoother sentence tempts. Keep the state, not the record's word for it.
- **Write about the system and the people, not about the record:** not "we've written down" or "this page records". How a decision was reached is the page's `## History`.
- **Open with what the system does for people, then what is still open,** in two or three short sentences naming threads, not items; point at the list or table below for the rest.
- **One topic a paragraph, ending on the last fact worth knowing.** Ask the reader to hold only a few new things at once; more becomes a group ("three things hold up the first release") or a list.
- **A criterion reads aloud,** by names, as it could be read to a tester over the phone.
- **Be warm by being direct.** No jokes.
- **Spell in American English and write dates in American order:** "October 14" this year, "October 14, 2026" in any other, "Tuesday, February 2, 2027" with a weekday; ISO stays in frontmatter, tables of record and IDs.

Every number, date and ID in a draft comes from a capture, a source or a page; where you can't point to it, leave it out. Link the words that rely on a source or point at an item. A run of bullets that aren't fact bullets is a paragraph waiting to be written.

The shape to match, on an invented initiative; the opening explains and the item under it leans on it:

> Two releases are planned. The first is a pilot at the Riverside docks, starting Wednesday, March 3, 2027, where riders will unlock and return bikes, along with what that needs: paying by card at the dock, a rider account, and a way to report a broken bike. The pilot is still an assumption, not a decision, and two open questions could move the date. Paying by phone waits for the second release, which has no date yet.
>
> The card processor has to certify the dock reader before the pilot. We don't know how long that takes, so the payments team is asking by November 6. The pilot lead says the timeline is tight, so this holds up the March 3 date.

## Pages that are mostly a list

Unknowns and risks, concerns, decisions, sources and any page that is mostly a list have two parts:

1. **An opening that counts and points:** two or three sentences, how many are open, which few hold the rest up, and the most urgent with its date, naming about three items at most. "One open call holds up most of this page: who settles whether docks may stand on the pavement. Most other questions wait on it, or on what the card processor will certify. The newest question is whether the transport committee votes on the pilot; everything else is listed below, grouped by what it holds up." A new item joins its group; the opening isn't extended to mention it.
2. **The items as a grouped list,** by what they hold up, about seven to a group. Each line: the plain name, who to ask and by when, what it holds up. Past seven, the rest go under `## Also open (n)`.
