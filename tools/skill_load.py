"""Words a session loads before its first question, per mode (overhaul plan 8.1, "Load measure").

    python3 tools/skill_load.py grill            # the working tree
    python3 tools/skill_load.py grill --rev bcddf6a   # as of a commit

A mode session reads START, MODES, CONVERSATION-VOICE, REVIEW and its own SKILL.md before it asks anything. Each of
those that cites CONVENTIONS.md the old way ("as `CONVENTIONS.md` says under ...", "The format is `CONVENTIONS.md`")
sends the model to the whole 21,000-word file, so it is counted whole, once. A cite through
`vela conventions "<section>"` costs only that section. The number must not rise across a skill rewrite; a thinner
session makes it fall too, so this is a sensor for load, not for detail (the paid run measures detail).
"""
import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugin" / "lib"))

SHARED = ("plugin/references/START.md", "plugin/references/MODES.md", "plugin/references/CONVERSATION-VOICE.md",
          "plugin/references/REVIEW.md")
CONVENTIONS = "plugin/vault/CONVENTIONS.md"
OLD_CITE = re.compile(r'`CONVENTIONS\.md`(?: (?:says|defines it|gives|shows))? under "|`CONVENTIONS\.md`, "|'
                      r'" in `CONVENTIONS\.md`|The (?:page )?formats? (?:is|are) `CONVENTIONS\.md`')
NEW_CITE = re.compile(r'`vela conventions "([^"<]+)"`')


def read(path, rev):
    if rev is None:
        return (REPO / path).read_text(encoding="utf-8")
    done = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"], capture_output=True, text=True, timeout=30)
    if done.returncode != 0:
        raise SystemExit(f"skill_load: git cannot show {path} at {rev}: {done.stderr.strip()}")
    return done.stdout


def words(text):
    return len(text.split())


def section_words(conventions_text, name):
    from vela import conventions
    found = conventions.section(conventions.sections(conventions_text), name)
    if found is None:
        raise SystemExit(f"skill_load: a skill cites the section {name!r}, which CONVENTIONS.md does not have")
    return found.words


def measure(mode, rev=None):
    """{"files": {path: words}, "conventions": words, "conventions_how": str, "total": words}."""
    paths = list(SHARED) + [f"plugin/skills/{mode}/SKILL.md"]
    texts = {p: read(p, rev) for p in paths}
    files = {p: words(t) for p, t in texts.items()}
    joined = "\n".join(texts.values())
    rules = read(CONVENTIONS, rev)
    if OLD_CITE.search(joined):
        cost, how = words(rules), "whole file (an old-style cite sends the model to it)"
    else:
        names = sorted(set(NEW_CITE.findall(joined)))
        cost, how = sum(section_words(rules, n) for n in names), f"{len(names)} sections: {', '.join(names)}"
    return {"files": files, "conventions": cost, "conventions_how": how, "total": sum(files.values()) + cost}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mode", help="a mode skill, such as grill or close")
    parser.add_argument("--rev", help="a commit to measure instead of the working tree")
    args = parser.parse_args(argv)
    found = measure(args.mode, args.rev)
    for path, n in found["files"].items():
        print(f"{n:>6}  {path}")
    print(f"{found['conventions']:>6}  CONVENTIONS.md, {found['conventions_how']}")
    print(f"{found['total']:>6}  words before the first question ({args.mode}{', ' + args.rev if args.rev else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
