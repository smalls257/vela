#!/usr/bin/env python3
"""Build the vault explorer for the tests. The builder lives in the plugin (plugin/lib/vela/explorer); `vela explore`
is how a vault's user runs it. This wrapper adds what only the tests need: a new pins file is seeded from seed-pins/
by the same name, so layouts that were placed by hand stay put, and --assets takes any assets.config.json.

    python3 tests/fixtures/explorer/build.py <vault> <out.html> [--today YYYY-MM-DD] [--pins <name>.json]
                                             [--assets <folder>/assets.config.json]
                                         [--theme console|graphite|daylight|vaporwave]
                                         [--design APP-x=<team repo>/docs/tech-design/<slug>.md ...]
                                         [--breakdown APP-x=<team repo>/docs/plan/<slug>-breakdown.md ...]
"""
import argparse
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "plugin" / "lib"))

from vela.explorer import build  # noqa: E402

SEED_PINS = HERE / "seed-pins"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("vault", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--today", help="the date due windows count from, YYYY-MM-DD (default: the system date)")
    parser.add_argument("--pins", type=pathlib.Path,
                        help="the pinned positions file, started from seed-pins/ of the same name (default: "
                             "computed in memory and not kept)")
    parser.add_argument("--assets", type=pathlib.Path,
                        help="an assets.config.json; its provider's files are inlined (default: builtin only)")
    parser.add_argument("--design", action="append", default=[], metavar="APP-x=PATH",
                        help="a team's tech design doc for an app, for Inside this app; repeat for each app")
    parser.add_argument("--breakdown", action="append", default=[], metavar="APP-x=PATH",
                        help="a team's work breakdown for an app, for its Build plan; repeat for each app")
    parser.add_argument("--theme", choices=build.THEME_IDS, default=build.THEME_IDS[0],
                        help=f"the theme the page opens in until the reader picks another (default: {build.THEME_IDS[0]})")
    parser.add_argument("--selftest", action="store_true", help="bundle the page's own checks, for #selftest (default: left out)")
    args = parser.parse_args(argv)
    today = args.today or datetime.date.today().isoformat()
    seed = SEED_PINS / args.pins.name if args.pins else None
    try:
        lines = build.generate(args.vault, args.out, today, pins_path=args.pins, seed=seed, assets_config=args.assets,
                               design_args=args.design, theme=args.theme, breakdown_args=args.breakdown, selftest=args.selftest)
    except build.ExplorerError as exc:
        print(f"build.py: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(f"build.py: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
