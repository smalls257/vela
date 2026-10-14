"""`planner record`: reserved for the CLI/skill overhaul (docs/plans/2026-10-14-cli-skill-overhaul.md, Task 6b). Adds no
parser until that task gives it a subcommand, so `planner --help` never lists a command that does nothing."""


def register(sub):
    return None
