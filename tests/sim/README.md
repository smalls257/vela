# Session simulator

A simulated solution lead runs real multi-turn Claude Code sessions in a scratch vault, once per arm. Each arm
gets the same persona and the same script. Every run leaves transcripts you can read and a scorecard measured
against the lead's hidden brief.

It answers one question. When a lead starts from a vague idea, do the vela skills guide them to figure
things out better than plain Claude Code does?

## Run it

Start with the smoke script. It runs one dump and its close, with low caps, and checks the CLI assumptions the
free tests cannot check (listed under "Not verified" below):

```
python3 tests/sim/run.py coastal-merger --script smoke --model claude-sonnet-5-5 --persona-model claude-haiku-4-5-20251001 --judge-model claude-sonnet-5-5 --budget 10
```

Then the full default script:

```
python3 tests/sim/run.py coastal-merger --model claude-sonnet-5-5 --persona-model claude-haiku-4-5-20251001 --judge-model claude-sonnet-5-5 --budget 80
```

The model IDs are suggestions. Edit them to the IDs you pin. Every model flag and `--budget` is required, and
none has a default.

- `--arms` defaults to `vela,vela-seuss`. `baseline` runs only when you name it, as `--arms vela,baseline`.
- `--script` takes a name in `scripts/` or a path. `default` runs dump → close → discover → close → shape →
  close → discover → close → shape → close → grill → close.
- `--stub` swaps `claude` for the scripted fake in `stub/`. It costs nothing, and it is what the tests use.
- `--out` changes the results folder. The default is `tests/sim/results/`, which git ignores.

To score a finished run again without replaying it, for example after the judge or the keywords change:

```
python3 tests/sim/run.py --rejudge tests/sim/results/<run-id> --judge-model claude-sonnet-5-5 --budget 4
```

It reads each arm's `transcript.jsonl` and `vault/`, and the persona, models and endings from `run.json`. It
rewrites `scorecard.json`, `scorecard.md` and `compare.html`, writes what it cost to `rejudge.json`, and never
writes the transcript, the vault or `run.json`. New raw judge files are numbered after the run's own. It takes no
persona, `--model`, `--persona-model`, `--script` or `--arms`, because the run already fixed them. It exits 0 when
every arm was scored, 2 on a tool failure, such as a transcript with no turns, and 3 when a final vault is under the
script's completeness gate. It reads the script `run.json` names, so the judge reads the same news and outsiders the
run gave the lead.

A run that stopped part-way goes on with `--resume-run`; see "Resume a run" below.

| Arm | Vault | Plugin | Voice |
|---|---|---|---|
| `vela` | `plugin/template/`, plugin copied to `.claude/skills/vela` | `--plugin-dir plugin` | the AOSA public seed |
| `vela-seuss` | the same | `--plugin-dir plugin` | `voices/seuss-style/` in `voice/local/`, public seed retired |
| `baseline` | `plugin/template/` with no `.claude/skills` | none | none: the vault's `CONVENTIONS.md` and `CLAUDE.md` only |

### Exit codes

- 0: every session of every arm ended when the persona wrote `[END]`, and every arm was scored.
- 1: the budget or a turn cap ended at least one session early. Every output is still written. At the cap the
  lead is still asked, so an [END] there ends the session as the lead's; any other reply would never reach the
  assistant, so it is written as a `lead-unsent` driver note, not a lead turn, and the judge never credits it.
- 2: a tool failed. `claude` was missing, its JSON lacked a field, a call errored, the judge's JSON was bad
  twice, or git or the scaffold failed. The run stops at that arm. What was written before the failure stays,
  and `run.json` names the failure. The raw output of every call is in `<arm>/raw/`.
- 3: every session ran and was scored, but the final vault's Completeness (the line `vela status` prints) is under
  the script's `completeness_gate`, so the run does not count. The scorecard's Completeness section names the shares
  that held it back, weakest first. A `--stub` run reports the gate and is never failed by it. 2 outranks 3, and 3
  outranks 1.
- 4: the judge preflight failed, so no session ran.
- 5: `--resume-run` refused: the `--budget` left can't cover one more typical session. Nothing was spent or moved.

A session's `persona:` names the person who speaks in it instead of the lead: a team's senior, or an outsider the
lead brings in (`outsider: true`, such as `heron-dpo`), who answers only what is theirs. Every session persona is
checked before the first call. The judge's invented-facts call reads each outsider's facts, so what an outsider said
in the room is given, not invented.

## Cost

This is a rough estimate. It is not a quote. The driver measures the real spend from each call's
`total_cost_usd`, prints it after every turn, and stops at `--budget`.

The reasoning, for a Sonnet-class assistant model:

- An assistant turn is several API requests, one per tool call, over a context of about 30k to 80k tokens:
  Claude Code's system prompt, the skill, START, CONVENTIONS and the vault pages it read. With prompt
  caching, that is roughly $0.10 to $0.30 a turn. A close turn renders, checks, edits many pages and may
  dispatch the voice reviewer, so it is nearer $0.50 to $1.50.
- The default script allows 118 assistant turns per arm. A run that ends most sessions before the cap might use
  about 80: around 55 ordinary turns and 25 close turns. That is about $10 to $40 an arm.
- Each assistant turn has a persona turn. On a Haiku-class model, over a transcript that grows to about
  40k tokens, that is about $2 to $4 an arm.
- The judge is seven calls an arm, one per category. Each holds the transcript and only what its category needs:
  the inbox for W and the shape, and for K and D a page index plus, per item, the vault passages that hold its
  keywords. No call sends more than `JUDGE_INPUT_CHARS` (300k characters, about 100k tokens); a 69-page vault of
  990k characters once sent whole came back `prompt_too_long`. Whatever is left out (passages, or turns cut
  short) is named under Check these. `python3 tests/sim/run.py --dry-judge <run-dir>` prints every input's size
  and its cuts without calling claude. On the smoke run a call is about 8k to 17k tokens, 60k to 70k an arm, plus
  the thinking each call does: about $0.50 to $1 an arm.

So the default two arms come to about **$25 to $90** on a Sonnet-class model, and several times that on an
Opus-class model. The smoke script comes to about **$3 to $8** for two arms. These rates are assumptions; check
them against current pricing before you trust the range.

The budget is split evenly across the arms. In each arm, 15% is held back for the judge, so sessions stop at
85% of the arm's share. Every call gets `--max-budget-usd` equal to what is left. A call can overshoot its cap
a little before Claude Code stops it.

## What each file shows

Each run gets `results/<date-time>-<persona>/`:

| File | What it shows |
|---|---|
| `compare.html` | The arms side by side: every brief item with yes or no and its evidence, spend, how each session ended, and links to each arm's files. Start here. |
| `run.json` | Models, budget, spend per arm, each session's ending, the setup notes, any failure, the exit code. |
| `<arm>/transcript.html` | The conversation as chat bubbles, with a header per session, tool calls and permission denials collapsed, and the driver's own actions in italics. Everything is escaped and the page has no script. |
| `<arm>/transcript.jsonl` | One line per turn: turn number, session, mode, speaker, text, cost, tool calls (name and a short input), session id. Driver events have no turn number. |
| `<arm>/vault/` | The final scratch vault, with its own git history. `origin.git` beside it is the bare remote its pushes go to. |
| `<arm>/vault-git-log.txt` | `git log --oneline --all --decorate` of the final vault. |
| `<arm>/vault-check.txt` | `vela check` on the final vault, with its exit code. |
| `<arm>/viewer.html` | `vela view` of the final vault. If the vault does not parse, `viewer-error.txt` says why instead. |
| `<arm>/scorecard.json`, `scorecard.md` | The judge's scorecard after the driver checked every citation. |
| `<arm>/tickets/` | Only for a script with a team `breakdown` session. `tickets.csv` in Jira's CSV import shape and a `README.md` on importing it, made by `tools/breakdown_to_tickets.py` from the breakdown the arm wrote, with no model, so each ticket is one story or task of the breakdown. Lines it could not map are listed as problems in that README. |
| `<arm>/raw/` | The raw stdout and stderr of every `claude` call, numbered in order. Read these when a run exits 2. |

## How to read a scorecard

The brief has five kinds of item, each with an ID:

- **U, gaps.** Things the lead never thought about. "Surfaced" means the assistant raised it first. This is the
  heart of the question: a good session finds what the lead does not know to ask.
- **W, wrong beliefs.** "Challenged" means the assistant questioned the belief, or gave a reason or a source
  against it.
- **K, facts.** "Captured" means the fact is written somewhere in the final vault, with the file named.
- **D, decisions.** "Decided" with "yes asked" tells you whether the explicit yes was asked for. A brief can hold
  a decision the lead refuses to make until something outside the room is confirmed, so deciding it is a failure.
- **C, stakeholder conflicts.** "Surfaced" means the assistant named the disagreement as something to resolve,
  rather than picking a side.

The shape of the guidance: the most questions in one assistant turn (counted by the driver, not the judge),
the turns that told rather than asked, decisions made without a yes, invented facts, and whether each session
ended with a clear next step.

The voice rule is counted by the driver, not the judge: the scorecard counts check codes (a W or E and three
digits), raw IDs (`UNK-`, `CAP-`, `CON-`, `EPC-`) and gate names (`GATE-2`, `gate 2`, `--gate`) in the assistant's own
text, which is what the lead reads. Tool output and subagent text are not counted. The voice score is the share of
assistant turns with none, a turn with more than two is listed under Check these, and the shape judge is shown the
count so its view of the guidance agrees with it.

One more scored question, the tracer: does release one name a tracer that runs end to end through every app and
contract it needs, or record why not (`**Tracer:** none, <reason>` or a `**Not in the tracer:**` bullet)? The
judge reads the releases page and quotes the Tracer line; a quote the page does not hold reads as not recorded.
A tracer that skips an app and does not say why scores no.

Beside every verdict the scorecard sets the driver's **keyword hits**: the assistant turns and final vault pages
that hold one of the item's `keywords` from the persona, and for W and U items the lead turns too. A gap the lead
raised first is not one the assistant surfaced. Vault hits leave out `CONVENTIONS.md`, `CLAUDE.md`, `README.md`,
`voice/`, `.inbox/` and any keyword the template's own copy of the page already holds. **Check these**, at the top,
lists every item where the judge and the hits disagree, such as "K4: judge: no; vault mentions <keyword> in
01-goals.md". Neither side is proof. A hit can be a question or a parked idea, and a capture can use other words.
Read the item before you believe either.

The judge makes one call per category, so it reads each item. Every row starts with a `search` note on what it
looked for and where, written before the verdict; a row without one is rejected and asked again once. The judge
gets the hits as hints and is told that a hint is not proof. Judge calls pass `--effort high` and
`alwaysThinkingEnabled`, and the scorecard prints each call's thinking tokens. If every call reports 0, Check
these says so.

Every claim needs a turn number and a quote. The driver checks each one against the transcript: the quote must
appear in that turn, give or take whitespace, quote marks and emphasis. A K claim must name a page of the final vault, so
not the inbox, the conventions or the voice examples. A claim that fails is turned to "no" and listed under "Dropped claims". This is mechanical,
not taste. Read the quoted turns in `transcript.html` before you believe a score.

### Precision

Recall against the brief can rise because a session wrote more. So the scorecard also asks what share of what the
vault holds can be trusted. `precision.py` draws 4 passes of 30 items (seeds 101, 202, 303, 404; pooled 120, reported with a plus-minus, the half-range of the per-seed precisions; `--quick` for one pass, which swings about 15 points) from the final vault (`origin/main`, as the comparison
reads it): a section under an item heading, or on a page with none a paragraph, bullet or table row. The sample is
stratified by page type with a fixed seed, so two runs are sampled the same way and a rerun draws the same items.
Session records (`sessions/`), the team's documents (`docs/`), any text the vault template already holds word
for word, and everything the tool generated rather than the model wrote are left out: handoff pages, an epic's
`- Trace:` and decision-link lines, template and retired template lines, CLI-rendered tables. One judge call (capped at $1.50, thinking on, in the preflight like every other category)
classes each item:

- **backed**: in a source document or the lead's own words (the judge quotes the place), or plainly an open
  question, an assumption or a risk put to the lead rather than a fact (it quotes the item's own framing words), so
  a gap the assistant raised from its own knowledge is not punished;
- **duplicate**: the same fact as another item; the driver shows each item's two nearest neighbours by shared words;
- **padding**: no information, such as a placeholder row or a restated heading;
- **unsupported**: stated as fact, given by nobody.

A citation the driver can't find (a quote not in the document, the lead turn or the item, a neighbour not listed)
turns the item unsupported and is listed under `dropped`. Precision is 1 - (unsupported + padding) / sampled; the
duplicate rate is shown beside it. A full run and `--rejudge` write `<arm>/precision.json`; for a run judged before
the pass existed:

```
python3 tests/sim/precision.py tests/sim/results/<run-id> --judge-model claude-sonnet-5-5 --budget 2 [--arm vela]
```

It sends the preflight (one tiny call) first and exits 4 if that fails, 2 on a tool failure. About $0.20 a run on
Sonnet 5.5 for a 26-session heron-desk vault. `--stub` fakes the judge for free.

## Compare two runs

    python3 tests/sim/compare_runs.py results/<baseline run> results/<later run> [--arm vela] [--json out.json]
    python3 tests/sim/compare_runs.py --baseline <run> --baseline-checkout <checkout> --midpoint <run> --midpoint-checkout <checkout>

The later run against the baseline, for one arm (`--arm`, default `vela`). It is the one comparison tool; it
replaced `compare.py`. It replays nothing and costs nothing, and it never writes into a run folder or a checkout.
Markdown goes to stdout, with the verdict first: **GO** (exit 0), **ADJUST** (1), **STOP** (3), or **UNSCORED** (4)
when a run has no scorecard; 2 when a run folder or its arm can't be found.

**The verdict comes from recall and precision, and nothing else.** Recall is the share of the persona key the run
reached, per kind (K facts captured, U gaps surfaced, W wrong beliefs challenged, C conflicts surfaced, D decisions
decided, each "n of N" and a share; C and D have their own rows marked "weak spot") and pooled over all of them.
Precision is the precision pass above, read from `<arm>/precision.json`. The rule:

- **STOP** when pooled recall falls more than 5 points and precision more than 10 at once, or recall falls more than
  15, or precision more than 20.
- **ADJUST** when pooled recall falls more than 5 points (about 3 of 60 key items), or precision more than 10 (3 of
  30 sampled items), or any one kind loses 2 or more items and more than 20 points of its share, which a steady pool
  can hide.
- **GO** otherwise. Recall up with precision down is never a GO: more written, less of it true, is the Paper Tiger
  this verdict exists to catch, and the "why" says so.

Without precision the verdict reads recall alone and is provisional. It is also provisional, with reasons, when a
run isn't finished, its vault was read from the working tree, the key had a different size in the two runs (news
arrives at different points), or the runs didn't run the same sessions.

**Everything else is a diagnostic.** Items written, captures, ledger rows, words per item, pages, Completeness, the
prose judge's lists, voice, close steps, consent and IDs sit under "Diagnostics (never set the verdict)", each with
its direction ("up 23%"), to read the transcripts by. A count going up is not the run getting better. The
reliability figures that used to move the verdict (pushes without consent, skipped close steps, decided without a
yes, invented facts, reused IDs) are listed beside the verdict as "Guardrails that got worse", and still never set it.

**A holdout is sealed.** When either run's persona says `split: holdout`, or has no split, or no file, the report
prints scores only: no key item ID, in the Markdown or the JSON (the per-item scorecard rows and the precision items
are taken out). `--reveal` prints them; never pass it while iterating on the skills.

Each run is measured by one ruler: the same parser reads both transcripts and both vaults. Completeness, `check` and
`capture` are printed by each run's own checkout (`--baseline-checkout`, `--midpoint-checkout`; by default the
checkout the run folder sits in, or this repo, and the notes say which). It reads:

- **Sessions and spend** from `run.json` and the transcript: how each session ended, turns per mode, spend split
  between assistant, lead and judge.
- **Recall and precision**: as above. For a dev persona, the key items that were yes in one run only are listed
  under the recall table.
- **The scorecard's other figures** (diagnostics): the prose judge's lists, the voice score, the tracer.
- **Codes, IDs and tool names in lead-facing turns**: each assistant turn's own text, by kind, with the worst turns
  listed. The patterns name both the old tool name and vela, so an old run is counted as it was recorded.
- **Skipped close steps**: each close session's full tool inputs, read from `raw/NNN-assistant.txt` (the
  transcript cuts them at 200 characters), checked for each step the run's own close skill names. A step missing
  from a session cut by a cap or the budget is counted apart. The tool is recognized by name, through a variable
  (`$P render`), or through a shell function or alias the run defined (`v(){ python3 …/vela "$@"; }; v render`).
  A command whose output says it never started (zsh's `no such file or directory: python3 …` for an unsplit
  variable, `command not found`, exit 127) or a call the sandbox denied counts for nothing. `vela close finish`
  counts as the gate, render, check, the close commit and the explorer rebuild: it refuses unless the gate passes.
- **Consent before push**: a push is a `git push` that went (not denied, not rejected) or a `vela close push
  --consent ^cN` that sent. A `close push` with no `--consent` is a notice: it asks and sends nothing, and is counted
  on its own line. A `git push` needs a lead turn earlier in the session that asked for it, or a yes to an
  assistant question about it. A `close push --consent ^cN` needs the words `record add` captured as ^cN in a lead
  turn after the session's last notice and before the send. The ones it can't match are listed by turn with why.
- **Wrong or reused IDs**: check's reuse codes, IDs that carried two names in the vault's history, and IDs said to
  the lead that the vault never had. A question-ledger ID is read whole, so the tail of `R-DAT-02` or
  `Q-DAT-01@INI-001` is not an ID of its own. Vela's own families (UNK, CAP, CON, EPC, FLO, SLC, ADR, APP, PTY, SV,
  EVT, ENT, R) need a heading, a page id or a table row on some branch; any other family (ledger rows, sources,
  goals, the team's D-001 or OQ-011) counts as known when the vault's history holds that exact ID, and is listed
  apart.
- **The final vault**: pages, items by kind and state, unknowns with an Ask line, contracts with case tables, flows
  drawn, slices, captures, ledger rows, and words of detail per page type and per item. It is read from the arm's
  `origin/main`, in a temporary clone, because that is what the next session and the team pull; the branch the
  last session left checked out can be far behind (the 2026-10-14 mid-point ended 21 commits behind main). The
  report names the ref it scored and how the working tree stood against it. A run with no origin to read is scored
  from its working tree, and the verdict is marked provisional for it. Completeness, `check` and `capture` run on
  the same clone, so the run folder is never written to.
- **Team documents**, apart: the pages under `docs/` (the design, its decision records, the work breakdown), from
  origin/main and from any origin branch not merged into it, each listed with the ref it came from. Their items
  (the design's OQ, the breakdown's S) are not in "Items written" or "Items by kind", and their rows never move
  the verdict: the team's sessions run after the plan's and can be blocked by it, so a drop there is a lost team
  tail to read in the transcript, not the plan thinning.

Missing data is never read as zero: a figure it couldn't read is `missing (<why>)`, and its delta is `n/a`.

Runs recorded before the tool was renamed to vela keep their old arm folder (`planner`). `LEGACY_NAMES` in
`compare_runs.py` is the one place those names live: `--arm vela` finds the old folder, and the report says it paired
them. A copy of the script runs outside the repo too (`/tmp/compare/compare_runs.py`): it needs nothing but Python
and git.

## Resume a run

A run that was killed, crashed, or stopped on its budget or a turn cap goes on from where it stopped, instead of
paying for every session again:

```
python3 tests/sim/run.py --resume-run tests/sim/results/<run-id> --budget 60
```

- **Where each arm picks up.** At its first session with no `session-end` in `transcript.jsonl`. A session skipped
  for budget has none, so it is played. A session the run stopped inside goes on from its last turn, in the same
  claude session (`--resume <id>`): if the lead spoke last, the assistant call that should have answered never
  returned, so that message is sent again; if the assistant spoke last, the lead answers next. A `session-continued`
  line in the transcript says which, and what the vault had uncommitted. An ended session is never played again.
- **What it reuses.** The arm's own vault, origin, gh stub, team repos and news. The lead gets the news in the
  order the transcript says it arrived (each news line now carries the news itself). An arm that never started a
  session is built anew, and any folder its setup left is renamed `<arm>.set-aside-<time>`. An arm that ended
  every session and has a scorecard is not judged again: only its pages are written.
- **What it takes.** Only the run folder and `--budget`. The persona, models, script, arms and `--stub` come from
  `run.json`. A script edited since the run so that a started session's mode moved is refused. A paid resume sends
  the judge preflight again, since the judge prompts may have changed.
- **Money.** `--budget` is the new total cap for the whole run, spend so far included; left out, it is `run.json`'s
  `budget_usd`. Spend so far is `per_arm` in `run.json`, plus the turns of a session it had not counted yet, read
  from the transcript. When `run.json` has no `per_arm` (a crash before the summary, as on 2026-10-14) it is rebuilt
  from the transcript and the scorecard's judge spend, and `run.json`'s `notes` say so. Before anything is spent,
  the resume checks each arm with sessions left has room for one session at this run's average session cost (and,
  once any arm of the run has been judged, for a judging after it), and otherwise exits 5 with the `--budget` that
  would do. A run with no ended session yet, or no judged arm, has nothing to check against, and says so.
- **What it writes.** It appends to each transcript, numbers new raw files after the highest one, and adds to
  `run.json` a `resumes` entry naming where each arm went on from. Then it scores and finishes as a new run does,
  with the same exit codes.

Two things every run now does make this safe. `run.json`'s `per_arm` is written after every session (replaced
whole, so a kill mid-write leaves the last good copy): `spent_usd` holds the ended sessions and judging,
`through_session` the last session it counts, and `open_session_usd` what a session under way had cost. And a
failure writing an arm's pages (transcript.html, the viewer, `vela check`) is recorded as `finish_failure` and the
run exits 2, but the summary is still written; that failure is what lost the 2026-10-14 baseline's `per_arm`.

Not covered: a call cut off mid-way is not in the transcript, so its cost is missing from a rebuilt spend; and a
session the run stopped inside goes on in a claude session that may hold half a turn.

## Long runs: launch them detached

A shell command started in the background by a tool (Claude Code's included) is killed after 2 hours, and a full run
takes longer. Launch it detached, and keep the Mac awake:

```
nohup caffeinate -dimsu python3 tests/sim/run.py <persona> --script <script> ... > results/<name>.log 2>&1 &
```

Then follow the log with `tail -f`.

To see whether a detached run has hung, run `python3 tools/stall_check.py` (free, read-only). It lists each sim or
probe run folder that isn't finished (no `"exit"` in run.json, no probe.json) and has had no write for 25 minutes
(`--minutes`) with no `run.py` or `probe.py` process working in its checkout, across this checkout and every agent
worktree. Exit 1 means at least one is stalled; exit 2 means it couldn't read the process list, which it never takes
as "nothing is running".

## What the driver does that a person would do

- **It merges each closed session's PR.** The arm's `gh` is a stub: `gh pr create` records the PR (number, head,
  base) in `origin.git/sim-prs.jsonl` and prints a URL; `gh pr list` (`--head`, `--state`, `--search`, `--json`),
  `gh pr view` (a number, a branch or the current branch) and `gh pr comment` read and add to that record, so "open
  the PR" can be seen in a run; every other `gh` command fails. A merge below marks the PR `MERGED`. After every close
  session, the driver merges each `session/*` branch whose records are all closed into `main` on the bare origin,
  as an approving reviewer would, and logs `merged PR <n> as the reviewer` in the run log and the transcript. Without
  this, the next session's START would pull a `main` without the last session's work, and a team session
  (tech-design-grill in vault mode) would not find `handed_off` on `origin/main`. A branch with an open record, or
  one that conflicts, is not merged, and the transcript says so. Set `merge_prs: false` at the top of a script to
  turn this off; it defaults to `true`.
- **It retires the seed for the Seuss arm.** CONVENTIONS says a local example never retires a committed seed,
  so house-voice would read the public seed after the local examples. The scratch vault for `vela-seuss`
  starts as if the owner had seeded their voice. The six public-seed examples are set to `retired` in the
  first commit, and the six Seuss-style examples sit in the gitignored `voice/local/`. house-voice reads local
  owner examples first, and two per type is enough, so the Seuss voice is the only voice it reads.
- **It answers nothing else for `gh`.** Past the pull request commands above, the `gh` stub first on `PATH` prints
  "gh: not available in the simulator" and exits 1 (`gh api user` included, so the handle falls back as it would
  offline). `GH_CONFIG_DIR` points at an empty folder,
  and `GH_TOKEN` and `GITHUB_TOKEN` are removed, so even the real `gh` would fail.

## Isolation

- Each assistant call runs in the arm's vault with `--permission-mode acceptEdits`, `--permission-prompts none`
  and an `--allowedTools` list wide enough for the skills: Read, Write, Edit, Glob, Grep, and Bash for git,
  python3, mkdir, cat, date, shasum, cmp, awk, sed, rm, mktemp and gh.
- Every call passes `--setting-sources project,local`, `--strict-mcp-config`, and a `claudeMdExcludes`
  setting for `~/.claude/CLAUDE.md` and `~/.claude/**/*.md`. Your own plugins, hooks, MCP servers and global
  CLAUDE.md would otherwise steer every arm alike and hide the difference the run exists to show.
- The persona and the judge run with `--tools ""`, `--system-prompt`, `--disable-slash-commands` and
  `--no-session-persistence`, in an empty folder in the run. The persona prompt holds the K, W, C and D
  items and never the U items or the truths behind the W items, so it cannot leak a gap.
- `HOME` is left alone, because Claude needs its login. `TMPDIR` points into the run folder, so a skill's
  `mktemp` stays there. Claude Code itself still writes its session logs under `~/.claude/projects/`:
  `--resume` needs them. Nothing else is written outside the run folder.

## Not verified without a paid call

These come from `claude --help` and reading. The smoke run settles them. Each one fails loudly if it is
wrong, rather than producing a quietly wrong score.

1. **The stream-json events.** The driver reads `system`/`init` for `slash_commands`, `assistant` events for
   text and `tool_use` blocks, and the final `result` event for `session_id`, `result`, `total_cost_usd` and
   `is_error`. A missing result field exits 2. If `assistant` events carry no `tool_use` blocks, tool calls
   come out empty, so read `raw/` to confirm.
2. **Whether `total_cost_usd` on a `--resume` call is that call's cost or the session's running total.** The
   driver adds them up as per-call costs. If they are running totals, it overcounts and stops early, which is
   the safe direction. Compare the per-turn costs in `transcript.jsonl` after the smoke run.
3. **The plugin loads, and a slash command passed after `--` runs the skill.** For vela arms, the driver
   checks that the init event's `slash_commands` lists the command and exits 2 if it does not. If the init
   event has no `slash_commands` at all, `run.json` notes "plugin load not verified".
4. **The budget stop.** The driver treats a result with subtype `error_max_budget_usd` as a budget stop and any
   other error as a tool failure.
5. **The isolation settings.** That `--setting-sources project,local` keeps your user plugins and hooks out
   without touching your login, and that `claudeMdExcludes` passed through `--settings` is honored.
6. **The `gh` stub stays first on `PATH`.** Claude Code's Bash tool may rebuild `PATH` from your shell
   profile. If it does, the real `gh` runs, and fails for want of a token instead.
7. **Judge thinking.** `claude --help` lists `--effort <level>`; `alwaysThinkingEnabled` is a settings key the
   help does not list. Whether either makes a `-p` call with `--system-prompt` and `--tools ""` think shows in
   `output_tokens_details.thinking_tokens`, which each scorecard prints per call.
8. **The subagents.** Close dispatches the voice reviewer, and a review checkpoint the five area reviewers, with
   the Agent tool, which `--allowedTools` now lists. Whether a `-p` call with `--permission-prompts none` lets a
   subagent run shows in the transcript: a denied dispatch makes close write "Voice review: not run" and the
   checkpoint write `did not run` for each area, and `area-coverage` with `require: ran` then fails.
9. **The oracle reaches the model.** `claude --help` lists `--append-system-prompt`, and the stub test sees it on
   every assistant call of an `--oracle` probe and on no persona or judge call. Whether a resumed (`--resume`) turn
   keeps it is what the first ceiling run shows: its transcript should follow the instruction after the first turn.

## What it can't tell you

- A simulated lead is more fluent and cooperative than a real one.
- The judge is an LLM. That is why every score cites a turn, and why the transcripts are the primary output.
- It can't say whether it's faster than plain Markdown for the user. Only real sessions under the kill rule can.

## Iterating without teaching to the test

The personas' answer keys are a test. A skill that learns them scores better on the persona and no better for the
next real lead, so the loop never lets a key reach a skill:

1. **Read generic failures from the dev persona only.** `heron-desk` (and the outsiders and team lead its runs bring
   in, all `heron-*`) is the dev persona. After a dev run:

   ```
   python3 tests/sim/run.py --failures tests/sim/results/<dev run>
   ```

   prints what the assistant did wrong as behaviors with turn numbers ("when the lead said they weren't sure, the
   session filed an owner or a due date instead of proposing one and asking (2 times: T52, T192)"), scores per key
   kind, and precision. It never names a key item, never says which items were missed, never quotes a turn, a page
   or the brief, and never names a persona's people, organizations or products: every line comes from a fixed
   template, then a redaction pass replaces any persona term with `[redacted]` and refuses to print (exit 2) if
   one survives. Read the turns it lists in `transcript.html` to see the behavior; don't read the scorecard's
   per-item tables or `personas/heron-desk.yaml` for what to add.
2. **Make one skill change** that fixes a behavior, in the skill's own words and examples. Never paste a persona's
   name, product, keyword or a sentence of its brief into `plugin/**`: `tests/test_sim_seal.py` scans the plugin for
   every persona's terms and fails on a new one (see below).
3. **Run the dev persona again** and compare: `compare_runs.py <previous dev run> <new dev run>`. The verdict reads
   recall and precision only, so a change that writes more without reaching more of the key, or that pads, does not
   pass.
4. **Every second iteration, score the holdouts** (`coastal-merger`, `holdout-hospitals`, `trading-coach`, and
   `coach-lead`, trading-coach's team lead): a full run, `precision.py`, and `compare_runs.py` against the last
   holdout run. They are sealed: scores only, never per-item results, never their failure patterns (`--failures`
   gives a holdout's scores only). A change that lifts the dev persona and not the holdouts learned the dev
   persona, not the job: undo it.
5. **Keep a change only when the keep rule says so** (`probe_keep.py`, below under "Scaled probes, the ceiling and
   the keep rule"): a change counts only if both dev personas (`heron-claims` and `civic-permits`) improve beyond
   the spread and neither holdout (`holdout-nursing`, `holdout-freight`) gets worse, no voice measure gets worse
   beyond its spread, and the voice-loading, leak and conversation-voice tests pass. A change that lifts one dev
   persona and not the other learned that brief, not the job. A change that helps accuracy but hurts the voice is
   reverted.

The keys are sealed three ways. Every persona file says `split: dev` or `split: holdout`, and a persona that says
neither, or a run that names none, is treated as holdout (`seal.py`, `compare_runs.persona_sealed`, `probe.py`).
Per-item results of a holdout are printed only with `--reveal`, by `compare_runs.py`, `failures.py` and `probe.py`
alike. And the plugin is scanned: `tests/test_sim_seal.py` builds the term list from every file in `personas/`
(each persona's name and surname, the names it made up, which are capitalized every time, are not ordinary words of
Python's standard library, and are not real products, the keywords that are not ordinary phrases, and every six-word
run of brief text), leaves out anything the example vault `examples/unified-booking/` holds (coastal-merger borrowed
Harborline, FERRYMASTER and Tidepay from it, and the plugin quotes it as the worked example; its `CONVENTIONS.md` is
the plugin's own file and doesn't count), and fails on any term found under `plugin/**` that
`seal-known-leaks.txt` does not list. That file held 98 terms in 44 files on 2026-10-15 (heron and trading-coach
names and examples in skills, the conventions and the explorer's art); the same day they were rewritten as a
made-up bike-share example and the art keyed by icon kind, so it is empty and any key term in the plugin fails
the test. It only shrinks: the test also fails when a listed leak is gone, and `python3 tests/sim/seal.py
--prune` drops those lines.
`python3 tests/sim/seal.py --leaks` lists every leak by file. `--write-known` accepts new ones and is a reviewed
change, never a way to make the test pass.

## Probes and the iteration loop

A full run is 12 sessions and costs about $36 to $55, which is too slow and too dear to try a skill change. A
probe is one session, started from a saved vault, that checks one capability with mostly mechanical criteria. It
costs about $1 to $3. The loop is: edit a skill, probe it, read the summary, repeat. `probe.py` imports `run.py`
for everything a session needs: the claude calls and isolation flags, the sandbox, the persona and its prompt, the
`gh` stub, the transcript and its HTML, the per-run budget. Only the starting vault, the criteria, blind output
and the loop ledger are its own.

### The commands

One per case and persona. `--budget` is for the whole invocation and is split evenly over `--runs`, so with
`--runs 3` give three times the per-run figure. `--runs` defaults to 5 since 2026-10-15: one or three runs could not
tell a change from noise. Keep one `--loop-ledger` file for one loop.

One run of a probe swings by a whole item or more, so a single before and after cannot tell a change from noise.
The probe ends by printing each check's measure over the runs (probe_scale.summarize, the only averaging): the
mean, the spread (the sample standard deviation) and the values, such as `conflicts surfaced in full: 1.333 of 4 ±
0.577  (1, 2, 1; higher is better)`. A check returns its measure, or a list of them, as its fourth value; a measure
name used twice in one run is a tool failure, never a merged mean. Count a change as real only when the dev mean
moves by more than the larger of the two spreads, and the holdout mean does not fall by more than its spread
(`probe_keep.py`). The numbers are counts, so they print blind too.

```
L="--loop-ledger tests/sim/results/probes/loop-ledger.json --loop-budget 60"
M="--model claude-sonnet-5-5 --persona-model claude-haiku-4-5-20251001 --judge-model claude-sonnet-5-5"
python3 tests/sim/probe.py discover-implications --persona coastal-merger    --runs 1 $M --budget 4 $L
python3 tests/sim/probe.py discover-implications --persona holdout-hospitals --runs 1 $M --budget 4 $L
python3 tests/sim/probe.py dump-sweep            --persona coastal-merger    --runs 1 $M --budget 3 $L
python3 tests/sim/probe.py dump-sweep            --persona holdout-hospitals --runs 1 $M --budget 3 $L
python3 tests/sim/probe.py shape-options         --persona coastal-merger    --runs 1 $M --budget 3 $L
python3 tests/sim/probe.py shape-options         --persona holdout-hospitals --runs 1 $M --budget 3 $L
python3 tests/sim/probe.py discover-reviewers    --persona coastal-merger    --runs 1 $M --budget 8 $L
python3 tests/sim/probe.py discover-reviewers    --persona holdout-hospitals --runs 1 $M --budget 8 $L
```

Every model flag, `--budget`, `--loop-ledger` and `--loop-budget` is required. `--stub` uses the fake claude and
costs nothing. `--out` moves the results folder, which defaults to `tests/sim/results/probes/` (gitignored).

### The cases

Each case in `probes/` names a snapshot per persona, the opening message, a cap in assistant turns and its
criteria. The opening may use `{opening}`, `{topics[...]}` and `{first_decision}` (the persona's first D question).

| Case | Starts from | Opening | Cap | Passes when |
|---|---|---|---|---|
| `discover-implications` | coastal `after-s2`, holdout `after-dump`, heron and trading-coach `empty` | `/vela:discover {topics[discover_1]}` | 12 | at least half the gaps surfaced first (judged); at least 75% of the `cross-source-mismatch` items FLAGGED; 0 decided without a yes |
| `dump-sweep` | `empty` | `/vela:dump {opening}` | 12 | at least 3 of legal-regulatory, finance-liability, third-party-contract and unnamed-stakeholder raised first by the assistant; at most 3 questions in any turn; no decisions |
| `shape-options` | coastal `after-s4`, holdout `after-discover` | `/vela:shape {first_decision}` | 8 | 2 to 4 options, each naming its costs, what it rules out, and a stakeholder or unknown; no decisions |
| `discover-reviewers` | coastal `after-s4`, holdout `after-discover` | `/vela:discover {topics[discover_2]}`, then `/vela:close` | 14, then 10 | every review checkpoint gives all five focus areas a result and every area ran; every owed copy has a valid disposition; 0 decided without a yes |

| `stakeholder-conflict` | heron and trading-coach `empty`, holdout `after-dump` | `/vela:discover {topics[discover_1]}, and who wants what from it` | 12 | at least half the stakeholder positions surfaced in full: the disagreement named, who holds it named in that turn, and recorded as an unknown or risk; 0 decided without a yes |
| `unsure-owner` | heron and trading-coach `empty`, holdout `after-dump` | `/vela:discover {topics[discover_1]}`, with news that the lead knows no owner or date | 12 | every time the lead is unsure of an owner or date the next turn proposes one and asks; no owner or date written that the lead's next message didn't say yes to or name |
| `grill-decisions` | heron `after-full-1`, holdout `after-discover` | `/vela:grill {topics[grill]}` | 14 | at least 1 decision recorded after an explicit yes; 0 without; at most 3 questions in any turn |
| `grill-ready` | heron `grill-ready` | `/vela:grill the prep note's requirements` | 14 | both ready requirements decided after an explicit yes, none without one, and none of the three blocked ones decided; at most 3 questions in any turn |

`discover-implications` also counts gaps (`gaps-surfaced`): the U items the assistant raised before the lead did,
in any words. One judge call (run.py's `unaware` category, about $0.05) reads the gap items and the session and
cites a turn and a quote for each it finds; a quote that is not in that assistant turn drops the claim, so the judge
can fail a gap but never pass one. Its per-item verdicts go to the blind detail file only. The older keyword count,
`unaware-raised-first`, needed one of the item's keywords, which are a specialist's terms, and scored a gap raised
in plain words as a miss; it stays as a check for a case that wants the exact term.

`grill-decisions` could not tell a careful grill from a timid one: no heron snapshot held an item the gate finds
ready, so deciding nothing passed. `grill-ready` starts from `heron-desk/grill-ready`, which is `after-full-1` with
a Shape's options written for three of the prep note's requirements. `vela check --gate decide --item` finds two of
them ready and the third, and the other two, waiting on open questions only the DPO and Legal can answer;
`tests/test_probe.py` checks the case's lists against the gate. `decided-items` reads each named item's own
`**State:**` after every turn, so items that share a page are told apart.

heron-desk is the dev persona of every case it maps; `python3 tests/sim/failures.py <probe run
folder>` prints a probe's generic failure patterns, sealed for a holdout as for a full run. The loop ledger is
written under a lock, so the dev and holdout probes of one iteration can run side by side.

A case with `close: <cap>` runs `/vela:close` as a second session after the first, with that cap, and its
criteria read the vault after the close. The question ledger is written at close, so a criterion on the ledger
needs it.

How each criterion is measured:

- **Owed copies disposed.** The current plugin's `vela questions --json` and `vela check` run on the final
  vault. It passes when every owed copy of the case's `severity` (`high`, or `any`) has a ledger row whose state is
  not `open`, through its own row, a wildcard or an initiative row, and check flags no ledger row (E801, E802,
  E803). The summary gives counts only.
- **Area coverage.** Each `- **Coverage:**` line a review checkpoint wrote into a session record must give every
  focus area in the catalog one result: `found N`, `checked, none` or `did not run (<reason>)`. With
  `require: ran`, an area that did not run fails the run, so a reviewer that was never dispatched cannot pass as
  clean. No coverage line at all fails too.

- **FLAGGED, LISTED, NEVER.** For each keyword hit in an assistant turn, the hit is FLAGGED when (a) its sentence is
  a question, (b) its sentence, or the whole bullet or table row it sits in, holds a flag cue (conflict, mismatch,
  differ, disagree, clash, contradict, both sources, two different, doesn't match, inconsistent, flag), or (c) the
  keyword lands in the final vault in an unknown or a risk that the snapshot did not already hold it in: a
  `### UNK-` or `### R-` section, or an `[unknown]` or `[worry]` capture, which is where a session that has not
  closed keeps them. Otherwise it is LISTED, and an item no turn names is NEVER. A question that is only a
  confirmation tag ("99.9%, right?", "Is that right?", "(yes/no)?") is not a question here: a read-back list with
  "right?" on every line would otherwise flag everything on it.
- **Raised first.** An item counts when an assistant turn holds one of its keywords before any lead turn does.
  Categories are counted, not items, so one lucky guess does not pass.
- **Decisions.** After every assistant turn the driver reads the vault for lines that record a decision: `state:
  decided`, `**State:** decided`, a `| decided |` cell, a `(decided)` capture mark, a `**Decision:**` bullet. Each
  new one is pinned to that turn. It is "with a yes" when a lead message since the last decision said yes to an
  assistant turn that asked a question. A grill reads back, gets the yes, asks why, and files the decision after
  the why answer, so the yes is often a turn or two earlier; a turn that records a decision uses the yes up.
- **Questions per turn.** `run.py`'s count: question marks in the turn's prose.
- **Options.** The first assistant turn with two or more labeled options ("Option A", "### B.", "**1)**") is
  read. A label seen twice ends the options. Cue words settle each part: costs (cost, effort, expensive, budget,
  £...), rules out (rules out, gives up, precludes, closes off...), stakeholder or unknown (an `UNK-` ID, "unknown",
  a role such as director or board, or a stakeholder the persona names). Only when a part is still missing, or no
  labels were found, one judge call without tools reads that turn. Its "present" counts only with a quote that is
  in the turn, so a careless judge can fail an option but never pass one.

### Snapshots

`snapshots/<persona>/<name>/` are plain vault trees, committed.

| Snapshot | What it is |
|---|---|
| `coastal-merger/empty` | `plugin/template/` as `tests/evals/scaffold.py` builds it for a run, without `.claude/skills` |
| `coastal-merger/after-s2` | the vela arm of `results/2026-10-05-124823-coastal-merger` (recorded under its old arm name, see `LEGACY_NAMES`) after its dump and close: `git archive 4185442` |
| `coastal-merger/after-s4` | the same run after its first discover and close: `git archive 0ed88c7` |
| `holdout-hospitals/empty`, `after-dump`, `after-discover` | written by hand as a dump and close, then a discover and close, would leave them; each passes `vela check` with 0 errors |

Each snapshot holds the persona's documents in `.inbox/`, exactly as `run.py` writes them. A vault's `.gitignore`
ignores `.inbox/`, and git honors that file inside the snapshot too, so they are committed with `git add -f`. A
probe whose snapshot inbox has drifted from the persona's docs stops with exit 2.

A probe copies the snapshot into its run folder, removes any `.claude/skills` it holds, installs the current
`plugin/` at `.claude/skills/vela`, and runs `git init`, the first commit, the bare origin and the push as
`run.py` does. Assistant calls pass `--plugin-dir plugin` too. So a skill edit takes effect on the next probe,
and no snapshot can carry an old copy of a skill. `start-check.txt` holds `vela check` on the starting vault.

### Blind runs and the holdout

`holdout-hospitals` is a second domain with the same shape and the same categories, for checking that a skill
change did not just learn one brief. Since 2026-10-15 coastal-merger and trading-coach are holdouts too (see
"Iterating without teaching to the test"). **While iterating, never read a holdout's persona file, its snapshots,
or anything in a blind run's folder.** The tooling never shows them: a persona with `split: holdout` (or no split)
is always blind unless `--reveal` is given, and `tests/test_sim.py` checks a holdout by counts only, so a failing
test cannot print it. The probe cases start from coastal-merger snapshots, so a probe now prints categories and
counts by default; `--reveal` shows the items, for debugging a case, never for tuning a skill.

Blind output prints categories and counts only, such as "cross-source-mismatch: 2 of 4 flagged, 1 listed, 1
never". It never prints an item ID, its text, its keywords, the opening or a transcript excerpt. A tool failure
prints only the part of its message that names what failed. The item detail goes to
`detail-DO-NOT-READ-WHEN-BLIND.md` in the run folder, and an invalid holdout persona's problems to a
`...-validation-detail-DO-NOT-READ-WHEN-BLIND.md` file. `--blind` does the same for any persona.

### The loop ledger

`--loop-ledger` is a JSON file that adds up what every invocation spent: `spent_usd` and one entry per
invocation with its case, persona, runs, budget, spend, exit code and run folders. `probe.py` refuses to start,
exit 1, when the ledger's spend plus this `--budget` would pass `--loop-budget`, and prints the running total
before and after every invocation. A ledger that does not parse is exit 2, never a fresh start. Spend is recorded
even when a run fails part-way.

### Output and exit codes

Each run writes `tests/sim/results/probes/<timestamp>-<case>-<persona>-<n>/`: `transcript.jsonl`,
`transcript.html`, `vault/` with its own git history, `vault-check.txt`, `viewer.html`, `raw/`, `probe.json`
(the printed summary, blind-safe) and `detail-DO-NOT-READ-WHEN-BLIND.md` (per item, with turns and excerpts).

- 0: every run passed every criterion.
- 1: a run failed a criterion, a run ended on its budget (the criteria then read a cut-off session), or the loop
  ledger refused to start.
- 2: a tool failed: claude, git, a snapshot, a case or persona file, the ledger, or the judge's JSON twice.

### Cost of one probe run

Rough, from the same assumptions as the Cost section above, on a Sonnet-class assistant and a Haiku-class persona.
A probe session is short, so the context stays near the 30k floor and the persona reads a small transcript.

- `discover-implications`: 6 to 12 assistant turns, each reading the inbox and writing facts, at $0.15 to $0.35,
  plus about $0.01 to $0.03 a persona turn: about **$1 to $4**. Budget $4 a run.
- `dump-sweep`: 6 to 12 short capture turns at $0.10 to $0.25: about **$0.80 to $3**. Budget $3 a run.
- `shape-options`: 3 to 8 turns at $0.10 to $0.30, plus at most two small judge calls of a few cents: about
  **$0.50 to $2.50**. Budget $3 a run; 15% of it is held back for the judge, as in `run.py`.

No probe has been run with a real model yet. The first paid probes settle these figures, and `probe.json` holds
each run's real spend.

### Scaled probes, the ceiling and the keep rule

Round two of the probe loop (2026-10-15) could not show an improvement where one might exist: the scales were too
short (decisions topped out at 2, the hospitals holdout had 4 conflicts, most scores sat at the floor or the
ceiling), one to three runs could not separate a change from noise, and nobody knew what score a probe could reach.
The rebuild fixes each in its own place.

**Bigger scales.** `scale/cases/` holds four cases, each scored on 6 to 8 items, for two dev personas and two
holdouts (sealed: never read a holdout while iterating). Their snapshots are in `scale/snapshots/`, named by the case's
`snapshot_root:`. `probe.py <case>` finds a case in `probes/` first, then `scale/cases/`.

| Split | Persona | Field | Difficulty |
|---|---|---|---|
| dev | `heron-claims` | expense claims at a professional-services firm | normal |
| dev | `civic-permits` | residential building permits at a city | hard: gaps buried in staff shorthand, two resting on a remark the lead makes only in passing; positions held by groups the lead meant to consult late; owners mostly unclear, every loose end between two groups |
| holdout | `holdout-nursing` | sealed | sealed |
| holdout | `holdout-freight` | sealed | normal |

Every persona has the same scale: 8 gaps, 8 positions, 6 loose ends, and a grill-ready vault with 8 ready items and
3 blocked. The second dev persona (2026-10-16) is there so a change has to help two briefs in different fields, one
of them hard in the generic ways a holdout can be, before it counts; the second holdout widens what "didn't get
worse" covers.

| Case | Starts from | Opening | Cap | Measure (of N) |
|---|---|---|---|---|
| `scale-gaps` | `empty` | `/vela:discover {topics[discover_1]}` | 14 | gaps raised as an issue (a real question on the line, a flag cue, or a new unknown or risk) before the lead names them, of 8 |
| `scale-conflicts` | `empty` | `/vela:discover {topics[discover_people]}` | 24 | stakeholder positions surfaced in full (disagreement named, holder named, recorded as open), of 8 |
| `scale-unsure` | `empty`, with unsure-owner's news | `/vela:discover {topics[loose_ends]}` | 24 | the lead's loose ends named in a turn that proposes who or by when and asks, of 6; any owner or date written unconfirmed fails the run |
| `scale-decisions` | `grill-ready` | `/vela:grill {topics[grill]}` | 30 | ready items decided after the lead's yes, of 8; any of the 3 blocked items decided fails the run |

How the material keeps the scale honest:

- A gap's keywords name the document facts it rests on, so reading a document back (LISTED) never counts; seeing what
  two facts imply and asking about it does.
- The stakeholder positions are facts, not C items. The persona relays C items whenever asked "who wants what"; a
  fact is given only when its own subject comes up ("Only if you are asked about audit..."). So the opening does not
  hand the positions over, and a session hears one only by asking the right kind of question. No position's keyword
  is in a document or another fact.
- A decision with `item:` names a requirement on the grill-ready snapshot; `blocked: true` ones are held there by an
  open unknown, and the lead's `refuse_until` keeps them undecided. `vela check --gate decide` on the snapshot says
  exactly the other eight are ready, and `tests/test_probe_scale.py` holds it to that.
- A loose end counts in `scale-unsure` when its turn proposes who or by when and asks about it anywhere later in that
  turn, so one closing question can confirm a batch. Until 2026-10-16 the question had to sit within 200 characters
  of the proposal (the unsure-owner check's window, which that check keeps), and a dev baseline run that proposed and
  asked for all six in one turn scored 0.
- Checks read items by kind, category and those flags only. Summaries hold counts; item IDs go to the detail file.

**The ceiling.** Each scaled case has an `oracle:`, a plain instruction to do exactly the measured behavior. `--oracle`
passes it to every assistant call of that probe as `--append-system-prompt`, never through `plugin/**`, so it
measures the material, not a skill. Run it once per case and persona before any baseline: its score is the reachable
maximum. A low ceiling means the persona or the snapshot is broken; fix the material, never the skill. An oracle names
nothing from any brief (`tests/test_probe_scale.py` scans it with the seal's terms).

**Power.** Every check that has a scale returns a measure, and every probe ends with a summary over its runs: each
measure's mean, its spread (the sample standard deviation; 0 for one run) and its values. The same numbers go to
`<stamp>-<case>-<persona>[-oracle]-summary.json` in `--out` and to the loop ledger entry. **A change is real only when
its mean moves by more than the larger of the two spreads.**

**The voice.** Every probe, old cases too, also measures the voice on the lead-facing turns (the assistant's own text,
not tool output or subagents), each with mean and spread:

- codes and IDs per turn, counted with `vela.say.LEAD_PATTERNS` (the patterns `--for-lead` refuses), overlapping
  matches once;
- the voice score: the share of turns with none, of 100;
- turns that told rather than asked: a turn that settles something ("I've gone with", "the answer is", "you should")
  and asks nothing. A mechanical stand-in for the full run's judge measure of the same name;
- turns offering more than four things (`say.LEAD_LIMIT`): top-level list items and table rows, or questions,
  whichever is more;
- whether the voice-loading step ran: the share of sessions that read `CONVERSATION-VOICE.md` before their first
  question (START step 0).

A voice sensor that breaks is a tool failure, exit 2, never a quiet zero.

**The keep rule.** After a skill change, with a before and an after summary for every persona the case maps (each
flag once per persona; the n-th before pairs with the n-th after):

```
python3 tests/sim/probe_keep.py \
  --dev-before <heron-claims A> --dev-after <heron-claims B> --dev-before <civic-permits A> --dev-after <civic-permits B> \
  --holdout-before <nursing C> --holdout-after <nursing D> --holdout-before <freight C> --holdout-after <freight D>
```

A change counts only if both dev personas improve beyond the spread and neither holdout gets worse. It prints each
persona's measures, each move against its spread, and KEEP (exit 0) only when all four hold: for each dev persona, an
accuracy measure is a real gain and none a real loss; no accuracy measure of either holdout is a real loss; no voice
measure, dev or holdout, is a real loss; and `tests/test_conversation_voice.py` (the conversation voice and the
voice-loading order), `tests/test_lead_voice.py`, `tests/test_sim_seal.py` (the leak seal) and
`tests/test_skill_load.py` pass. Otherwise REVERT (exit 1) with the reasons. An oracle summary, a holdout in the dev
pairs, summaries of different cases, a persona given twice, or a persona the case maps with no pair is a tool failure
(exit 2): a missing holdout is never read as "didn't get worse".

**Cost.** From round one's real spend (a discover probe of 12 turns cost $1.80 to $3.90, about $2.60), at the caps
above: a discover case is about $3 a run ($2.20 to $4.50), `scale-unsure` about $2.40, and `scale-decisions`, a grill
of up to 30 turns that files eight decisions, about $7 ($4 to $10; not yet measured). One ceiling run and a 5-run
baseline per case on each persona is 12 runs a case: about $36 for gaps, $36 for conflicts, $29 for unsure owners and
$84 for decisions, about **$185 in all ($120 to $260)**. Run the eight ceiling runs first (about $31): a low ceiling
saves the baselines for material that works. Give `--budget` as $5 a run for a discover case and $12 a run for the
grill, so 5 runs take `--budget 25` or `--budget 60`. The second pair of personas (`civic-permits` and
`holdout-freight`, 2026-10-16) costs the same again: about $185 ($120 to $260) for their ceilings and 5-run baselines
on all four cases, $31 of it the eight ceiling runs. Their material is checked on the stub only; no paid run yet.

## Tests

`tests/test_sim.py` runs the driver end to end against `stub/claude`, with every arm and a two-session
script. It checks the transcript, the HTML escaping, `--resume` from the second turn, the `gh` stub on `PATH`,
the Seuss examples in one arm only, the baseline vault without skills, the budget stop (exit 1), a missing JSON
field (exit 2), bad judge JSON (exit 2), the required flags, the persona and script files, the voice files,
the simulated merge, that nothing is written outside the run folder, the persona keywords, the keyword hits (lead
turns excluded for U), Check these, one judge call per category with thinking asked for, the `search` note, and
`--rejudge` on a copy of a stub run without an assistant or persona call. It costs nothing.

`tests/test_probe.py` runs `probe.py` against the same stub: the snapshot copy with the current plugin installed
over the snapshot's, every snapshot passing `vela check` with its persona's inbox, category validation, flag
detection (a question, a cue, an unknown, a read-back list counted as listed), decisions pinned to a turn, the
options and the judge's quotes, blind output holding no ID, keyword or brief text, the holdout always blind, the
ledger refusing to start, and every exit code. Holdout tests assert on counts only. It costs nothing.

`tests/test_probe_scale.py` pins the rebuild, also on the stub: each scaled check and its measure, the voice
measures, mean and spread and the "real change" rule, the keep rule (a gain that hurts the voice is reverted; an
oracle summary or a holdout in the dev pair is refused), the oracle reaching every assistant call and nothing else,
5 runs by default, the scaled snapshots (clean, their persona's inbox, 0 errors), each persona's scale and splits,
positions heard only when asked, the grill-ready vaults' eight ready and three blocked items, oracles naming no key
term, every scaled case and its ceiling run on the stub for all four personas with a holdout's output holding counts
only, and the keep rule needing both dev personas to gain, neither holdout to fall, and a pair for every persona the
case maps.

`tests/test_sim_compare.py` runs `compare_runs.py` on runs it builds from a few pages and turns: lines copied from a
run recorded before the rename (`legacy_lines.py`) count the same as their hand-renamed twins, and an old arm folder
pairs with today's. `tests/test_sim.py` also rejudges and compares a stub run whose arm folder carries the old name.
`tests/test_sim_compare.py` also pins the verdict: recall up with precision steady is GO whatever the item count did, recall up with precision
down is never GO, a weak kind that falls is named, no scorecard is UNSCORED, and a holdout's report and JSON hold no
key item ID unless `--reveal`.

`tests/test_sim_precision.py` pins the precision pass: which text is an item, the stratified, seeded sample,
the neighbours shown for the duplicate check, a citation the driver can't find reading unsupported, the call going
through the judge machinery on the arm's ledger, and the command-line pass writing `precision.json` that the
comparison reads.

`tests/test_sim_seal.py` pins the seal: every persona's split, the term list (names, keywords, brief runs; ordinary
words and the example vault's terms left out), redaction, the plugin scan against `seal-known-leaks.txt`, and the
failure report on stub runs whose assistant says persona names and keywords: no key term, no key item ID, and scores
only for a holdout.

## Files

- `run.py`: the driver.
- `compare_runs.py`: two runs side by side, with the verdict from recall and precision. `legacy_lines.py`: its
  test lines.
- `precision.py`: the precision pass over a sample of the final vault.
- `failures.py`: generic failure patterns of a run for skill authors (`run.py --failures`).
- `seal.py`: the dev/holdout split, the key-term list, redaction and the plugin leak scan.
  `seal-known-leaks.txt`: the plugin's known leaks, to remove (empty since 2026-10-15).
- `probe.py`: one-session probes from a snapshot, for the iteration loop.
- `probe_scale.py`: the scaled checks and their measures, the oracle, the voice measures, and mean, spread and the
  "real change" rule. `probe_keep.py`: the keep rule over a before and after pair for every persona a case maps.
- `probes/`: the probe cases. `snapshots/`: the starting vaults. `scale/cases/` and `scale/snapshots/`: the scaled
  cases and theirs.
- `personas/heron-claims.yaml` and `personas/civic-permits.yaml`: the scaled probes' dev personas, the second one
  hard. `personas/holdout-nursing.yaml` and `personas/holdout-freight.yaml`: their holdouts. Do not read them while
  iterating.
- `personas/heron-desk.yaml`: the dev persona, with the `heron-*` personas its runs bring in.
- `personas/holdout-hospitals.yaml`: a holdout. Do not read it while iterating.
- `personas/coastal-merger.yaml`: a holdout since 2026-10-15, and the default persona of the smoke and default
  scripts. Harborline has merged with Northway Rail, the CIO's
  mandate is one line, and the lead starts from an empty vault. 15 K, 5 W, 8 U, 4 C and 5 D items, each with
  two to four `keywords`, and four inbox documents that contradict each other in places. A missing or empty
  keyword list fails the run at load, exit 2, and no keyword other than K1's may appear in the opening. Every
  item also has one `category` from the fixed set in `run.py` (`CATEGORIES`), checked at load the same way.
- `scripts/default.yaml` and `scripts/smoke.yaml`: the sessions, with each arm's opening and a turn cap.
  `scripts/retired/` keeps four scripts that ran the user's own skills, now removed; no test reads them.
- `voices/seuss-style/`: two original pastiche examples per voice type. None holds text from any published
  book, and each says so in its `from` field.
- `stub/claude`: the scripted fake.
