# Plugin evals

Seven cases, each in two arms: `plugin/<case>/` (the planner plugin, prompt starts `/planner:`) and
`stub/<case>/` (conventions only, prompt points at `CONVENTIONS.md`). `tests/test_evals.py` checks the
case files and scaffolds without calling a model. Every real run costs money and is started by hand.

`run.py` runs both arms with `--keep-temp`, then grades each kept workspace with `planner check`,
`git status` and file patterns. It prints "could not grade" and exits 2 when it finds no workspace.
Results land in `tests/evals/.results/`, which git ignores.

## Smoke run (about one dollar)

```
python3 tests/evals/run.py e5-ask --model <pinned model> --judge-model <pinned judge> --runs 1 --max-cost-usd 1
```

Confirm three things the Claude Code docs leave open:

1. The scaffold finds the repo from `BASH_SOURCE`.
2. `plugins:` in a `case.yaml` loads that plugin when the target is the file.
3. `--keep-temp` prints paths that `find_workspaces()` recognises.

If any fails, the wrapper says so. Fix `fixture.sh`, `case.yaml` or `find_workspaces()`, then rerun.

## Baseline (V1-07)

Run `e1-dump`, `e1-close`, `e2-discover` and `e3-grill-refused` with `--runs 3 --max-cost-usd 10`.
Write `tests/baseline/2026-10-findings.md`: each failure in the stub arm mapped to the skill meant to
address it, or marked "conventions fix", or "none".

## Ship rule, per skill (06 section 4.2)

On its own cases, the plugin arm beats the stub arm on structural defects or provenance in at least
2 of 3 runs, and passes every invariant in 3 of 3: no `decided` outside a Grill and without an
explicit yes, no invented ID, no write by `/ask`, `check` clean. A skill that fails is cut to a
two-line pointer to `CONVENTIONS.md`.

Rerun a skill's cases after any change to its `SKILL.md` or a reference it reads, and when the
default model changes. `e6-epics` needs Plan C's `epics` skill.
