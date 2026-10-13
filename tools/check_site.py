#!/usr/bin/env python3
"""Check a built example site before it is published to GitHub Pages, where anyone with the link can read it.

The Violation to prevent is a leak nobody sees until a stranger does (Black Box): a path under the builder's home,
the builder's git name or email, a token, or a page that loads from outside. The site branch holds no code, so the
pre-push hook runs this on it instead of the gate. Exit 0 when clean; exit 1 and one line per finding otherwise.

Usage: python3 tools/check_site.py <site-folder> [--forbid TEXT ...]
"""
import argparse
import pathlib
import re
import sys

ALLOWED_SUFFIXES = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".ico", ".txt"}
ALLOWED_NAMES = {".nojekyll", "CNAME"}
SECRETS = re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}"
                     r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,}|https?://[^/\s\"']+:[^@/\s\"']+@")
LOCAL_PATHS = re.compile(r"(?<![\w.])(?:/Users/|/home/|/private/(?:tmp|var)/|[A-Z]:\\\\Users\\\\)")
EXTERNAL_LOAD = re.compile(r"<(?:script|link|img|iframe|source|video|audio)\b[^>]*\b(?:src|href)\s*=\s*[\"']?(?:https?:)?//", re.I)
CSS_IMPORT = re.compile(r"(?:@import|url\()\s*[\"']?(?:https?:)?//", re.I)


def findings(site, forbidden):
    """(relative path, what is wrong) for every problem in the site folder."""
    for path in sorted(p for p in site.rglob("*") if p.is_file()):
        name = path.relative_to(site).as_posix()
        if ".git" in path.relative_to(site).parts:
            continue
        if path.name not in ALLOWED_NAMES and path.suffix.lower() not in ALLOWED_SUFFIXES:
            yield name, f"'{path.suffix or path.name}' files are not part of a built site; publish only the pages"
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        for pattern, why in ((SECRETS, "looks like a credential"), (LOCAL_PATHS, "names a folder on the builder's machine"),
                             (EXTERNAL_LOAD, "loads something from another site"), (CSS_IMPORT, "loads a style from another site")):
            match = pattern.search(text)
            if match:
                yield name, f"{why}: {match.group(0)[:60]!r}"
        for word in forbidden:
            if word and word.lower() in text.lower():
                yield name, f"contains {word!r}, which was named as private"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site", type=pathlib.Path)
    parser.add_argument("--forbid", action="append", default=[], help="text that must not appear, such as a name or email")
    args = parser.parse_args(argv)
    if not args.site.is_dir():
        print(f"check_site: {args.site} is not a folder", file=sys.stderr)
        return 2
    problems = list(findings(args.site, args.forbid))
    for name, why in problems:
        print(f"check_site: {name}: {why}", file=sys.stderr)
    if not any(args.site.glob("*.html")):
        print("check_site: the folder holds no .html page", file=sys.stderr)
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
