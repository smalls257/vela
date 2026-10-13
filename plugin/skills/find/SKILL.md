---
name: find
description: Find where something is in the vault, fast, in the middle of a conversation. Takes a question in plain words ("how does coach talk to brightwater", "paper order", "who holds the budget"), and answers in a few lines with the places to look, best first, and the flows that cross them. Use when the user needs to locate a flow, an app, a contract or a question quickly, not a careful cited answer; that is /planner:ask.
argument-hint: "<what you are looking for, in your own words>"
model: haiku
allowed-tools: Read Bash(python3 *scripts/planner *)
disallowed-tools: Write Edit NotebookEdit
---

# Find it in the vault

The user is probably mid-conversation. Speed matters more than completeness: answer in seconds, in a few lines.

## Looking for

$ARGUMENTS

## Steps

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded).

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner query search <the user's words> --limit 6`.
2. If it finds nothing, or the top places don't match what was asked, the user's words are probably not the vault's. Think of the words the vault would use: the app, partner and flow names in the hits, and plain synonyms ("book" → "hold", "pay", "confirm"; "talk to" → the partner's name and "contract"). Search once or twice more with those. Read `12-glossary.md` only if that still fails. Stop after three searches in all.
3. Answer in this shape, and nothing longer:

   ```
   Best place: <title> — <path> › <heading>
   <one or two sentences from the hit's snippet, in plain words>

   Also: <title> — <path> › <heading>   (at most three of these, one line each)
   Flows that cross it: <flow title> — <path>   (when the search shows any)
   ```

   For a "how does …" question, put a flow first when one is among the hits. For "who …", put the item that names the owner first.
4. If the user asks to walk through a flow ("walk me through it", "show the steps"), Read that flow page's `## Steps` section and give the steps, numbered, one line each, in plain words, with the app that does each step first: "1. TickerTalk: the reader picks a stock and places a paper order, sent to Coach over Paper trades."
5. End with one line: "For a careful answer with every source checked: /planner:ask <question>."

## Rules

- Say only what the search output or a page you read says. Do not add facts, guesses or advice. If the snippet doesn't answer the question, say where to look and that the page holds the detail.
- Never print IDs on their own. Name things by title, with the path after.
- If three searches find nothing, say so in one line, name the closest place, and offer /planner:ask.
- Never write, edit or create a file.
