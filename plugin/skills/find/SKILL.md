---
name: find
description: Find where something is in the plan, fast, mid-conversation ("how does the app talk to spokewell", "who owns repairs"). Answers in a few lines with the best places to look and the journeys that use them. For a careful cited answer, use /vela:ask.
argument-hint: "<what you are looking for, in your own words>"
model: haiku
allowed-tools: Read Bash(sh *scripts/run-vela *)
disallowed-tools: Write Edit NotebookEdit
---

# Find it in the vault

Before you say anything, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, for how to talk.

The user is probably mid-conversation. Speed matters more than completeness: answer in seconds, in a few lines.

## Looking for

$ARGUMENTS

## Steps

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded).

1. Run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela query search <the user's words> --limit 6`.
2. If it finds nothing, or the top places don't match what was asked, the user's words are probably not the plan's. Think of the words the plan would use: the app, partner and flow names in the hits, and plain synonyms ("book" → "hold", "pay", "confirm"; "talk to" → the partner's name and "contract"). Search once or twice more with those. Read `12-glossary.md` only if that still fails. Stop after three searches in all.
3. Answer in this shape, and nothing longer:

   ```
   Best place: <title> (<page title> page, "<heading>")
   <one or two sentences from the hit's snippet, in plain words>

   Also: <title> (<page title> page, "<heading>")   (at most three, one line each)
   Journeys that use it: <flow title>   (when the search shows any)
   ```

   For example: `Best place: Record consent (Consent and identity page, "Record consent")`. For a "how does …" question, put a flow first when one is among the hits. For "who …", put the item that names the owner first.
4. If the user asks to walk through a flow ("walk me through it", "show the steps"), Read that flow page's `## Steps` section and give the steps, numbered, one line each, in plain words, with the app that does each step first: "1. Rider app: the rider scans a dock and asks to unlock, sent to the Dock service over Dock unlock."
5. End with one line: "For a careful answer with every source checked: /vela:ask <question>."

## Rules

- Say only what the search output or a page you read says. Don't add facts, guesses or advice. If the snippet doesn't answer the question, say where to look and that the page holds the detail.
- Never print IDs or file paths. Name things by title, and the page by its title.
- If three searches find nothing, say so in one line, name the closest place, and offer /vela:ask.
- Never write, edit or create a file.
