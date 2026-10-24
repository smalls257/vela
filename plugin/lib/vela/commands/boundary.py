"""`vela boundary cover --cut FILE`: per proposed cut, the requirements one app carries whole, the ones split across
apps (so the crossing needs a contract), and the ones no app carries (CLI/skill overhaul, Task 21g).

Why: boundary tests each of its cuts against the functional requirements. That test is a count, and
counted by hand over every capability page it came out wrong and reached the lead full of IDs. The count is here;
which cut to pick, and whether a split is worth its contract, stays with the lead and the skill.

The file's shape is in `vela.boundarycover`'s docstring and in `vela boundary cover --help`. Exit 0 with the three
lists per cut (a split or an uncarried requirement is a cost to weigh, not a refusal); 1 the vault has no functional
requirements yet, with a plain reason; 2 the tool failed, or the cut file is missing or does not validate. The model
wrote the cut file, so a bad one is the model's to fix (exit 2 with the reason), never a refusal the lead hears with
a path and a parser error in it (voice audit row 211).

Reads only: it writes nothing, so it runs the same in a reader copy.
"""
import argparse
import pathlib

from vela import allocation, boundarycover, say
from vela.commands import emit

CUT_HELP = """The cut file (JSON, version 1), one entry per cut:

  {"version": 1,
   "cuts": [
     {"name": "One desktop agent",
      "apps": [
        {"name": "Desktop agent", "change": "new", "carries": ["CAP-001", "CAP-002.FR1"]},
        {"app": "APP-consent-and-identity", "change": "integrated", "carries": ["CAP-005.FR1"]}]}]}

An app the vault does not have yet is named in words ("name"); one it has is named by its ID ("app") and said by its
title. "carries" lists capabilities (every requirement under one) and single requirements. "change" is optional.
Cut and app names are said to the lead, so they are words with no ID in them.

Per cut it lists each requirement carried whole by one app, split across apps (the crossing needs a contract), or
carried by no app, after the cuts side by side. Exit 0 listed; 1 the vault has no requirements to test (plain
reason); 2 the tool failed, or the cut file is missing or not valid (the reason says what to fix)."""


def register(sub):
    boundary = sub.add_parser("boundary", help="test proposed cuts of a direction into apps")
    each = boundary.add_subparsers(dest="step", required=True)
    parser = each.add_parser("cover", help="per cut, the requirements carried whole, split across apps, or by no app",
                             description=CUT_HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cut", required=True, metavar="FILE", help="the cut file (JSON, version 1; shape above)")
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(parser)
    parser.set_defaults(func=cmd_cover)


def refused(plain, fix):
    return say.Result("boundary cover", exit=say.REFUSED,
                      refusals=[say.Refusal("cut file", plain, fix, "Nothing to override: this command only counts.")])


def cmd_cover(args, out):
    from vela import cli  # loads the vault; imported here as every command module does
    vault = cli.load_vault(pathlib.Path(args.vault))
    resolver = say.Resolver(vault)
    names = {r.id: r.name or r.id for r in allocation.requirements(vault)}
    if not names:
        result = refused("The vault has no functional requirements yet, so there is nothing to test the cuts against.",
                         "Offer /vela:requirements first, then test the cuts.")
        return emit(result, args, out, resolver)
    path = pathlib.Path(args.cut)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise cli.ToolError(f"there is no cut file at {path}: write it, then run this again.") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise cli.ToolError(f"cannot read {path}: {exc}") from exc
    apps = {app.id: vault.name_of(app.id) for app in vault.apps}
    try:
        cuts = boundarycover.parse_cut(text, names, apps)
    except boundarycover.CutError as exc:
        raise cli.ToolError(f"{path}: {exc.plain} {exc.fix}") from exc
    coverages = boundarycover.cover(cuts, list(names))
    result = say.Result("boundary cover", lines=boundarycover.lines(coverages, names),
                        data={"cuts": [c.as_json(names) for c in coverages]})
    return emit(result, args, out, resolver)
