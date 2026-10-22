---
title: Working with Claude
lede: Claude runs the sessions. The reasoning behind how it behaves is the reasoning behind everything else here: put commitments where they can be seen and checked, and don't rely on good behavior.
---

## A session, from start to pull request

Each session is one conversation with one job, on its own branch. Step through one.

::: steps session | One session

::: step Start
Claude checks the repo is clean, pulls main, lists overdue questions, and suggests a next step from `vela next`. It's a suggestion and never a decision.
::: end step

::: step One question, with a view
Claude asks one question at a time and recommends an answer: "I'd write it down as a question for Legal, due the sixth, unless you already know. Fine?" A bare question makes the lead do the thinking and the typing.
::: end step

::: step Capture
What's said is saved as a numbered line in the session record, with who said it. A person's words are quoted word for word, and Claude's own ideas are labeled as Claude's.
::: end step

::: step Read back, then a yes
Before anything is written, Claude reads back what it would write and waits for an explicit yes to that line. "Looks fine" doesn't count. Readbacks go in groups of about five, and a yes to a group counts for the lines in it.
::: end step

::: step Review checkpoint
At set points, five reviewers each read only the written pages, in a fresh context, one area each: money, data, partners, regulation, operations. They find what someone joining cold would ask. `vela findings merge` drops any finding whose quote isn't on the page it cites. An area that didn't run says "did not run," never "checked, none." The lead sees at most three findings at a time.
::: end step

::: step Close
Close sorts each capture (keep, park or drop), writes the pages in the house voice, has a fresh reader review them, checks the plan, and prepares the pull request. Claude never starts it unprompted: "close" or "we're done" is the word.
::: end step

::: step One more yes before sending
Sending can't be undone from the lead's side. "A bare 'close' is consent to file, not to send."
::: end step

::: end steps

::: fold Where this is stated and enforced
Stated in [START.md][start], [MODES.md][modes], [REVIEW.md][review] and [the close skill][s-close]. Enforced by the commands the skills call (`vela session`, `vela record`, `vela close`, `vela findings merge`). Pinned by [`test_close_stage.py`][t-close_stage], [`test_close_pr.py`][t-close_pr], [`test_findings.py`][t-findings], [`test_reviewers.py`][t-reviewers].
:::

## In the person's own words

Captures are why a reader can tell later whose idea was whose. A restatement the person accepts is labeled "claude, from" them, and close lists those as "promoted on a nod."

::: fold A real slice of the demo plan's first dump
```
- [thought] (solution lead) The staff survey showed 71 percent missed a follow-up they owed in the past month—so that's the real pain we'd be solving. → keep: [[01-goals#Goals|goals]] (inkling) ^c10
- [unknown] (solution lead) HR should have it. I quoted that 71 percent from memory, not from reading the actual report. → keep: [[11-unknowns-and-risks#UNK-057 Origin of the 71 percent figure|UNK-057]] (open) ^c15
```
The first is the lead's belief, kept at `inkling`. The second turns a belief the lead admitted was from memory into an open question.
:::

::: fold Where this is stated and enforced
Stated in [START.md][start] and [the close skill][s-close]. Enforced by `vela record add`, which checks a person's words against what they typed where hooks run, and marks the line unverified where they don't. Pinned by [`test_record_add.py`][t-record_add] and [`test_said.py`][t-said].
:::

## What Claude is never allowed to do

Written into the sessions, enforced by commands where a command can, and checked by tests. Click one to see what holds it.

::: deck never | What Claude never does

::: card invent | Invents a source | Where would a fact come from? | rule | Never
A fact needs a registered source, and Claude's general knowledge is never one. `vela apply` won't write a fact from a plan or an unregistered source.
::: end card

::: card decide | Decides without a grill | Who said yes? | rule | Never
`vela decide` re-runs the check that holds a decision up, and E303 and E317 report a decision with no grill. Requirements, shape, boundary, allocate and releases sessions cannot write `decided`.
::: end card

::: card byhand | Writes states by hand | What if a command can't do it? | rule | Never
The skills say "when a command can't express what the lead wants, say so and stop; never fall back to writing the page by hand." A hook denies a hand-moved state and an edit inside a generated block.
::: end card

::: card copy | Copies document text into the plan | Whose words are these? | rule | Never
Discover and import summarize. Contract and legal terms, numbers and direct quotes are kept word for word, with the source linked, and only on the lead's answer.
::: end card

::: card draft | Drafts a message for you to send | Who does the asking? | rule | Never
An unknown has an owner who does the asking. Claude may offer research it can do now, with a source, and never offers to write the email.
::: end card

::: card claimed | Claims a command ran that didn't | Did it really? | rule | Never
"Never report a step as done when it failed." A command line that says "Something went wrong on my side" is Claude's to fix, never to pass on as-is.
::: end card

::: card noyes | Writes a line nobody said yes to | Was that a yes? | rule | Never
A line is written after a yes to that line. "Looks fine" doesn't count.
::: end card

::: end deck

Two limits. Hooks run only where Claude Code runs them (`/vela:where` tells you), and when they don't, close checks everything itself. And these are defaults: the lead can override any, and it gets recorded.

::: fold Where this is stated and enforced
Stated in [MODES.md][modes] (the must-not column), [START.md][start] and each skill's "Never" list. Enforced by the commands on the cards and the hooks that deny hand-moved states and edits inside generated blocks ([hooks.json][hooks]). Pinned by [`test_hooks.py`][t-hooks], [`test_guard.py`][t-guard], [`test_apply_marks.py`][t-apply_marks].
:::

## Pages read like a colleague across a desk

A plan is read by people who weren't in the sessions: a new team lead, an executive, a lawyer with ten minutes. Pages that sound like meeting minutes lose them. So the voice is part of the method: a senior colleague explaining the plan to someone who wasn't there.

- **Short sentences, one point each,** cause before consequence (median 10 to 16 words, grade 8.5 at most).
- **Say a point's state with its verb, once.** "We're assuming the first release is a pilot."
- **Never sound surer than the record.** A number or date needs a source, or the page says "no figure given yet."
- **For anything open, say who settles it and by when.**
- **Plain words, never vela's own.** "Holds up," not "gates." "A session to test it," not "a grill."

::: fold The demo plan's goals page in this voice
> We're assuming the first release is a pilot for the 60 people on Sam Hadley's team, and that it succeeds if they miss fewer follow-ups they owe after client calls. That isn't decided. It holds only if Legal says clients can opt in and a call summary isn't a client record, and a grill will test it once Legal answers.
:::

::: fold Drafted from examples, and the lead's own voice wins
Rules alone drift, so pages are drafted from examples (`vela voice examples`). The public seed examples hold until the lead adds two of their own for a page type. After that the lead's examples win, and `voice/VOICE.md`, in the lead's own words, wins over everything. The lead answers for the plan; if the pages don't sound like them, they won't trust or fix them.
:::

::: fold What a rewrite is never allowed to lose
A smoother sentence is where facts get lost. `vela voicecheck <before> <after>` fails if an ID, number, date, link, table cell or negation was lost, added or moved, and close then keeps the earlier draft. Negatives matter most: "the agent doesn't send anything off the laptop" turned into a positive claim says something else. Case tables, acceptance criteria, decision lines and a person's captured words are never restyled.
:::

::: fold Names, not codes, for the lead
In conversation Claude says "the calendar entries" and "the pilot date is a plan, not a fact yet," not `CON-003` or a check code. If the lead asks for an ID, Claude gives it. Spelling and dates are American ("October 14, 2026").
:::

::: fold Where this is stated and enforced
Stated in [the house-voice skill][hv], [voice/DEFAULT.md][dvoice], [CONVERSATION-VOICE.md][cvoice] and [Voice examples][c-voiceex]. Enforced by `vela voicecheck` ([voicecheck.py][voicecheck-py]), `vela prose replace`, the `--for-lead` output ([say.py][say-py]) and W372. Pinned by [`test_voice.py`][t-voice], [`test_voicecheck.py`][t-voicecheck], [`test_say.py`][t-say], [`test_spelling.py`][t-spelling]. The voice and its target numbers are vela's own design choices, not outside research.
:::

## Not overloading people

People hold only a handful of things in mind at once. The format says "about four to seven" and cites Cowan [1] and Miller [2]. A tool that asks a lead to judge twenty things in one reply gets "ok" to all of them, and "ok" is not a decision. This site follows the same rule.

- **Answer first, then about four things,** each with a recommendation. A longer list is grouped or offered ("six more, want them?").
- **Commands stop at about four lines** and end with a count. "Three more, want them?" runs the command again with `--more`.
- **Openings count and point.** "28 questions are open. Five hold up the first release; the most urgent is who owns the dock repair contract, due October 23." Long lists group by what they hold up, about seven to a group.

The research supports the limit on how much people hold, not this particular design; how vela applies it is its own choice.

::: fold Where this is stated and enforced
Stated in [Pages][c-pages] ("A page fits in a head"), [CONVERSATION-VOICE.md][cvoice] and [START.md][start]. Enforced by `vela check --for-lead` ([say.py][say-py]) and the reading-load warnings. Pinned by [`test_say.py`][t-say] and [`test_readload.py`][t-readload].
:::

## The dashboard, for finding things under pressure

The dashboard is the surface to present from in a live call, when someone asks how the app talks to the billing service. It is a single offline page: a search box, a flow picker that plays any flow step by step, and a right-hand panel that every diagram node opens, by click or keyboard. The test suite fails if one opens empty.

We haven't measured how many clicks any answer takes, so we claim no number. The aim is a short walk from a topic to its flow, with pictures in place of walls of text, following Shneiderman's "overview first, zoom and filter, then details on demand" [6]. `vela view` is the other surface: a document you send, "kept apart on purpose."

::: fold Where this is stated and enforced
Stated in the dashboard section of the [README][readme] and [Progress and next step][c-progress]. Enforced and pinned by [`test_explorer_browser.py`][t-explorer_browser] and [`test_explorer_needs.py`][t-explorer_needs].
:::
