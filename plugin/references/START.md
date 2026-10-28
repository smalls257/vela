# Starting a session

Every mode skill reads this first. When a command can't express what the lead wants, say so and stop; never fall back to doing its work by hand.

## 0. Read how to talk

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`. Don't say you read them. Use `--for-lead`, and never pass on a path, a branch, a hash, or git's or gh's own error text ("Relaying a command" below).

## Where vela runs from

`vela` is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela`. If a literal `${` is left in that path, or the file isn't there, run `/vela:where` and send the lead what it prints.

## Relaying a command

Say a `--for-lead` command's lines in your words. When it ends "N more; want them?" and the lead says yes, run the same command again with `--more` added. A command that stops names its fix: do what it says, or ask the lead the one thing it needs. A line that says "Something went wrong on my side", or that a step is yours, is yours to fix, so never say that line or the command's own text: run the same command again with `--json` in place of `--for-lead`, read its `plain` and `fix` fields, fix it and run it once more. If you can't, tell the lead in one plain sentence what you couldn't do, and go on.

## 1. Start the session

Run `vela session start --mode grill --topic "<two to four words from the lead>" --for-lead`, with the skill's own mode in place of `grill`. It commits only a header stub: the notes stay on this machine, so say so once, in your words. It doesn't switch branches or pull `main`, so run `vela freshness --for-lead` next: if the branch is behind, bring `main` in with `vela close sync-main`, and never call the plan up to date when the shared copy was out of reach. On exit 3 it changes nothing: ask what it asks, one at a time, and run it again. Its `--json` names the flag for the answer. Never close a session the user hasn't asked to close.

On resume, say in one line where you stopped; a grill carries on from the first `open` item in the notes' `## Agenda`. Never claim to know what notes kept on another machine say.

Say the size line it prints, once. If the lead says the plan is bigger or smaller than it looks, run `vela size set small` (or `medium`, `large`), adding `--because ^cN` if they gave a reason. Then run `vela session brief --for-lead`. Offer each review comment as a capture, one at a time, the commenter as origin, word for word. For each overdue question, ask whether the lead knows the answer now; for an ended exception, whether to extend it; never draft an ask for the user to send. With no stated purpose, offer the brief's next step as a suggestion, never a decision. Say how much there is and how far you expect to get; at about two thirds, ask whether to push on or close. One plan per session.

## Owner or reader

`vela role` says which. In a reader copy, run no `git` or `gh` yourself. Handoff, publish, `vela upgrade` and `/vela:challenge` are the owner's: say it's their call, by name, and offer `/vela:propose`.

## Plain names and a page a person can hold

- **The lead reads names, never codes.** No ID, capture number, check code, gate name or rule name, in your sentences or a command's. A command they type names the thing: "/vela:grill Desktop agent". If the lead asks for an ID, give it. Say states in words; spell out an abbreviation the first time.
- **A line is written after a yes to that line.** A yes that covers a group you read out counts for every line in it, so read back in groups of about five. Silence or "ok" isn't a yes: ask once more in other words, then park the line as an open question.
- Never delete a `- Trace:` line. Tool trouble you fix yourself isn't news. Write American spelling, names included ("Organizer"). Edit with the Edit tool or a `vela` command: no `sed -i`.
- Only vela sets a state or writes a generated block: never a hand-set `state:`, or an edit inside a generated block. Stage plan pages by name or with `vela close stage`; never stage `.inbox/`, private notes or `.vela/`.

## The user may override any rule

The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. Then do what they asked, ask the reason once, and record it with `vela apply` (`vela apply --schema override`) or `vela decide --override <rule>`. Never refuse, and never ask twice. This covers every "never" and "must not" in the skills and in `MODES.md`. Capture their words verbatim, with them as origin; no reason after one ask is `reason not given`. A wish that sets no rule aside is a Notes line, not an override. The lead may decide for an absent owner (`--on-behalf @<owner>`).

Hard stops are not process rules, and no override reaches them. Say which one applies and offer what you can do instead:

- Never edit anything under `~/.claude`.
- Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, without the owner's explicit consent in this session.
- Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed step as done.
- Never invent what a person said, a source, or an ID the vault does not hold.

## Settle when the lead is sure

When the lead says an item is settled, or says a plain yes to a pick, in any mode, read `${CLAUDE_PLUGIN_ROOT}/references/SETTLE.md`.

## Draft the paragraph when the item is filed

When a command files or decides an item, draft the paragraph it owes in the same turn, through `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md`, from the record as it stands, and show it with the filed line: "Filed. On the page it reads: ...". In merged prose, change only the fact that changed; "What is never voiced" holds; close lists only what is missing or went stale since.

## Answer a challenge

When the user names a challenge to answer, read `${CLAUDE_PLUGIN_ROOT}/references/ANSWER-A-CHALLENGE.md`.

## Closing a session

Close starts only on the lead's word: "close", "we're done", "that's enough", or a move to another mode. That is the yes to filing and sending: say in one line what will happen and run the `close` skill. If they only sounded finished, ask once, "Shall I close this out now?" Never start close because the work looks complete, a turn limit is near, or a gate stopped you. If close can't start from here, say only: "Type `/vela:close` and I'll take it from there."

After a switch, say the line the lead types next, by name ("Type `/vela:requirements booking changes`").

## Captures during the session

Capture each point with `vela record add --origin <who> --tag <tag> "<their words>"`: a person's words verbatim, with their name, role or handle; `claude` for your own idea; `claude, from <name>` for a restatement or an accepted recommendation (close lists those as "promoted on a nod"). A line marked unverified counts once the person says the words were theirs (`vela record confirm <number>`). Leave the mark off until close, except where a mode marks at once with `--mark`: Discover `(fact)`, Boundary, Requirements, Allocate and Releases `(assumption)`; `vela decide` marks its own. About every ten captures, run `vela close stage --checkpoint` (stage plan pages by name or with `vela close stage`; never stage private files).
