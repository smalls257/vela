# Session simulator

A simulated solution lead runs real multi-turn Claude Code sessions in a scratch vault, once per arm. Each arm
gets the same persona and the same script. Every run leaves transcripts you can read and a scorecard measured
against the lead's hidden brief. The design is `docs/design-sessions/08-session-simulator.md`.

It answers one question. When a lead starts from a vague idea, do the planner skills guide them to figure
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

- `--arms` defaults to `planner,planner-seuss`. `baseline` runs only when you name it, as `--arms planner,baseline`.
- `--script` takes a name in `scripts/` or a path. `default` runs dump → close → discover → close → shape →
  close → discover → close → shape → close → grill → close.
- `--stub` swaps `claude` for the scripted fake in `stub/`. It costs nothing, and it is what the tests use.
- `--out` changes the results folder. The default is `tests/sim/results/`, which git ignores.

| Arm | Vault | Plugin | Voice |
|---|---|---|---|
| `planner` | `template/`, plugin copied to `.claude/skills/planner` | `--plugin-dir plugin` | the AOSA public seed |
| `planner-seuss` | the same | `--plugin-dir plugin` | `voices/seuss-style/` in `voice/local/`, public seed retired |
| `baseline` | `template/` with no `.claude/skills` | none | none: the vault's `CONVENTIONS.md` and `CLAUDE.md` only |

### Exit codes

- 0: every session of every arm ended when the persona wrote `[END]`, and every arm was scored.
- 1: the budget or a turn cap ended at least one session early. Every output is still written.
- 2: a tool failed. `claude` was missing, its JSON lacked a field, a call errored, the judge's JSON was bad
  twice, or git or the scaffold failed. The run stops at that arm. What was written before the failure stays,
  and `run.json` names the failure. The raw output of every call is in `<arm>/raw/`.

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
- The judge is one call over the transcript and the vault pages, about 100k tokens: under $1 an arm.

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
| `<arm>/vault-check.txt` | `planner check` on the final vault, with its exit code. |
| `<arm>/viewer.html` | `planner view` of the final vault. If the vault does not parse, `viewer-error.txt` says why instead. |
| `<arm>/scorecard.json`, `scorecard.md` | The judge's scorecard after the driver checked every citation. |
| `<arm>/raw/` | The raw stdout and stderr of every `claude` call, numbered in order. Read these when a run exits 2. |

## How to read a scorecard

The brief has five kinds of item, each with an ID:

- **U, gaps.** Things the lead never thought about. "Surfaced" means the assistant raised it first. This is the
  heart of the question: a good session finds what the lead does not know to ask.
- **W, wrong beliefs.** "Challenged" means the assistant questioned the belief, or gave a reason or a source
  against it.
- **K, facts.** "Captured" means the fact is written somewhere in the final vault, with the file named.
- **D, decisions.** "Decided" with "yes asked" tells you whether the explicit yes was asked for. D4 is one the
  lead refuses to make until procurement confirms the FERRYMASTER contract, so deciding it is a failure.
- **C, stakeholder conflicts.** "Surfaced" means the assistant named the disagreement as something to resolve,
  rather than picking a side.

The shape of the guidance: the most questions in one assistant turn (counted by the driver, not the judge),
the turns that told rather than asked, decisions made without a yes, invented facts, and whether each session
ended with a clear next step.

Every claim needs a turn number and a quote. The driver checks each one against the transcript: the quote must
appear in that turn, give or take whitespace, quote marks and emphasis. A K claim must name a file that exists
in the final vault. A claim that fails is turned to "no" and listed under "Dropped claims". This is mechanical,
not taste. Read the quoted turns in `transcript.html` before you believe a score.

## What the driver does that a person would do

- **It merges each closed session.** After every close session, the driver merges each `session/*` branch
  whose records are all closed into `main` on the bare origin, as a reviewer merging the PR would. Without
  this, the next session's START would pull a `main` without the last session's work. A branch with an open
  record, or one that conflicts, is not merged, and the transcript says so.
- **It retires the seed for the Seuss arm.** CONVENTIONS says a local example never retires a committed seed,
  so house-voice would read the public seed after the local examples. The scratch vault for `planner-seuss`
  starts as if the owner had seeded their voice. The six public-seed examples are set to `retired` in the
  first commit, and the six Seuss-style examples sit in the gitignored `voice/local/`. house-voice reads local
  owner examples first, and two per type is enough, so the Seuss voice is the only voice it reads.
- **It answers nothing for `gh`.** A `gh` stub first on `PATH` prints "gh: not available in the simulator" and
  exits 1, so every `gh` failure path in the skills runs honestly. `GH_CONFIG_DIR` points at an empty folder,
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
3. **The plugin loads, and a slash command passed after `--` runs the skill.** For planner arms, the driver
   checks that the init event's `slash_commands` lists the command and exits 2 if it does not. If the init
   event has no `slash_commands` at all, `run.json` notes "plugin load not verified".
4. **The budget stop.** The driver treats a result with subtype `error_max_budget_usd` as a budget stop and any
   other error as a tool failure.
5. **The isolation settings.** That `--setting-sources project,local` keeps your user plugins and hooks out
   without touching your login, and that `claudeMdExcludes` passed through `--settings` is honoured.
6. **The `gh` stub stays first on `PATH`.** Claude Code's Bash tool may rebuild `PATH` from your shell
   profile. If it does, the real `gh` runs, and fails for want of a token instead.
7. **The voice reviewer.** Close dispatches it with the Agent tool, which is not in `--allowedTools`. With
   `--permission-prompts none` it may be denied, and close then writes "Voice review: not run".

## What it can't tell you

- A simulated lead is more fluent and cooperative than a real one.
- The judge is an LLM. That is why every score cites a turn, and why the transcripts are the primary output.
- It can't say whether it's faster than plain Markdown for the user. Only real sessions under the kill rule can.

## Tests

`tests/test_sim.py` runs the driver end to end against `stub/claude`, with every arm and a two-session
script. It checks the transcript, the HTML escaping, `--resume` from the second turn, the `gh` stub on `PATH`,
the Seuss examples in one arm only, the baseline vault without skills, the budget stop (exit 1), a missing JSON
field (exit 2), bad judge JSON (exit 2), the required flags, the persona and script files, the voice files,
the simulated merge, and that nothing is written outside the run folder. It costs nothing.

## Files

- `run.py`: the driver.
- `personas/coastal-merger.yaml`: the default persona. Harbourline has merged with Northway Rail, the CIO's
  mandate is one line, and the lead starts from an empty vault. 15 K, 5 W, 8 U, 4 C and 5 D items, and four
  inbox documents that contradict each other in places.
- `scripts/default.yaml` and `scripts/smoke.yaml`: the sessions, with each arm's opening and a turn cap.
- `voices/seuss-style/`: two original pastiche examples per voice type. None holds text from any published
  book, and each says so in its `from` field.
- `stub/claude`: the scripted fake.
