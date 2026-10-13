---
name: house-voice
description: Draft or redraft the prose paragraphs of an initiative vault in the house voice, from the vault's own example passages. Close follows it for every paragraph a session needs. Use to draft a paragraph by hand outside a session.
argument-hint: "[page or paragraph to draft]"
disable-model-invocation: true
---

# House voice

Prose in this vault has one voice. Draft it from the example passages, not from rules alone. Prose is drafted only here, so every paragraph meets the examples.

## Load the examples

If the vault has `voice/VOICE.md`, read it first. It holds the owner's own rules for their pages, in their own words, and it sits above the rules at the end of this file and above the examples where they disagree. With no file, the defaults apply. The owner may override any default.

The examples are `voice/examples/<voice type>/*.md` in the vault, and `voice/local/<voice type>/*.md` when that gitignored folder exists on this machine. For the page you are drafting, find its voice type in the table below. Read every example of that type whose frontmatter says `state: active`, in file-name order, local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example, before you write a word. Skip every `state: retired` example. The order is fixed so two drafts of the same page start from the same context.

An example with `source: owner` or `source: owner-edit` is the owner's own writing. When `/planner:voice-seed` adds the owner's examples of a type, it retires that type's public seed, so the owner's voice is what you read.

If the type has fewer than two active examples across both folders, say "No examples for <type>: drafted without examples" in the PR body, and draft from the defaults at the end of this file.

Never read `voice/corpus/`. It is gitignored and stays out of every draft.

## Page types and voice types

A page's key is its `id` if the table lists it, and its `type` otherwise.

| Key | Voice type |
|---|---|
| `goals` | diagnosis |
| `solution-strategy` | decision |
| `capability-delta` | decision |
| `context-and-scope` | how-it-works |
| `constraints` | structured |
| `glossary` | structured |
| `initiative-section` | how-it-works |
| `index` | structured |
| `sources` | structured |
| `session` | structured |
| `app-building-blocks` | how-it-works |
| `app-runtime` | how-it-works |
| `flow` | how-it-works |
| `concern` | how-it-works |
| `decision` | decision |
| `epic` | how-it-works |
| `capability` | how-it-works |

`structured` means the page holds no voiced prose. Its content is tables, lists and fact bullets.

## What is never voiced

These keep the exact words they were written in. Do not restyle them:

- fact bullets, such as `**Owner:**` or `**Tested by:**`;
- tables;
- acceptance criteria, and the `- Trace:` line under each;
- `**Decision:**` and `**Dissent:**` lines;
- generated blocks;
- a person's words lifted from a capture;
- a sentence another page quotes as evidence: a reviewer question's `quote:` or a `source:` quote names its page, and `planner check` looks for those exact words there. Leave the sentence as it is, or rewrite it and change the quote in the same edit to the new words, which must carry the same fact. E802 from `planner check` means a quote lost its words.

## Prose that is already merged

Merged prose belongs to the vault and the people who edited it. When a session changes a fact in a merged paragraph, change only that fact and the fewest words grammar needs. If the change makes the paragraph wrong as a whole, rewrite it, and keep the old paragraph word for word in the session record under `## Replaced prose`, with the page and the date, so whoever wrote it can find it. Say so under **Prose drafted** in the pull request body. A page never carries two openings, and never a note to a reader about which paragraph to delete: those are editing notes, and a page with one ships as a draft.

## The rules

The examples are what to match. These rules are what to do where they are thin. Close and epics point here for page prose.

1. **Write like a senior technical writer explaining the system to a colleague.** Plain, spoken sentences in the active voice. Use negatives where a person would ("the agent doesn't send anything off the laptop"), and don't twist them into positives.
2. **Open with what the system does for people, then what is still open.** The first paragraph is two or three sentences, at most about 80 words and three links. It names threads, not items; the blocks and tables below list the items.
3. **Every sentence has a character.** The subject is a person, a team, an app, a document or a date: "Sam Hadley hasn't confirmed the 70% figure". Where a subject is "it", "this" or "there", find who acts and make that the subject. The subject may be the app: "Booking holds the seat for ten minutes".
4. **Give each point its true state, once.** Say whether it is assumed, decided or open, in one sentence, worded the way you would say it to a colleague. Never make it sound more certain than the record, and don't reach for the same phrase on every page. On a capability page and in a requirement, the paragraph says what the system will do, because it is planned, not built: "The Desktop agent will read a person's own calendar entries", not "reads", which says it already does, and not "the business can have".
5. **For anything open, say who settles it and by when,** in words, not codes: "the identity team needs to confirm this by 6 November". "The lead believes most of the team's work comes from client calls, and the pilot lead hasn't confirmed it" is a hedge a reader can use.
6. **One topic, under 120 words, ending on the last fact worth knowing.** A second topic starts a second paragraph. Start a sentence with what the last one left and end it on the new thing. The page type's own closing section, such as `## Out of scope`, is the only ending.
7. **Ask the reader to hold about four new things at once.** A paragraph that brings in more names, numbers or open points than that groups them ("three things hold up the first release") or moves them to a list or a table. People hold about four things in mind at once (Cowan); grouping is what keeps a long record readable.
8. **Point at a block or a table, and leave its numbers there.** Write "the open questions are listed below", and let the generated block carry the count.
9. **A criterion reads aloud.** It names things by their names and could be read to a tester over the phone. Its IDs sit on the `- Trace:` line under it, and a bracketed aside becomes a clause that says who says it.
10. **Write about the system and the people, not about the record.** Not "we've written down", "the vault says" or "this page records". How a decision was reached, and which session added what, is the page's `## History`.
11. **Keep the owner's words and the record's facts.** Who said what, and every state word, number, date and negation, stay as the record has them, even when a smoother sentence is tempting. A merged paragraph changes only the fact that changed; voicecheck says so when one is gone.

Write paragraphs where the page asks for prose: a run of bullets that are not fact bullets is a paragraph waiting to be written. Name things in the sentence and keep their IDs on a `- Trace:` line. Facts come from somewhere. Every number, date and ID in a draft comes from a capture, a source or a page; where you cannot point to it, leave it out. Spell an abbreviation out at its first use on the page, put a link on the words that rely on a source or point at an item, and link every ID as `CONVENTIONS.md` says under "Pages". A paragraph says what is true now; how a decision was reached is the page's `## History`.

## Pages that are mostly a list

Unknowns and risks, concerns, decisions, sources and any page that is mostly a list have two parts, and the opening never does the second part's job.

1. **An opening that counts and points.** Two or three plain sentences: how many are open, which few hold the rest up, and the most urgent with its date. "28 questions are open. Five hold up the first release; the most urgent is who owns Heron, due 23 October." It names about three items at most and sends the reader to the list below.
   This opening, from an unknowns page, is the shape to match, and it fits the opening's limit of about 80 words. One call holds most of the page up, so it comes first; the documents nobody is writing are one sentence; the newest question closes it with a pointer to the list:

   > One open call holds up most of this page: who settles whether meeting text may leave the laptop. Most other questions wait on it, or on the lawful basis for each source. Three documents have an owner and a date but nobody writing them yet. The newest question is whether the works council votes on the pilot; everything else is listed below, grouped by what it holds up.

2. **The items as a grouped list.** Group by what they hold up (the first release, the prep-note requirements, the security review), about seven to a group. Each line reads: the plain name, who to ask and by when, what it holds up. Anything past seven in a group goes under `## Also open (n)`, which the viewer folds.

## Size

If a PR would change more than about 20 prose paragraphs, ask: "<n> paragraphs changed. Split into PRs by page group, or open one PR?"

## When examples are thin

Follow the rules above, rule 1 first: a senior technical writer explaining the system to a colleague. Name the system, the number and the date, say what happens and why, and use tables for facts and prose for reasons.
