# requirements-grill: vault mode

This folder adds a vault mode to your `requirements-grill` skill. Nothing in the toolkit edits `~/.claude/skills`. You apply the change yourself.

- `skill/` is your skill as it stood on 2026-10-03, with the four vault-mode edits applied.
- `vault-mode.patch` holds the same four edits as a patch against `~/.claude/skills/requirements-grill`.

## The four edits

1. `SKILL.md` description: it mentions initiative vaults, so Claude picks the skill there.
2. `PREREQ-CHECK.md`: a "Vault mode" section. When `.planner.yaml` is at the repo root, vault mode is on, a `CAP-NNN` scope is required, and the skill follows `.claude/skills/planner/references/REQUIREMENTS-IN-VAULT.md` from the vault's planner plugin.
3. `SKILL.md` "Capture answers inline", Output and "Capture inline": in vault mode, write where that reference says, never under `docs/requirements/`.
4. `SKILL.md` completion gate: in vault mode, run `NEG-AUDIT.md`, then hand over to `/planner:close` instead of flipping `status: complete`.

## Install

Check that the patch still fits your skill:

```
cd ~/.claude/skills && patch -p1 --dry-run < <toolkit>/integrations/requirements-grill/vault-mode.patch
```

If it reports no failed hunk, apply it:

```
cd ~/.claude/skills && patch -p1 < <toolkit>/integrations/requirements-grill/vault-mode.patch
```

If a hunk fails, your skill changed after the copy was made. Make the four edits above by hand. Do not copy `skill/` over your skill unless you have no local changes to keep.

`PREREQ-CHECK.md` is the same file in `requirements-grill` and `tech-design-grill`. The section this patch adds covers both skills, so after this patch the two copies differ until you also apply `integrations/tech-design-grill/vault-mode.patch`, or copy this `PREREQ-CHECK.md` over the other one.

## Check it

1. In a vault with the planner plugin at `.claude/skills/planner`, run requirements-grill scoped to one capability. It writes `### CAP-NNN.FRn` items at `assumption`, each with a `**Source:**` capture link, and no file under `docs/requirements/`. "Decide FR1" is refused and a Grill is offered. Then `python3 .claude/skills/planner/bin/planner check` exits 0.
2. In a repository with no `.planner.yaml`, run it as before. It writes `docs/requirements/<slug>.md` with the same sections as before the patch.

## Undo

```
cd ~/.claude/skills && patch -p1 -R < <toolkit>/integrations/requirements-grill/vault-mode.patch
```
