# Review checkpoints

A review checkpoint finds the questions the plan owes and nobody has asked. Code works out what the catalog owes (`vela questions`). One focused reviewer per focus area, each in a fresh context, reads only the written pages and finds what code can't. `vela findings merge` combines what they return. The lead never sees the reviewers, only one short digest. The skill that sends you here names the checkpoint and its focus.

## 1 and 2. Prepare the checkpoint

Make sure everything said so far is in the session record as captures: a reviewer sees only what is written. Then run `vela reviewers prepare --checkpoint "<the checkpoint and its focus>" --focus <the pages its focus touches>`. Give only the pages the focus touches; every reviewer reads them, and each page is paid for again on each of its turns. It numbers the checkpoint from the record, commits the record and the changed pages, writes one packet per area to review into `.vela/review/<n>/<AREA>.md` with that area's owed questions beside it, clears the findings folder, lists each area it skipped with the reason, and prints the heading and the merge command for later. In a reader copy it commits nothing and says so. While the reviewers run, say the one line `--for-lead` gives ("Checking this against five angles, about a minute.", naming any angle left out) and nothing more until the digest is ready.

## 3. One reviewer per area

Run `git status --porcelain` and keep its output as the baseline (in a reader copy, `shasum` each page and the record instead).

Dispatch the `vela:area-reviewer` subagent with the Agent tool, once per packet, in one message so they run side by side: all five in one message when no area is skipped. Set the Agent tool's `model` to `sonnet` on every dispatch, as the agent's own `model: sonnet` says. A focused read-only check against a short list of pages doesn't need the session's model, and five at once cost five times as much. Give each one only its packet's text, word for word. Never send a placeholder, a `<...>` template or another area's packet.

Give no conversation, no summary of what the lead said, and no other area's questions. If the Agent tool lists no `vela:area-reviewer`, dispatch a general-purpose subagent instead, with `model` set to `sonnet` as well, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md` after the frontmatter as its instructions, then the packet, then this: you must not change any file. If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead. Never review the pages yourself in this conversation.

Don't report each reviewer returning, a failed command, a retry or a commit. Save each reply exactly as it came back, with the Write tool, to the findings path its packet names. If a reviewer errored, or couldn't be dispatched, write `{"area": "<AREA>", "error": "<what happened>"}` instead. Never write an empty findings list for a reviewer that did not finish: that would read as "checked, none".

Then run `git status --porcelain` again and compare it with the baseline. If a tracked file changed that you didn't change, a reviewer changed it: stop and tell the user, in plain words, which page changed.

## 4. Merge

Run the merge command `reviewers prepare` printed: `vela findings merge .vela/findings/<session id>/<n> --changed <paths>`, with `--areas` and `--skipped` when it named them. A new question about a page this session didn't change is dropped: it was owed when that page was written, and raising it again every session is what makes a digest grow faster than a lead can answer it. The merge keeps the union, folds the same question from several areas into one finding, and drops every finding whose quote isn't on the page it cites. A finding may address an owed copy, an open reviewer question by its `R-` id, or `new`. Exit 1 means an area didn't run or a finding was dropped, and the output says which. Exit 2 means the tool failed: record the checkpoint with every area as `did not run (merge failed: <error>)` and no table rows.

Write the result into the session record, under `## Reviews` after `## Captures`, with the heading `reviewers prepare` printed. Add `## Reviews` if the record has none.

```
### <n>. <checkpoint>, <today>

- **Coverage:** <the merge's coverage line, after "coverage: ", word for word>
- **Dropped:** <each dropped finding, its area and the reason, or none>
- **Merged:** <each finding the merge folded into another, as `[<area>] into F<n>.<m>: <its question>`, or none>

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F<n>.1 | FIN | high | Q-FIN-03@SV-01 | <the question> | "<the quote>" in [[<page file name without .md>]] |
| F<n>.2 | DAT, PTN, REG | high | new | <the question> | "<the quote>" in [[<page file name without .md>]] |
```

Number the kept findings `F<n>.1`, `F<n>.2` and so on, in the merge's order. The Area cell lists every area the merge gives the finding, first one first. The **Merged** line takes each entry under `duplicates:` whose question differs from the finding it joined, so every area's own words stay on the record. Escape a `|` inside a cell as `\|`. In the quote cell, replace each inner straight `"` with `”`, as the merge does when it checks the quote.

Give the coverage in one sentence ("All five angles found something", or "Four angles ran; the regulation angle didn't, because its reviewer failed"). An area that did not run is never reported as clean, and a skipped area is never reported as checked: name it in that sentence and offer to run it. The per-area detail goes in the record and the pull request body, not the conversation.

**Re-running areas.** Running some areas again, or one a checkpoint skipped, is a new checkpoint: `vela reviewers prepare --checkpoint "<checkpoint>" --focus <pages> --rerun 1 --areas FIN,REG` re-runs two areas of checkpoint 1. Its findings are numbered from the next checkpoint's number, so earlier finding IDs never change.

## 5. The digest

Run `vela questions --digest --session <session id> --for-lead`. It gives the next three lines for this session's lead, high and blocking first, never one already shown or taken this session, and writes what it showed into the record. Nothing is dropped: every line stays in `vela questions --open` and in the ledger.

What the lead is shown is small, so they can answer it.

- **Once per session, at a pause.** A mode may run its checkpoint more than once; each result goes in `## Reviews`. But the lead sees one digest per session, at the natural pause after a topic or at the end, never in the middle of their own line of thought. Shape is the exception: its checkpoint comes before the options, and its findings go with the options as "what must be true" (the Shape skill says how); what's left goes in the one digest.
- **At most three questions.** Say each as one plain sentence with one question mark, as a colleague would across a desk, naming the thing and the person who would know, with your recommended answer. No copy ID, finding ID, area code, severity or command in what the lead hears; those go in the record.
- **Never twice, never ruled out.** The command keeps count, so a question shown once this session isn't shown again, and one the lead answered or ruled out isn't asked.
- **The rest, in one line, by what they're about.** "Six more are about cost and four about who sees client data; want the next three?" On "more", run it again.

For example, instead of "Q-PTN-02@PTY-01 and @PTY-03: does the agreement permit transfer of data to a new owner or user? One answer for all?", say:

> Legal hasn't been asked whether a digest of a client call counts as a client record. My suggestion is to write it down as a question for legal, due 6 November, unless you already know. Fine?
>
> Eleven more are written down, six of them about cost. Want the next three?

A turn of 50 questions is a dump, not an interview, and the lead answers none of it well. Never paste a reviewer's reply, or the findings JSON, into the conversation: the digest is the only thing the lead reads. When the lead asks for everything on one subject, read `vela questions --open --digest --all` and say those lines three at a time, the same way.

## 6. Record what the lead does

The lead sets the pace. What they take, capture as `START.md` says, starting the words with the copy ID or the finding ID, for example `- [thought] (Head of Finance) Q-FIN-03@SV-01: finance carries the balance today ^c14`. A yes to an existence question, one whose entry `creates` a party or stored value, also ends with the subject note, `type at close: PTY` or `type at close: SV`, as `dump/SKILL.md` shows, so close types the subject and writes the row in one go. A ruling-out is a capture with its reason. When the lead says a group of lines all wait on one open unknown, such as "all of these wait on the Platform team, UNK-050", capture it once, naming every ID: `- [thought] (<name>) waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4 ^c21`. Close writes one `unknown` row per ID linking that unknown, so the whole group leaves the digest and comes back when the unknown is resolved. If the group waits on something no unknown asks yet, write that unknown first. A belief the lead states without a source is a capture tagged `thought` that says it is a belief, and close asks whether it is load-bearing.

Write nothing to a page because of a finding, beyond what the mode itself writes. Close writes the ledger rows from these captures and from the `## Reviews` tables, so every copy taken and every finding ends in a row. Whatever the lead doesn't take stays open and visible, in the ledger and in `vela questions`.
