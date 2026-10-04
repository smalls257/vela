---
name: house-voice
description: Draft or redraft the prose paragraphs of an initiative vault in the house voice, from the vault's own example passages. Close follows it for every paragraph a session needs. Use to draft a paragraph by hand outside a session.
argument-hint: "[page or paragraph to draft]"
disable-model-invocation: true
---

# House voice

Prose in this vault has one voice. Draft it from the example passages, not from rules alone. Prose is drafted only here, so every paragraph meets the examples.

## Load the examples

The examples are `voice/examples/<voice type>/*.md` in the vault. For the page you are drafting, find its voice type in the table below. Read every example of that type whose frontmatter says `state: active`, in file-name order, before you write a word. Skip every `state: retired` example. The order is fixed so two drafts of the same page start from the same context.

An example with `source: owner` or `source: owner-edit` is the owner's own writing. When `/planner:voice-seed` adds the owner's examples of a type, it retires that type's public seed, so the owner's voice is what you read.

If the type has fewer than two active examples, say "No examples for <type>: drafted without examples" in the PR body, and draft from the defaults at the end of this file.

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
- acceptance criteria;
- `**Decision:**` and `**Dissent:**` lines;
- generated blocks;
- a person's words lifted from a capture.

## Prose that is already merged

Merged prose belongs to the vault and the people who edited it. When a session changes a fact in a merged paragraph, change only that fact and the fewest words grammar needs. If the change makes the paragraph wrong as a whole, leave it alone and add a new paragraph under it that starts `> Replaces the paragraph above after <session id>; delete one.` A person picks.

## Numbers and IDs

- Cite a generated block rather than restating its numbers. Write "the open unknowns are listed in Where it stands", not "there are 3 open unknowns".
- Every number, date and ID in a draft must come from a capture, a source or a page. If you cannot point to where it came from, leave it out.
- Link every ID the way `CONVENTIONS.md` says.

## Size

If a PR would change more than about 20 prose paragraphs, ask: "<n> paragraphs changed. Split into PRs by page group, or open one PR?"

## Defaults when examples are thin

Write the way a senior engineer explains something to a peer they respect. Plain words, short sentences, active voice. Name the system, the number and the date. Say what happens and why. Use tables for facts and prose for reasons. If a sentence explains nothing, cut it. No dashes for asides, no rhetorical questions, no closing summary that repeats the page.
