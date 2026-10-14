#!/usr/bin/env python3
"""Print the five reading-load counts of a vault (design session 16, 16-D10), so a later run can be compared with an
earlier one. Read-only.

    python3 tools/voice_counts.py tests/sim/snapshots/heron-desk/after-design-2
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "plugin" / "lib"))

from vela import cli, readability, readload  # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("Give one vault folder: python3 tools/voice_counts.py <vault>", file=sys.stderr)
        return 2
    try:
        vault = cli.load_vault(pathlib.Path(argv[0]).resolve())
    except cli.ToolError as exc:
        print(f"voice_counts: {exc}", file=sys.stderr)
        return 2
    for name, number in readload.counts(vault, readability.criteria).items():
        print(f"{number:4d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
