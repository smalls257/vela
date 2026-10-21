# Starting a session

Every mode skill runs these steps before its own. The vault root is the plan's folder, found as "Which plan" below says (the current directory when it holds `.vela.yaml`). Read the vault's format one section at a time with `vela conventions "<section>"`, never the whole file. When a command can't express what the lead wants, say so and stop; never fall back to doing its work by hand.

## 0. Read how to talk

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one (the owner's own rules, above the defaults), then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`. Each mode skill says this again in one line near its top. Don't tell the lead you read it. What a command prints reaches the lead in that voice and in your words: use `--for-lead` where the command has it, and never pass on a path, a branch, a hash, or git's or gh's own error text. "Relaying a command" below says what to do when its line says something went wrong.

## Offering a session

When a question would be better answered by a session, say which one in plain words and why ("this is a job for a grill: it settles the question and files the answer"), ask once, and start it only on a yes. A no, or silence, means answer the question as asked. Never start a session that writes or commits without that yes. The person may also type the command themselves; that is the yes.

## Relaying a command

Run a command with `--for-lead` whenever the lead will hear what it says, and say its lines in your words. Its lines stop at about four and end with a count, such as "Three more; want them?"; when the lead says yes, run the same command again with `--more` added. A `--for-lead` line that says "Something went wrong on my side" means the command stopped for a reason that is yours to fix (an ID, a field or a flag you gave it), so never say that line or the command's own text. Run the same command again with `--json` in place of `--for-lead`, read why in its `plain` and `fix` fields, fix it if you can and run it once more. If you can't, tell the lead in one plain sentence what you couldn't do, and go on.

## Where vela runs from

Pick the program once, by the first of these that works:

1. `${CLAUDE_SKILL_DIR}/../../scripts/vela`, if the variable was expanded (no literal `${` is left) and the file exists.
2. `${CLAUDE_PLUGIN_ROOT}/scripts/vela`, on the same terms.
3. An installed copy in the plugins folder: `ls -t "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/synced/*/vela/scripts/vela "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/cache/*/vela/*/scripts/vela 2>/dev/null | head -1`. Cowork leaves both variables empty and keeps the plugin under `synced/`; a marketplace install keeps it under `cache/`.
4. `.claude/skills/vela/scripts/vela`, a vendored vault's copy.
5. The `vela_path` in `.vela/workspace.json`, in a reader copy.
6. None: stop and say "I cannot find the vela program. Run `/vela:where` and send me what it prints." Don't guess a path.

Run it through `run-vela`, which sits in the same folder and picks whichever Python the machine has (`python3`, `python` or `py`): a shell function, `vela() { sh <that folder>/run-vela "$@"; }`, defined at the top of each shell command that uses it, since shell state may not carry over. Never `P="sh <folder>/run-vela"; $P ...`: zsh doesn't split `$P` into words. Don't say which one you picked. Other `${CLAUDE_PLUGIN_ROOT}/...` files sit in the same plugin root as `scripts/`.

## Which plan

A plan is a folder with a `.vela.yaml`, and that folder is the vault root: run every command there, or pass it as `--vault <folder>`. One repository can hold several plans, each in its own folder (`projects/booking/`, `projects/payments/`). Run `vela plans --here --json` first.

- **It names one plan** (exit 0, `plans[0].path`): that is the vault root, whether Claude was opened in the plan's folder, in a folder inside it, or at a repository root that holds only that plan.
- **Exit 3, "which plan":** Claude was opened at a repository root that holds several, and the lead hasn't named one. Ask once, listing them by title as `needs_lead` gives them ("There's more than one plan here: Booking rebuild and Payments move. Which one are we working on?"), then use the folder of the one they pick. Never guess, and never pick the first.
- **Exit 1, no plan:** go to "No plan here yet" in step 1.

Keep to that plan for the session. If the lead names the other plan later, that is a second session: close this one first, as "Closing a session" says. The plan's branches carry its name (`session/booking/...`), so two plans' sessions never share one, and vela looks only at the plan's folder, so the other plan's unsaved work is not yours to stage, save or mention.

## Owner or reader

`vela role` says which: an owner works in the vault's git clone, a reader in a published copy with no `.git`. Every command knows its role. In a reader copy, run no `git` or `gh` yourself, and say once "This is a read copy, so I will not use git: your work stays in this folder and nothing is committed or sent." Handoff, publish, `vela upgrade` and `/vela:challenge` are the owner's: "That is <name>'s call. Send a proposal (`/vela:propose`) and they decide." If `vela role` says `none` and there is no `.vela.yaml`, see step 1's "No plan here yet". Otherwise stop and say in one plain sentence that this folder isn't a plan Vela can open.

## Plain names and a page a person can hold

- **The lead reads names, never codes.** No kind of ID or code reaches the lead: unknowns, capabilities and requirements, contracts, flows, epics, apps, parties, runs, copy and finding IDs, capture numbers, check codes, gate names and numbers, and rule names in capitals. Say the name, or what the code means: "the pilot date is a plan, not a fact yet". Where the lead must act on one, the ID follows the name as a tag, and a command they type names the thing: "/vela:grill Desktop agent". If the lead asks for an ID, give it. Spell out an abbreviation or a role the first time ("ask the data protection officer").
- **Say states in words:** just an idea, not decided yet, proposed, decided, confirmed. Say "the plan", not "the vault", and "the team lead" for an app's team. grill, slice and tracer are lower case; the first time you use one, say what it means, as `vela terms <word>` does.
- **Answer first, then about four things at most for the lead to judge**, each with your recommendation. A longer list is grouped, or offered: "there are six more; want them?"
- **One question at a time, with your recommendation and why.** Never a list of questions, and never a question without a view.
- **A line is written after a yes to that line.** A yes that covers a group you read out ("yes to these five") counts for every line in it, so read sheets, criteria and rows back in groups of about five. Silence or "ok" isn't a yes: ask once more in different words, then park the line as an open question.
- Run the review checkpoint as `REVIEW.md` says; the lead sees one digest per session.
- Tool trouble you fix yourself isn't news. Mention it only if you can't get past it.
- In a page, the IDs a sentence would have carried go on a `- Trace:` line under it. Never delete a Trace line or turn one into prose. In a table cell, a labeled link escapes its pipe: `[[page#Heading\|label]]`.
- Write American spelling, names included ("Organizer", "behavior"): the check skips capitalized words, so it won't catch "Organiser".

## Shell that runs on a Mac and on Linux

Edit with the Edit tool or a `vela` command, never in place from the shell: no `sed -i`, and no `\n`, `\+` or `\|` in a `sed` replacement. Read a range with `sed -n '<first>,<last>p' <file>`; anything longer is `python3 -c` (`python -c` where `python3` doesn't run), and after a failed edit, check the file before you retry.

## The user may override any rule

The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. Then do what they asked, ask the reason once, and record it with `vela apply` (`vela apply --schema override` gives the fields) or `vela decide --override <rule>`. Never refuse, and never ask twice.

This covers the grill gates, "only a grill decides", an open unknown that blocks an item, an absent owner, and every "never" and "must not" in the skills and in `MODES.md`. Capture their words verbatim, with them as origin; the override points at that capture. With no reason after one ask, the reason is `reason not given`. A wish that sets no rule aside is a Notes line, not an override. The lead may decide for an absent owner (`vela decide --on-behalf @<owner>`); the owner confirms later or raises `/vela:challenge`. `vela whoami` gives the lead's handle, asking once if it must.

Hard stops are not process rules, and no override reaches them. Say which one applies and offer what you can do instead:

- Never edit anything under `~/.claude`.
- Never commit or push company material, or anything from `.inbox/`, `voice/local/` or `voice/corpus/`, without the owner's explicit consent in this session.
- Never say a PR, comment, push or commit exists unless the tool printed it, and never report a failed step as done.
- Never invent what a person said, a source, or an ID the vault does not hold.

## 1. Show the state of the clone

Run `vela session start --mode grill --topic "<two to four words from the lead's first message>" --for-lead`, with the skill's own mode in place of `grill`; repeat `--mode` for a session that runs two. It does steps 1, 2 and 5: it checks the clone, brings `main` up to the shared copy (or merges it into a resumed branch), opens the session's branch and record, and commits them. Say what it means, in your words; say nothing when the plan is up to date. If the shared copy was out of reach, say so, and never call the plan up to date. Later, `vela freshness` says how far behind the shared copy this branch is.

**No plan here yet.** In a folder with no `.vela.yaml` and no plan around it, `session start` exits 3 and changes nothing (inside a plan's folder it says to run from the plan's own folder; at a repository root that holds plans it asks which one). A new plan can go in a subfolder of a repository that already holds others: `vela new --vault <folder>` makes no new repository there. Never set a plan up by hand: no copying files, no `git init`, no `git add`. Ask the lead: "There's no plan in this folder yet. Want me to start one? What short name should the initiative go by, a few words as you'd say it to a colleague?" On a yes and a name, run `vela new --title "<their words>" --for-lead`. If it asks for their GitHub handle, ask once and run it again with `--handle <handle>`. If it stops, say what it said and don't go on. Whatever documents were in the folder are in the plan's inbox afterward, which is where this skill reads them from. Then run `session start` again, and carry on.

**Reader copy:** `session start` writes the record in the folder and runs no git. Also run `vela freshness --for-lead` and say whether a newer copy was published. If it fails, say in one plain sentence that you couldn't check, and go on.

## 2. Find open sessions

When the lead must choose, `session start` changes nothing and exits 3 with the choices: open sessions, uncommitted work that bringing `main` in would overwrite, or the initiative's name. Ask them one at a time, then run it again with the answer. An open session can be resumed (`--resume <id>`), closed now with `/vela:close`, or left open while another starts (`--new`). Never close a session the user hasn't asked to close. On resume, say in one line where you stopped and carry on from the last capture; a grill carries on from the first `open` item in the record's `## Agenda`.

## 3. Bring in review comments

Run `vela session brief --for-lead`. Offer each review comment it lists as a capture, one at a time, with the commenter as origin and the comment quoted word for word (`--json` holds them). The lead keeps or skips each. If it couldn't check review comments, say so in one plain sentence and go on.

## 4. Offer the overdue unknowns and the next step

For each overdue unknown the brief names, ask the user whether they know the answer now, and how, as `MODES.md` says under "Unknowns". If they don't, offer research Claude does now with a source. Never draft an ask for the user to send, and never offer to. If the user hasn't said what this session is for, offer the brief's next step first, as a suggestion, never a decision.

## 5. Open the record

Tell the lead the session's name in half a sentence ("calling this one desk-helper-start"); change it only if they object. The record's title uses the display name in `MODES.md`: Dump & Diverge, Discover, Shape, Boundary, Allocate, Releases, Grill, Requirements, Epics, Challenge or Answer. A second mode joins the same record's `modes`; it never opens a second record.

Say in one sentence how much there is and how far you expect to get: "Six capabilities, two or three requirements each; we'll do two or three today." At about two thirds of that, say so and ask whether to push on or stop and close.

**Name the initiative, once.** When `session start` asks "What short name should this initiative go by? A few words, as you would say it to a colleague.", ask the lead, then run it again with `--title "<their words>"` and never ask again. If they decline, use `--unnamed` and say once the dashboard reads "New initiative" until they give one. **Reader copy:** the owner names the initiative.

## Answer a challenge

When the user names a challenge to answer, by its PR number or the challenged ID, read `${CLAUDE_PLUGIN_ROOT}/references/ANSWER-A-CHALLENGE.md`. The answer is made on the challenge's own branch, so the challenge and its answer land in one PR.

## Closing a session

Close is a skill you may start, and only on the lead's word: any plain way of saying they're done ("close", "we're done", "that's enough", "let's wrap up"), or a request to move to another mode ("now do requirements for the third capability"), because the open session has to close before another opens.

- **They said close, or something equal to it.** That is the yes. Say in one line what will happen ("I'll file your notes, write the pages and send the branch for review"), and run the `close` skill in this conversation.
- **They only sounded finished** ("I think that's it"). Ask once, "Shall I close this out now?", and wait.
- **Never start close** because the work looks complete, a turn limit is near, or a gate stopped you. The lead decides when the session ends.
- **One confirmation stays, before anything leaves the machine.** Before close pushes the branch and opens a pull request, close says what will be sent and waits for a yes (close, section 7). That yes, given after close says what goes, is the only one that sends. Typing `/vela:close`, saying "close", or saying "push" before then is consent to file, not to send company material.
- **A switch.** After closing for a switch, say the one line the lead types next, by name ("Type `/vela:requirements booking changes`"). Modes start on the lead's word, not yours.
- **If close can't be started from where you are,** say only: "Type `/vela:close` and I'll take it from there."

## Captures during the session

Capture each point with `vela record add --origin <who> --tag <tag> "<their words>"`; it numbers them. Leave the mark off until close, except in the modes that mark at once with `--mark`: a grill marks the deciding capture `→ keep: [[<page>#<heading>|<ID>]] (decided)` when it writes the item decided; a Discover marks each fact it writes `(fact)`; Boundary, Requirements, Allocate and Releases mark each line they write `(assumption)`. Close leaves a mark already written alone.

- A person's words are quoted verbatim, with their name, role or handle as the origin. `vela record add` checks them against what the person typed here and stops (exit 3) on words they didn't type: quote them, or record your own sentence with `--origin claude`. Where nothing can check (no hooks), the line is marked unverified and the lead is asked to confirm it by name before it counts (`vela record confirm <number>` after their yes).
- Claude's own idea has origin `claude`, and close parks it by default.
- When Claude restates what someone said, or the user accepts Claude's recommended answer, the origin is `claude, from <name>`. Close lists those lines under "promoted on a nod".

After about every ten captures, run `vela close stage --checkpoint`: it stages the record and the pages you changed by exact path, never `git add -A`, and commits. In a reader copy the file on disk is the resume point.
