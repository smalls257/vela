"""`vela hook`: reserved for the CLI/skill overhaul (docs/plans/2026-10-14-cli-skill-overhaul.md, Tasks 7 and 24). Adds no
parser until that task gives it a subcommand, so `vela --help` never lists a command that does nothing."""


def register(sub):
    return None
