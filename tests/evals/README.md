# Plugin evals

Eight cases, each in two arms: `plugin/<case>/` (the planner plugin, prompt starts `/planner:`) and
`stub/<case>/` (conventions only, prompt points at `CONVENTIONS.md`). `tests/test_evals.py` checks the
case files and scaffolds without calling a model. Every real run costs money and is started by hand.

`run.py` runs both arms with `--keep-temp`, then grades each kept workspace with `planner check`,
`git status` and file patterns. It prints "could not grade" and exits 2 when it finds no workspace.
Results land in `tests/evals/.results/`, which git ignores.

## Smoke run (about one dollar)

```
python3 tests/evals/run.py e5-ask --model claude-sonnet-5-5 --judge-model claude-haiku-4-5-20251001 --runs 1 --max-cost-usd 1
```

Confirm three things the Claude Code docs leave open:

1. The scaffold finds the repo from `BASH_SOURCE`.
2. `plugins:` in a `case.yaml` loads that plugin when the target is the file.
3. `--keep-temp` prints paths that `find_workspaces()` recognises.

The model IDs are suggestions: edit them to the IDs you pin. If any fails, the wrapper says so and exits 2. Fix `fixture.sh`, `case.yaml` or `find_workspaces()`, then rerun.

## Cost

`--max-cost-usd` caps one `plugin eval` invocation, which is one arm of one case. A case runs two arms,
so the ceiling for a case is twice it. At the default of 10, the baseline below can spend up to $80 and
all eight cases up to $160. The ceiling is checked before each run starts, so a run in flight can overshoot.

## The override cases

`e3-grill-refused` and `e7-grill-override` start from the same `grill-refused` scaffold: UNK-001 open and
blocking CAP-021. In e3 the lead asks for a plain grill, so grill must not pick an override for them: a
grader fails any Write or Edit that adds `**Override:**`, and the run.py forbid check fails an override
bullet in the CAP-021 page. Offering to "decide anyway" or "override" counts as a way forward.
In e7 the lead explicitly overrides GATE-4 and GATE-5, so CAP-021 must end up decided with an
`**Override:**` naming GATE-4 and a `**Decided by:**` that says "on behalf of". Native graders read the page
(any tool that wrote it). run.py adds what a grader cannot: `planner check` must report W316 and never E316,
and one more decided page is allowed (`may_decide`). The scaffold's owner of CAP-021 is the lead themselves,
so the on-behalf line names the lead twice; the grader checks the wording, not that the handles differ.

## Exit codes

Every `plugin eval` call gets `--threshold 1`, so it exits 1 when any native grader (tool and regex
graders in `case.yaml`) fails in any run.

- 0: `plugin eval` exited 0 for every arm, so every native grader passed, and every kept workspace passed
  the wrapper's own grades (`planner check`, no invented ID, no new `decided` unless the case allows one, check codes a case demands or forbids, file expects and forbids,
  and a clean `git status` for read-only cases).
- 1: `plugin eval` exited 1 for some arm, or some workspace grade printed `FAIL`.
- 2: a run could not be graded. `plugin eval` exited with anything but 0 or 1 (2 is the cost ceiling), or
  the number of kept workspaces differs from `--runs`.

## Baseline (V1-07)

```
python3 tests/evals/run.py e1-dump e1-close e2-discover e3-grill-refused --model claude-sonnet-5-5 --judge-model claude-haiku-4-5-20251001 --runs 3 --max-cost-usd 10
```

The model IDs are editable. Write `tests/baseline/2026-10-findings.md`: each failure in the stub arm mapped to the skill meant to
address it, or marked "conventions fix", or "none".

## Ship rule, per skill (06 section 4.2)

On its own cases, the plugin arm beats the stub arm on structural defects or provenance in at least
2 of 3 runs, and passes every invariant in 3 of 3: no `decided` outside a Grill and without an
explicit yes, no invented ID, no write by `/ask`, `check` clean. A skill that fails is cut to a
two-line pointer to `CONVENTIONS.md`.

Rerun a skill's cases after any change to its `SKILL.md` or a reference it reads, and when the
default model changes. `e6-epics` needs Plan C's `epics` skill.
