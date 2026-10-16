---
name: discover
description: Register documents and code as sources, read them, show "here's what I think exists" for correction, and write cited facts. Use when nobody is sure what exists today.
argument-hint: "[area, app or question]"
disable-model-invocation: true
---

# Discover

Find out what exists before anyone designs anything. Every fact this session writes cites a source in `sources.md`.

Every `vela` below is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela`. Relay its `--for-lead` lines; reason over its `--json`. When a command can't express what the lead wants, say so and stop. Name sources by title when you talk ("the 2025 booking spec") and things by name; an ID only where the lead must act on one.

1. Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md` with mode `discover`, including its step that asks once for the initiative's short name. Read the Discover row of `${CLAUDE_PLUGIN_ROOT}/references/MODES.md`.
2. List `.inbox/` and `sources.md`. Grep earlier session records for `to fetch:` captures and ask whether each document has arrived; one that has not stays an unknown.
3. Ask the user to rank the documents and cut what is not worth reading. Before they cut one, say which others cover the same area: a clash only shows when both are read. Propose a `Kind` for each source kept, and ask in plain words whether it describes what runs today (`exists`) or what's planned (`intends`: a plan, deck or roadmap). A local clone of a code repository is `Kind: repo`. Every kept source needs a confirmed `Kind` before you go on; if the user overrides that, say once that an unconfirmed `Kind` can turn a plan into a fact, use yours, and record the override as `START.md` says. Register each with `vela add source --title "<title>" --owner <handle> --date <YYYY-MM-DD> --kind <kind> --location "<where>" --for-lead`. Location is `local only` for a file only in `.inbox/`; a repo's is `<url>@<sha>`, from `git -C <clone> remote get-url origin` and `git -C <clone> rev-parse HEAD` (pass the URL as git prints it: the command takes out any credential and says so). Read only the top-ranked sources.
4. Show "Here's what I think exists" as a numbered list, in groups of about five. Label every line with its source by title, and say whether it describes what runs today or a plan (the file holds `SRC-nn` and that source's `Kind`). Before writing, say aloud any pair of lines you can see disagreeing: a disagreeing pair becomes one unknown naming both sides (`vela add unknown --name "<name>" --for-lead`), never two facts. Its owner handle is the lead's; who to ask and the ask-by date are proposed and confirmed as `MODES.md` says under "Unknowns", never filled in on your own. Write only the lines the lead said yes to, as `START.md` defines a yes. Silence, or "looks fine" with no yes, does not count: ask once more in different words.

   > 1. Partners get a nightly file of changed bookings (the partner guide, what runs today).
   > 2. Guests can rebook on their phones by Q4 (the 2026 roadmap deck, a plan, so not decided yet).
   > 3. Partners get changes every hour (the ops runbook, what runs today).
   >
   > Lines 1 and 3 disagree; I'd make that one open question. I'd ask the partnerships team, by 1 March, since the pilot's partners sign up then; does that person and date work? Yes to these three?

   Documents rarely say where people pull against each other; the lead knows. From the first group on, when a line or the lead names a person, role or group, make your next question an open one about them, not a yes on your reading: what do they want from this, what would they push back on, who else has a say? ("What would the people who approve refunds resist here?") Ask the yes on the group the turn after. When two answers pull apart, say so in the lead's words and make it one unknown naming each side and who holds it, without picking one.

5. After each correction round, write each confirmed line as a sentence in its page's section (`vela conventions "Pages"`, prose as `house-voice` says): the source linked on the words that rely on it, the wording saying how sure it is ("the agreement summary says…" for a fact, "Partnerships expects…" for an assumption). Contracts, unknowns, parties and stored value keep their fact bullets, each opened by a sentence. Never copy document text into the vault.

   A line's state comes from its source:
   - A line from an `exists` or `repo` source is a `fact`, with `sources: [SRC-nn]` on the page or `- **Source:** SRC-nn` on a contract.
   - A line from an `intends` source is an `assumption`, however sure it sounds.
   - A line about the future ("will", "planned", "by Q4", "ready in") is an `assumption`, whatever its source's `Kind`.
   - A line the user knows first-hand is a `fact` only once it has its own source row. `first-hand` is not a registered `Kind`: register it as `Kind: exists`, the user's handle as Owner, Location `first-hand: <handle>`.
   - Claude's general knowledge is never a source.

   Each line written also gets a capture line and a `## Changes` row. Capture it with `vela record add --origin "claude, from <name>" --tag thought "<the line>"` (it numbers it). Mark the round's captures at once: a `marks` decision file in `.vela/decisions/<session>/` (fields from `vela apply --schema marks`; a fact names its `source`), then `vela apply <file> --for-lead`, so each reads `→ keep: [[<page>#<heading>|<ID>]] (fact)`. Apply won't write a fact from a plan or an unregistered source: say so, then write an assumption or confirm the `Kind` with the lead. Commit a checkpoint with `vela close stage --checkpoint --for-lead`.

   Type the subject: a line naming an outside organization, or value held for customers (points, credits, balances, deposits), goes through `vela add subject --subject-type PTY` (with `--relationship` and `--agreements`) or `--subject-type SV` (with `--holder` and `--owner`), plus `--name` and `--capture`. When it stops on a missing fact, ask the lead for it. The catalog's questions fire only on typed subjects.
6. For each open unknown a confirmed line answers, show the answer and its source and ask for a yes; then capture it and file a `resolve` decision file (`vela apply --schema resolve`) with `vela apply <file> --for-lead`. Say which unknowns stay open. Then run `vela questions --open --json` and do the same for its copies and reviewer questions: on a yes, capture the answer starting with the copy or `R-` ID, such as `Q-DAT-02@APP-coach: the privacy review says…`, so close writes its `answered` row with that source. A concern cell the answer settles, `unchanged` or `n/a`, is written now as `vela conventions "Concern cells and waivers"` says.
7. Run the review checkpoint in `${CLAUDE_PLUGIN_ROOT}/references/REVIEW.md`, with the checkpoint "after the read-back" (the "Here's what I think exists" step, once its lines are written) and the confirmed lines as its focus. Show the digest as REVIEW says and capture what they take. On a yes to an existence question ("does anyone hold value on customers' behalf?"), type the subject as step 5 says, run `vela questions --subject <ID>`, and say: "Noted: the plan holds money or points on customers' behalf. Because of that, these questions now need answers:", then each by name.
8. Finish with a short Dump & Diverge: ask what the documents leave out and what a careful reader would still ask, and capture the answers. Add `dump` to the record's `modes`.
9. When the lead says they are done, close as `${CLAUDE_PLUGIN_ROOT}/references/START.md` says under "Closing a session".
