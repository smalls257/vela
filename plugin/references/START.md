# Starting a session

Every mode skill reads this before its own steps. The vault root is the plan's folder. Read the vault's format with `vela conventions "<section>"`, one section at a time. When a command can't express what the lead wants, say so and stop; never fall back to doing its work by hand.

## 0. Read how to talk

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one (the owner's own rules, above the defaults), then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`. Don't tell the lead you read it. What a command prints reaches the lead in that voice and in your words: use `--for-lead` where the command has it, and never pass on a path, a branch, a hash, or git's or gh's own error text. "Relaying a command" below says what to do when a line says something went wrong.

## Offering a session

When a question would be better answered by a session, say which one in plain words and why ("this is a job for a grill: it settles the question and files the answer"), ask once, and start it only on a yes. A no, or silence, means answer the question as asked. Never start a session that writes or commits without that yes. The person may also type the command themselves; that is the yes.

## Relaying a command

Run a command with `--for-lead` whenever the lead will hear what it says, and say its lines in your words. Its lines stop at about four and end with a count, such as "Three more; want them?"; when the lead says yes, run the same command again with `--more` added. A command that stops names its fix: do what the fix says, or ask the lead the one thing it needs. A `--for-lead` line that says "Something went wrong on my side" means the command stopped for a reason that is yours to fix (an ID, a field or a flag you gave it), so never say that line or the command's own text. Run the same command again with `--json` in place of `--for-lead`, read why in its `plain` and `fix` fields, fix it if you can and run it once more. If you can't, tell the lead in one plain sentence what you couldn't do, and go on.

## Where vela runs from

`vela` is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela`. If a literal `${` is left in that path, or the file isn't there, run `/vela:where` and send the lead what it prints. Don't guess a path, and don't say which one you picked.

## 1. Start the session

Run `vela session start --mode grill --topic "<two to four words from the lead's first message>" --for-lead`, with the skill's own mode in place of `grill` (repeat `--mode` for a session that runs two). It opens the record on the branch the lead is on and doesn't switch branches or pull `main`; say what it means in your words, and never call the plan up to date when the shared copy was out of reach. If `vela freshness` says the branch is behind, offer to bring `main` in (`vela close sync-main`). On exit 3 it changes nothing: ask what it asks, one at a time, and run it again. Never close a session the user hasn't asked to close. On resume, say in one line where you stopped; a grill carries on from the first `open` item in the record's `## Agenda`.

Then run `vela session brief --for-lead`. Offer each review comment it lists as a capture, one at a time, the commenter as origin and the comment word for word. For each overdue unknown, ask whether the lead knows the answer now, as `MODES.md` says under "Unknowns"; never draft an ask for the user to send. With no stated purpose, offer the brief's next step as a suggestion, never a decision.

Say the session's name in half a sentence, and in one sentence how much there is and how far you expect to get; at about two thirds, ask whether to push on or stop and close. One plan per session: if the lead names another plan, close this one first.

## Owner or reader

`vela role` says which: an owner works in the vault's git clone, a reader in a published copy with no `.git`. In a reader copy, run no `git` or `gh` yourself, say once "This is a read copy, so I will not use git: your work stays in this folder and nothing is committed or sent," and run `vela freshness --for-lead`. Handoff, publish, `vela upgrade` and `/vela:challenge` are the owner's: "That is <name>'s call. Send a proposal (`/vela:propose`) and they decide."

## Plain names and a page a person can hold

- **The lead reads names, never codes.** No ID, capture number, check code, gate name or rule name reaches the lead, for any kind of thing in the plan. Say the name; where the lead must act on one, the ID follows as a tag, and a command they type names the thing: "/vela:grill Desktop agent". If the lead asks for an ID, give it. Say states in words, and spell out an abbreviation the first time.
- **Answer first, then about four things at most for the lead to judge**, each with your recommendation; a longer list is grouped or offered ("there are six more; want them?"). One question at a time, never without a view.
- **A line is written after a yes to that line.** A yes that covers a group you read out ("yes to these five") counts for every line in it, so read sheets, criteria and rows back in groups of about five. Silence or "ok" isn't a yes: ask once more in different words, then park the line as an open question.
- Never delete a `- Trace:` line or turn one into prose. Write American spelling, names included ("Organizer"). Run the review checkpoint as `REVIEW.md` says. Tool trouble you fix yourself isn't news.

## Shell that runs on a Mac and on Linux

Edit with the Edit tool or a `vela` command, never in place from the shell: no `sed -i`, and no `\n`, `\+` or `\|` in a `sed` replacement.

## The user may override any rule

The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. Then do what they asked, ask the reason once, and record it with `vela apply` (`vela apply --schema override` gives the fields) or `vela decide --override <rule>`. Never refuse, and never ask twice.

This covers the grill gates, "only a grill decides", an open unknown that blocks an item, an absent owner, and every "never" and "must not" in the skills and in `MODES.md`. Capture their words verbatim, with them as origin; the override points at that capture. With no reason after one ask, the reason is `reason not given`. A wish that sets no rule aside is a Notes line, not an override. The lead may decide for an absent owner (`vela decide --on-behalf @<owner>`); the owner confirms later or raises `/vela:challenge`. `vela whoami` gives the lead's handle, asking once if it must.

Hard stops are not process rules, and no override reaches them. Say which one applies and offer what you can do instead:

- Never edit anything under `~/.claude`.
- Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, without the owner's explicit consent in this session.
- Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed step as done.
- Never invent what a person said, a source, or an ID the vault does not hold.

## Answer a challenge

When the user names a challenge to answer, by its PR number or the challenged ID, read `${CLAUDE_PLUGIN_ROOT}/references/ANSWER-A-CHALLENGE.md`. The answer is made on the challenge's own branch, so the challenge and its answer land in one PR.

## Closing a session

Close starts only on the lead's word: "close", "we're done", "that's enough", or a request to move to another mode (the open session closes first). That is the yes to filing; say in one line what will happen ("I'll file your notes, write the pages and send the branch for review"), and run the `close` skill in this conversation. If they only sounded finished, ask once, "Shall I close this out now?" Never start close because the work looks complete, a turn limit is near, or a gate stopped you. If close can't be started from where you are, say only: "Type `/vela:close` and I'll take it from there."

One confirmation stays, before anything leaves the machine: close says what will be sent and waits for a yes (close, section 7). That yes, given after close says what goes, is the only one that sends. Typing `/vela:close`, saying "close", or saying "push" before then is consent to file, not to send company material. After a switch, say the one line the lead types next, by name ("Type `/vela:requirements booking changes`").

## Captures during the session

Capture each point with `vela record add --origin <who> --tag <tag> "<their words>"`. A person's words are quoted verbatim, with their name, role or handle as the origin; Claude's own idea has origin `claude`; a restatement, or Claude's recommendation the user accepts, has origin `claude, from <name>`; close lists those lines under "promoted on a nod". Leave the mark off until close, except in the modes that mark at once with `--mark`: a grill marks the deciding capture `→ keep: [[<page>#<heading>|<ID>]] (decided)`; a Discover marks each fact `(fact)`; Boundary, Requirements, Allocate and Releases mark each line `(assumption)`. After about every ten captures, run `vela close stage --checkpoint` (never `git add -A`: a hook only denies it where hooks run).
