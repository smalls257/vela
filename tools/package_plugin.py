#!/usr/bin/env python3
"""Build the planner plugin zip for claude.ai / Claude Cowork from the committed tree.

claude.ai-hosted plugins may not ship a top-level bin/ (it lands on PATH without appearing on the admin
approval surface). This lives in tools/, not in the plugin's CLI, because it needs the repo's git history
and a vendored copy inside a vault has neither. It reads git, never the working tree, so edits in
progress cannot ship.

    python3 tools/package_plugin.py --out ~/Desktop/planner-plugin.zip
"""
import argparse
import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ".claude-plugin/plugin.json"


class PackageError(Exception):
    """The archive would be rejected by claude.ai, or could not be built."""


def excluded(name):
    parts = name.split("/")
    return parts[0] == "bin" or "__pycache__" in parts or name.endswith(".pyc")


def committed_plugin_tar(repo, ref):
    done = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", f"{ref}:plugin"],
                          capture_output=True, timeout=60)
    if done.returncode != 0:
        raise PackageError(f"git archive {ref}:plugin failed: {done.stderr.decode(errors='replace').strip()}")
    return tarfile.open(fileobj=io.BytesIO(done.stdout))


def write_zip(tar, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for member in sorted(tar.getmembers(), key=lambda m: m.name):
            if not member.isfile() or excluded(member.name):
                continue
            info = zipfile.ZipInfo(member.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (member.mode & 0o777) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, tar.extractfile(member).read())


def verify_layout(out):
    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
    if MANIFEST not in names:
        raise PackageError(f"{MANIFEST} is not at the archive root")
    forbidden = [n for n in names if excluded(n)]
    if forbidden:
        raise PackageError(f"archive holds entries claude.ai rejects: {forbidden[:3]}")
    return len(names)


def validate_with_claude(out, say):
    claude = shutil.which("claude")
    if claude is None:
        say("claude not found on PATH: skipped `claude plugin validate`")
        return
    with tempfile.TemporaryDirectory() as unpacked:
        with zipfile.ZipFile(out) as archive:
            archive.extractall(unpacked)
        try:
            done = subprocess.run([claude, "plugin", "validate", unpacked], capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired as exc:
            raise PackageError(f"claude plugin validate timed out after 300s") from exc
    if done.returncode != 0:
        raise PackageError(f"claude plugin validate failed:\n{done.stdout}{done.stderr}")
    say("claude plugin validate passed")


def package(out, repo=REPO, ref="HEAD", say=print):
    """Write the zip and return its entry count; raise PackageError if it would be rejected."""
    with committed_plugin_tar(repo, ref) as tar:
        write_zip(tar, out)
    count = verify_layout(out)
    validate_with_claude(out, say)
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zip the committed plugin/ tree for claude.ai.")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="zip path (overwritten)")
    parser.add_argument("--ref", default="HEAD", help="commit to package (default: HEAD)")
    args = parser.parse_args(argv)
    try:
        count = package(args.out.expanduser(), ref=args.ref)
    except PackageError as err:
        print(f"package_plugin: {err}", file=sys.stderr)
        return 1
    print(f"package_plugin: {args.out} written, {count} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
