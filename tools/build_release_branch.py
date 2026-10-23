#!/usr/bin/env python3
"""Build or update the lean `release` branch: what an install needs and nothing else.

Installing from a marketplace clones the whole repo, then copies plugin/ into the cache. The tests, sim
recordings and docs are most of that clone. The release branch holds only the marketplace manifest, plugin/ exactly
as committed at a source commit, LICENSE and a README, with one commit per release, so installs and updates download
about the plugin and nothing more. Everything is built with git plumbing and a temporary index: the working tree
and the checked-out branch are never touched, and nothing is pushed.

    python3 tools/build_release_branch.py --ref <commit> [--branch release]
    python3 tools/build_release_branch.py --check <release-commit>      # what the pre-push hook runs

plugin/bin/ stays: only the claude.ai/Cowork zip (tools/package_plugin.py) must drop it, and the CLI install
needs it for the `vela` command. __pycache__ and .pyc files are dropped.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

MARKETPLACE = ".claude-plugin/marketplace.json"
PLUGIN_MANIFEST = "plugin/.claude-plugin/plugin.json"
ALLOWED_TOP = {MARKETPLACE, "LICENSE", "README.md"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # the largest committed file is mermaid.min.js at about 3.2 MB; 5 MB leaves room, a recording does not fit
MARKETPLACE_ID = "smalls257/vela#release"

README = """# vela (release branch)

This branch is generated. Do not edit it and do not open pull requests against it. It holds only what an
install needs: the marketplace manifest, the plugin and the license. The source, docs and tests live on
`main` (github.com/smalls257/vela).

Install, in Claude Code:

1. `/plugin marketplace add {marketplace}`
2. `/plugin install vela@vela`
3. Ask Claude to run `vela doctor`.

Built from source commit {commit} (vela {version}).
"""


class ReleaseError(Exception):
    """The branch was not built, or the release tree is not acceptable. The message says why."""


def git(repo, *args, env=None, stdin=None, check=True):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=env, input=stdin, timeout=120)
    if check and done.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {done.stderr.decode(errors='replace').strip()}")
    return done


def text(repo, *args, **kw):
    return git(repo, *args, **kw).stdout.decode().strip()


def version_key(version):
    if not re.fullmatch(r"\d+(\.\d+)*", version):
        raise ReleaseError(f"version {version!r} is not dotted numbers")
    return tuple(int(part) for part in version.split("."))


def plugin_version(repo, commit):
    done = git(repo, "show", f"{commit}:{PLUGIN_MANIFEST}", check=False)
    if done.returncode != 0:
        raise ReleaseError(f"{commit[:9]} has no {PLUGIN_MANIFEST}")
    try:
        version = str(json.loads(done.stdout)["version"])
        version_key(version)
        return version
    except (ValueError, KeyError, ReleaseError) as err:
        raise ReleaseError(f"{PLUGIN_MANIFEST} at {commit[:9]} has no usable version: {err}")


def is_junk(path):
    parts = path.split("/")
    return "__pycache__" in parts or path.endswith(".pyc")


def check_marketplace(raw, where):
    try:
        manifest = json.loads(raw)
        plugins = manifest["plugins"]
    except (ValueError, KeyError) as err:
        raise ReleaseError(f"{MARKETPLACE} at {where} does not parse as a marketplace: {err}")
    if [(p.get("name"), p.get("source")) for p in plugins] != [("vela", "./plugin")]:
        raise ReleaseError(f"{MARKETPLACE} at {where} must name exactly the plugin vela with source ./plugin")


def check_release_tree(repo, commit):
    """Everything the pre-push hook enforces about a release commit; raises ReleaseError on the first failure."""
    listing = text(repo, "ls-tree", "-r", "-l", "--full-tree", commit)
    present = set()
    for line in listing.splitlines():
        meta, path = line.split("\t", 1)
        size = int(meta.split()[3])
        present.add(path)
        if path not in ALLOWED_TOP and not path.startswith("plugin/"):
            raise ReleaseError(f"{path} is not allowed on the release branch (only {', '.join(sorted(ALLOWED_TOP))} and plugin/)")
        if is_junk(path):
            raise ReleaseError(f"{path} is a bytecode cache and must not ship")
        if size > MAX_FILE_BYTES:
            raise ReleaseError(f"{path} is {size / 1048576:.1f} MB, over the {MAX_FILE_BYTES // 1048576} MB per-file limit")
    for required in sorted(ALLOWED_TOP | {PLUGIN_MANIFEST}):
        if required not in present:
            raise ReleaseError(f"{required} is missing from the release tree")
    check_marketplace(git(repo, "show", f"{commit}:{MARKETPLACE}").stdout, commit[:9])
    version = plugin_version(repo, commit)
    parents = text(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
    if parents:
        before = plugin_version(repo, parents[0])
        if version_key(version) <= version_key(before):
            raise ReleaseError(f"version {version} is not greater than the previous release {before}; bump plugin.json first")
    return version


def checked_out_elsewhere(repo, ref_name):
    out = text(repo, "worktree", "list", "--porcelain")
    return any(line == f"branch {ref_name}" for line in out.splitlines())


def build(repo, ref, branch="release"):
    """Add one commit for <ref> to <branch>; return (commit, version). Working tree and index are never touched."""
    commit = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).stdout.decode().strip()
    if not commit:
        raise ReleaseError(f"{ref} is not a committed ref in this repo; commit first, then build from the commit")
    version = plugin_version(repo, commit)
    ref_name = f"refs/heads/{branch}"
    if checked_out_elsewhere(repo, ref_name):
        raise ReleaseError(f"{branch} is checked out in a worktree; building would leave it out of date")
    previous = git(repo, "rev-parse", "--verify", "--quiet", ref_name, check=False).stdout.decode().strip()
    if previous:
        before = plugin_version(repo, previous)
        if version_key(version) == version_key(before):
            raise ReleaseError(f"{branch} is already at vela {before}; nothing to release. Bump plugin/.claude-plugin/plugin.json and commit first")
        if version_key(version) < version_key(before):
            raise ReleaseError(f"{commit[:9]} is vela {version}, older than {branch} at {before}; refusing to go backwards")
    marketplace = git(repo, "show", f"{commit}:{MARKETPLACE}").stdout
    check_marketplace(marketplace, commit[:9])
    with tempfile.TemporaryDirectory() as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(scratch) / "index")}
        git(repo, "read-tree", "--prefix=plugin/", f"{commit}:plugin", env=env)
        junk = [p for p in text(repo, "ls-files", env=env).splitlines() if is_junk(p)]
        for path in junk:
            git(repo, "update-index", "--force-remove", path, env=env)
        extras = {MARKETPLACE: marketplace, "LICENSE": git(repo, "show", f"{commit}:LICENSE").stdout,
                  "README.md": README.format(marketplace=MARKETPLACE_ID, commit=commit[:9], version=version).encode()}
        for path, data in extras.items():
            blob = text(repo, "hash-object", "-w", "--stdin", stdin=data)
            git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = text(repo, "write-tree", env=env)
    message = f"vela {version}, built from source commit {commit[:9]}"
    parent = ["-p", previous] if previous else []
    new = text(repo, "commit-tree", tree, *parent, "-m", message)
    check_release_tree(repo, new)
    git(repo, "update-ref", "-m", message, ref_name, new, previous or "0" * 40)
    return new, version


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ref", help="the source commit to release")
    parser.add_argument("--branch", default="release")
    parser.add_argument("--check", metavar="COMMIT", help="check a release commit as the pre-push hook does")
    parser.add_argument("--repo", default=".", help="the repo to work in (default: the current directory)")
    args = parser.parse_args(argv)
    try:
        if args.check:
            version = check_release_tree(args.repo, args.check)
            print(f"release check: ok, vela {version}")
        elif args.ref:
            new, version = build(args.repo, args.ref, args.branch)
            print(f"{args.branch}: vela {version} at {new[:9]}. Nothing was pushed.")
        else:
            parser.error("give --ref <commit> or --check <commit>")
    except ReleaseError as err:
        print(f"build_release_branch: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
