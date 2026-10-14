#!/usr/bin/env python3
"""Rewrite the `check-codes` block in all four CONVENTIONS.md copies from `schema.CODES`, so the table a person reads
is the table `vela check` uses. Run it after adding or rewording a code; `tests/test_conventions_cli.py` fails until
you do. `vela render` never touches CONVENTIONS.md (it is not a vault page), so this script is the block's renderer.

    python3 tools/conventions_codes.py          # rewrite the copies
    python3 tools/conventions_codes.py --check  # exit 1 if any copy is out of date, write nothing
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugin" / "lib"))

from vela import conventions  # noqa: E402

COPIES = ("template", "plugin/vault", "examples/unified-booking", "tests/stub-conventions")


def main(argv):
    check_only = argv == ["--check"]
    if argv and not check_only:
        print("Usage: python3 tools/conventions_codes.py [--check]", file=sys.stderr)
        return 2
    stale = []
    for folder in COPIES:
        path = REPO / folder / "CONVENTIONS.md"
        text = path.read_text(encoding="utf-8")
        try:
            new = conventions.with_codes_table(text)
        except conventions.NoCodesBlock as exc:
            print(f"conventions_codes: {path.relative_to(REPO)} has {exc}; add the markers under "
                  "\"## vela check and vela render\".", file=sys.stderr)
            return 2
        if new == text:
            continue
        stale.append(path.relative_to(REPO).as_posix())
        if not check_only:
            path.write_text(new, encoding="utf-8")
    verb = "out of date" if check_only else "rewritten"
    print(f"conventions_codes: {', '.join(stale)} {verb}." if stale else "conventions_codes: every copy is current.")
    return 1 if (check_only and stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
