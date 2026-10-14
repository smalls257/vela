"""`vela reviewers`: reserved for the CLI/skill overhaul (docs/plans/2026-10-14-cli-skill-overhaul.md, Task 20). Adds no
parser until that task gives it a subcommand, so `vela --help` never lists a command that does nothing."""


def register(sub):
    return None
