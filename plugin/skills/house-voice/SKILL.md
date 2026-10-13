---
name: house-voice
description: Draft or redraft the prose paragraphs of an initiative vault in the house voice, from the vault's own example passages. Close follows it for every paragraph a session needs. Use to draft a paragraph by hand outside a session.
argument-hint: "[page or paragraph to draft]"
disable-model-invocation: true
---

# House voice

Prose in this vault has one voice. Draft it from the example passages, not from rules alone. Prose is drafted only here, so every paragraph meets the examples.

## Load the examples

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
- a person's words lifted from a capture.

## Prose that is already merged

Merged prose belongs to the vault and the people who edited it. When a session changes a fact in a merged paragraph, change only that fact and the fewest words grammar needs. If the change makes the paragraph wrong as a whole, rewrite it, and keep the old paragraph word for word in the session record under `## Replaced prose`, with the page and the date, so whoever wrote it can find it. Say so under **Prose drafted** in the pull request body. A page never carries two openings, and never a note to a reader about which paragraph to delete: those are editing notes, and a page with one ships as a draft.

## The ten rules

The examples are what to match. These ten rules are what to do where they are thin, and they are repeated nowhere else: close and epics point here.

1. **Open with the answer.** The first paragraph says what is true now and the one thing that most holds it up, in two or three sentences, at most about 80 words and three links. It names threads, not items. The blocks and tables below list items.
2. **Every sentence has a character.** The subject is a person, a team, an app, a document or a date: "Sam Hadley has not confirmed the 70% figure". Where a subject is "it", "this" or "there", find who acts, and make that the subject. The subject may be the app: "Booking holds the seat for ten minutes".
3. **Say a state once.** A paragraph names what is open or assumed once, in one sentence, and links it there. When three things are open, one sentence lists the three.
4. **One topic, under 120 words.** A second topic starts a second paragraph. Four links make a table or a list under a heading.
5. **Old before new, point at the end.** Start the sentence with what the last sentence left, and end it on the new thing.
6. **Hedge by saying who and what would settle it.** "The lead believes most of the team's work comes from client calls, and the pilot lead has not confirmed it" is a hedge a reader can use.
7. **Point at a block or a table; leave its numbers there.** Write "the open unknowns are listed below", and let the generated block carry the count.
8. **A criterion reads aloud.** It names things by their names and could be read to a tester over the phone. Its IDs sit on the `- Trace:` line under it, and a bracketed aside becomes a clause that says who says it.
9. **End on the last fact.** The last paragraph is the last thing worth knowing. The page type's own closing section, such as `## Out of scope`, is the only ending.
10. **Keep the owner's words.** A merged paragraph changes only the fact that changed. A rewrite keeps every negation, number and state word of the paragraph it replaces; voicecheck says so when one is gone.

Write paragraphs where the page asks for prose: a run of bullets that are not fact bullets is a paragraph waiting to be written. Name things in the sentence and keep their IDs on a `- Trace:` line. Facts come from somewhere. Every number, date and ID in a draft comes from a capture, a source or a page; where you cannot point to it, leave it out. Spell an abbreviation out at its first use on the page, put a link on the words that rely on a source or point at an item, and link every ID as `CONVENTIONS.md` says under "Pages". A paragraph says what is true now; how a decision was reached is the page's `## History`.

## Pages that are mostly a list

Unknowns and risks, concerns, decisions, sources and any page that is mostly a list have two parts, and the opening never does the second part's job.

1. **An opening that counts and points.** Two or three plain sentences: how many are open, which few hold the rest up, and the most urgent with its date. "28 questions are open. Five hold up the first release; the most urgent is who owns Heron, due 23 October." It names about three items at most and sends the reader to the list below.
2. **The items as a grouped list.** Group by what they hold up (the first release, the prep-note requirements, the security review), about seven to a group. Each line reads: the plain name, who to ask and by when, what it holds up. Anything past seven in a group goes under `## Also open (n)`, which the viewer folds.

## Size

If a PR would change more than about 20 prose paragraphs, ask: "<n> paragraphs changed. Split into PRs by page group, or open one PR?"

## Defaults when examples are thin

Write the way a senior engineer explains something to a peer they respect: plain words, short sentences, active voice. Name the system, the number and the date. Say what happens and why. Use tables for facts and prose for reasons. The ten rules above carry the rest.
