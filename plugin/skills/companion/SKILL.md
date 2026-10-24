---
name: companion
description: "Keep the panel beside the chat current: the session companion after each vela write, the plan companion with each answer about the plan, and where things stand when someone asks. Offer it when someone asks where we are or wants the plan beside the chat; start it only on a yes. After that it never takes a turn of its own unless asked."
allowed-tools: Read Bash(sh *scripts/run-vela *) Artifact
---

# The panel beside the chat

Before you say anything, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, for how to talk.

The panel only shows. Nothing in it sends anything back to you, and you never act on it. Everything the panel says comes from vela's own files in `.vela/companion/`. You publish a file; you never make one.

## What the panel is

vela draws it. You publish the file vela wrote, exactly as written, to the same artifact each time ("This session" for the session panel, "The plan" for the plan panel). Never write or edit its HTML: a second hand on the page is a second set of numbers, and the lead would see two answers.

## The session panel rides on a vela write

When a turn runs a vela command that writes (decide, record add, add, apply, map, a page edit through vela), put `; sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela companion session --html` at the end of that same Bash command, and in the same message, after that Bash call, publish `.vela/companion/session.html`. Never publish in a message of its own, and never in a turn that wrote nothing: an extra round costs the lead seconds every turn.

## The plan panel comes with the answer

For a question about where the plan stands, pick the one view that fits:

- track ("are we on track for the date?")
- stuck ("what's stuck?")
- needs ("what do you need from me?")
- left ("how much is left?")
- who ("who has what?")
- flow ("how does the booking flow work?", with `--about` and the flow's name)
- page ("what does the plan say about pricing?", with `--about` and the page's name)

Run it first, for example `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela companion explain --view stuck --html`. Start your answer with its `headline` sentences, word for word, then say what matters in your own words, and end with its `not_recorded` line when it has one. Say no number the panel doesn't show.

Write your answer text first, then publish `.vela/companion/explain.html` after it in that same message: the director reads the answer at once, and the publish follows it. If the panel feels slow to the person, drop the publish and show it only when they ask.

On exit 3, ask what it asks, once, and run it again with `--as` and the handle they give. On exit 1, ask which of the names it offered they meant.

## When no view fits

Answer with `/vela:ask` and run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela companion explain --view none --html`, publishing it with the answer, so the panel never shows the last question's view beside a different answer.

## Show me where we are

When the person asks for it ("show the panel", "where are we"), this is the one time the panel gets its own turn, because they asked: run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela companion session --html` (or `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela companion explain --view left --html` when no session is open), publish it, and say in one line what it shows.

## Where nothing can be published

With no artifact tool here, or when the publish fails, say once: "I can't show the panel here. It's in .vela/companion/session.html in this folder." Don't say it again that session, and never claim the panel updated.

## How current it is

The panel's header says how current it is ("as of 10:41 · capture 14"). If vela's hook says the panel is behind, follow the line it gives with your next write.
