#!/usr/bin/env python3
"""Build the vela plugin zip for claude.ai / Claude Cowork from the committed tree.

claude.ai-hosted plugins may not ship a top-level bin/ (it lands on PATH without appearing on the admin
approval surface). This lives in tools/, not in the plugin's CLI, because it needs the repo's git history
and a vendored copy inside a vault has neither. It reads git, never the working tree, so edits in
progress cannot ship.

    python3 tools/package_plugin.py --out ~/Desktop/vela-plugin.zip
    python3 tools/package_plugin.py --reader --out ~/Desktop/vela-reader.zip

`--reader` makes the slim plugin a director installs: five skills, the whole core (one set of rules, never a copy),
no planning sessions, no write guards, and the one-page setup beside the zip and inside it.
"""
import argparse
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ".claude-plugin/plugin.json"


READER_SKILLS = ("open", "ask", "find", "explore", "companion")  # the director reads; he never plans in vela
READER_NAME = "vela-reader"
READER_DESCRIPTION = ("Read a vela plan in plain words: open it from a GitHub link, ask about it, find things, see the "
                      "dashboard and the panel beside the chat. Nothing here changes the plan.")
READER_DROPS = ("bin/", "agents/")  # the reviewers serve planning sessions only
READER_HOOK_EVENTS = ("SessionStart", "UserPromptSubmit")  # the write guards protect nothing in a copy with no git
READER_HOOKS_DESCRIPTION = ("SessionStart leaves a marker so `vela where --probe` can tell whether hooks run here; "
                            "UserPromptSubmit logs what the person typed and, when the panel published to Cowork is "
                            "behind, tells Claude to republish it.")
COWORK_KEEPS_MODULES = False  # why: Cowork draws no mod and may refuse a hooks file with `modules` (plan ruling 18);
#                               set True only when the placement probe's Cowork row says the upload is accepted
DROPPED_MENTION_OK = {"skills/explore/ABOUT.md": "explains where a team's design comes from; a director never runs it"}
SETUP_SOURCE = "docs/director-setup.md"
SKILL_MENTION = re.compile(r"/vela:([a-z][a-z-]*)")


class PackageError(Exception):
    """The archive would be rejected by claude.ai, or could not be built."""


def excluded(name, reader=False):
    """What no zip ships: bin/, caches, and a mod's own tests. A reader zip also drops READER_DROPS and every skill
    folder that is not a reader skill."""
    parts = name.split("/")
    if parts[0] == "bin" or "__pycache__" in parts or name.endswith(".pyc"):
        return True
    if name.endswith((".test.ts", ".test.tsx")) or name.startswith("hooks/tests/"):
        return True
    if reader:
        if name.startswith(READER_DROPS):
            return True
        if parts[0] == "skills" and len(parts) > 1 and parts[1] not in READER_SKILLS:
            return True
    return False


def reader_rewrite(name, data):
    """A kept file as the reader plugin holds it: its own manifest and hooks, and every `/vela:<kept skill>` named as
    `/vela-reader:<kept skill>`, because a plugin's name prefixes its skills."""
    if name == MANIFEST:
        manifest = json.loads(data)
        manifest.update({"name": READER_NAME, "description": READER_DESCRIPTION})
        return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if name == "hooks/hooks.json":
        hooks = json.loads(data)
        hooks["hooks"] = {event: hooks["hooks"][event] for event in READER_HOOK_EVENTS}
        hooks.pop("modules", None)
        hooks["description"] = READER_HOOKS_DESCRIPTION
        return (json.dumps(hooks, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if name.endswith(".md"):
        kept = "|".join(READER_SKILLS)
        return re.sub(rf"/vela:({kept})\b", r"/vela-reader:\1", data.decode("utf-8")).encode("utf-8")
    return data


def cowork_hooks(data):
    """hooks.json as a Cowork zip holds it: without `modules` unless COWORK_KEEPS_MODULES."""
    if COWORK_KEEPS_MODULES:
        return data
    hooks = json.loads(data)
    hooks.pop("modules", None)
    return (json.dumps(hooks, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def content_of(member_name, data, reader):
    if reader:
        data = reader_rewrite(member_name, data)
    elif member_name == "hooks/hooks.json":
        data = cowork_hooks(data)
    return data


def dropped_mentions(out, repo=REPO):
    """[(file, line)] naming `/vela:<a skill the reader plugin doesn't have>` in a kept skill or the setup page, outside
    DROPPED_MENTION_OK and outside a line that says "full vela plugin": a command in a reader's skill that doesn't exist
    in its plugin is a dead end. `references/` and `template/` ship whole as the core and belong to the planning sessions;
    no reader skill offers anything from them."""
    dropped = {p.name for p in (repo / "plugin" / "skills").iterdir() if p.is_dir()} - set(READER_SKILLS)
    found = []
    with zipfile.ZipFile(out) as archive:
        for name in archive.namelist():
            if not name.endswith(".md") or name in DROPPED_MENTION_OK or not (name.startswith("skills/") or name == "SETUP.md"):
                continue
            for line in archive.read(name).decode("utf-8", errors="replace").splitlines():
                if "full vela plugin" in line:
                    continue
                if any(m.group(1) in dropped for m in SKILL_MENTION.finditer(line)):
                    found.append((name, line.strip()))
    return found


def committed_plugin_tar(repo, ref):
    done = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", f"{ref}:plugin"],
                          capture_output=True, timeout=60)
    if done.returncode != 0:
        raise PackageError(f"git archive {ref}:plugin failed: {done.stderr.decode(errors='replace').strip()}")
    return tarfile.open(fileobj=io.BytesIO(done.stdout))


def write_zip(tar, out, reader=False, extra=None):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        files = [m for m in sorted(tar.getmembers(), key=lambda m: m.name) if m.isfile() and not excluded(m.name, reader)]
        # Folder entries too (".claude-plugin/" before its manifest): Cowork's upload warned "The archive must contain a
        # .claude-plugin/plugin.json manifest" on a files-only zip that held it, while the plugin still installed.
        folders = sorted({"/".join(m.name.split("/")[:i]) + "/" for m in files for i in range(1, m.name.count("/") + 1)})
        for folder in folders:
            info = zipfile.ZipInfo(folder, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(info, b"")
        for member in files:
            info = zipfile.ZipInfo(member.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (member.mode & 0o777) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content_of(member.name, tar.extractfile(member).read(), reader))
        for name, data in sorted((extra or {}).items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)


def verify_layout(out):
    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
    if MANIFEST not in names:
        raise PackageError(f"{MANIFEST} is not at the archive root")
    forbidden = [n for n in names if excluded(n)]
    if forbidden:
        raise PackageError(f"archive holds entries claude.ai rejects: {forbidden[:3]}")
    tagged = tagged_descriptions(out, names)
    if tagged:
        raise PackageError("claude.ai rejects a skill description with anything that looks like an XML tag: "
                           + "; ".join(f"{name} has {tag}" for name, tag in tagged))
    return len(names)


DESCRIPTION = re.compile(r"^description:\s*(.*?)(?=^[A-Za-z][\w-]*:|\Z)", re.S | re.M)
TAG = re.compile(r"<[^<>\n]*>")


def tagged_descriptions(out, names):
    """[(SKILL.md path, first tag)] for each skill whose frontmatter description holds an angle-bracket span.
    claude.ai and Cowork read `<slug>` as an XML tag and refuse the whole upload, and claude plugin validate
    doesn't catch it, so the packager does."""
    found = []
    with zipfile.ZipFile(out) as archive:
        for name in names:
            if not name.endswith("SKILL.md"):
                continue
            text = archive.read(name).decode("utf-8", errors="replace")
            front = text.split("---", 2)[1] if text.startswith("---") else ""
            match = DESCRIPTION.search(front)
            tag = TAG.search(match.group(1)) if match else None
            if tag:
                found.append((name, tag.group(0)))
    return found


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


def committed_setup(repo, ref):
    done = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{SETUP_SOURCE}"], capture_output=True, timeout=60)
    if done.returncode != 0:
        raise PackageError(f"git show {ref}:{SETUP_SOURCE} failed: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout


def package(out, repo=REPO, ref="HEAD", say=print, reader=False):
    """Write the zip and return its entry count; raise PackageError if it would be rejected. With `reader`, the slim
    plugin, and the director's one-page setup both inside it (SETUP.md) and beside it."""
    setup = committed_setup(repo, ref) if reader else None
    with committed_plugin_tar(repo, ref) as tar:
        write_zip(tar, out, reader, {"SETUP.md": setup} if reader else None)
    if reader:
        out.with_name(f"{out.stem}-setup.md").write_bytes(setup)
    count = verify_layout(out)
    validate_with_claude(out, say)
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zip the committed plugin/ tree for claude.ai.")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="zip path (overwritten)")
    parser.add_argument("--ref", default="HEAD", help="commit to package (default: HEAD)")
    parser.add_argument("--reader", action="store_true", help="the slim plugin for a director: five skills and the setup page")
    args = parser.parse_args(argv)
    try:
        count = package(args.out.expanduser(), ref=args.ref, reader=args.reader)
    except PackageError as err:
        print(f"package_plugin: {err}", file=sys.stderr)
        return 1
    print(f"package_plugin: {args.out} written, {count} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
