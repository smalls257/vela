# tech-design-grill: vault mode

This folder adds a vault mode to your `tech-design-grill` skill, so a senior can start tech design from an app the solution lead has handed off. Nothing in the toolkit edits `~/.claude/skills`. You apply the change yourself.

- `skill/` is your skill as it stood on 2026-10-03, with the vault-mode edits applied.
- `vault-mode.patch` holds the same edits as a patch against `~/.claude/skills/tech-design-grill`.

## The edits

1. `SKILL.md` description: it mentions starting from an initiative vault.
2. `PREREQ-CHECK.md`: the "Vault mode" section, byte for byte the one in the requirements-grill integration. Given `--vault <path> --app <APP-id>`, the prereq is that app's page carrying `handed_off`, not `docs/requirements/<slug>.md`, and the skill follows `<path>/.claude/skills/vela/references/TECH-DESIGN-FROM-VAULT.md`.
3. `SKILL.md` what-to-do, Inputs and Boot step 1: in vault mode the "what" is the handed-off app's pages, and the trace targets come from that reference.
4. `SKILL.md` hard rule: in vault mode a functional gap becomes an `OQ-XXX` that challenges a vault ID, and the session goes on.

## Install

Back up your skill first. The backup goes outside `~/.claude/skills`, so it is not picked up as a second skill:

```
cp -R ~/.claude/skills/tech-design-grill ~/tech-design-grill.bak-$(date +%F)
```

Check that the patch still fits your skill:

```
cd ~/.claude/skills && patch -p1 --dry-run < <toolkit>/integrations/tech-design-grill/vault-mode.patch
```

If it reports no failed hunk, apply it:

```
cd ~/.claude/skills && patch -p1 < <toolkit>/integrations/tech-design-grill/vault-mode.patch
```

If a hunk fails, your skill changed after the copy was made. Make the edits above by hand. Do not copy `skill/` over your skill unless you have no local changes to keep.

Apply the requirements-grill patch too, so both copies of `PREREQ-CHECK.md` stay identical.

## Check it

1. On the fixture, `--vault <toolkit>/examples/unified-booking --app APP-booking` passes the prereq, because Booking carries `handed_off`.
2. On a copy of the fixture with that field removed, it refuses and says the app is not handed over yet.
3. With no `--vault`, it asks for `docs/requirements/<slug>.md` as before.

## Undo

To restore from the backup, copy it back over the skill (use the date you made it):

```
rm -r ~/.claude/skills/tech-design-grill && cp -R ~/tech-design-grill.bak-<date> ~/.claude/skills/tech-design-grill
```

Or reverse the patch:

```
cd ~/.claude/skills && patch -p1 -R < <toolkit>/integrations/tech-design-grill/vault-mode.patch
```

## Inside this app (optional, after vault mode)

`inside-view.patch` goes on top of vault mode. It records which vault IDs each component owns and which container
each component sits in, so the explorer's Inside this app reads ownership instead of inferring it. Back up first,
then from `~/.claude/skills`:

```
patch -p1 --dry-run < <toolkit>/integrations/tech-design-grill/inside-view.patch
patch -p1 < <toolkit>/integrations/tech-design-grill/inside-view.patch
```

`skill/` here stays vault mode only, so `vault-mode.patch` still reverses to the upstream skill.
