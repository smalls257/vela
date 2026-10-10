# work-breakdown

A new skill, not a change to one of yours: it breaks a settled technical design into stories and tasks. Every story traces to a requirement (in vault mode, the app's allocated requirement rows and epic criteria) and to the design's components. Every task is sized S, M or L, and the plan ends with the build order. It reads `tech-design-grill`'s `NEG-AUDIT.md` and `FRONTMATTER-FORMAT.md`, so install that skill's vault-mode patch first.

## Install

```
cp -R <toolkit>/integrations/work-breakdown/skill ~/.claude/skills/work-breakdown
```

## Check it

Run `/work-breakdown <slug>` in a repository whose `docs/tech-design/<slug>.md` is `complete` or `complete-with-gaps`. It refuses on one that is `in-progress`. In vault mode, add `--vault <path> --app <APP-id>`.

## Undo

```
rm -r ~/.claude/skills/work-breakdown
```
