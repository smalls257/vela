"""The one rule for anything that arrives from someone else: a published copy, a proposal, a patch, a received vault. Pure: no disk, clock or network.

The Violation this exists to prevent is a Distributed Monolith at the trust boundary. Open, proposal build, proposal
review, view and the Ask helper each used to carry their own idea of a dangerous path, so every new executable
location (.husky/, .mcp.json, a patch's rename header) passed whichever door nobody had patched yet. Now every door
asks this module, and the list lives here once.

Three verdicts for a path:
- ok: a page, a source, the stamp, the pinned layout.
- program: something a tool would run or obey (.claude/settings.json, .githooks/, .github/workflows, bin/, .mcp.json,
  .obsidian plugins). A reader has no use for it, so opening a copy leaves it out and says so; a proposal never carries it.
- forbidden: git's own folder, the planner's private folders, a symlink, a name that escapes. Nothing is opened or applied
  when one is present, and the message names the file.

What the stamp's tree_hash does and does not do (Paper Tiger if read as security): it is a plain sha256 over the files,
stored in the same archive. It catches an accidental edit or a half-copied folder. Whoever changed a file can recompute
it, so it says nothing about who sent the copy and nothing is trusted because it matches. Safety comes from the rules here.

edge/copies.py and edge/proposals.py read archives and call these; review.py calls the patch rules.
"""
import re
import stat

from planner import publish

MAX_ENTRIES = 20_000
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_PATCH_BYTES = 8 * 1024 * 1024

OK, PROGRAM, FORBIDDEN = "ok", "program", "forbidden"

# Hidden files a published copy legitimately carries and a reader's tools read.
HIDDEN_OK = {".planner.yaml", ".gitignore", publish.STAMP_PATH, ".planner/explorer-pins.json"}
PROGRAM_FOLDERS = {"bin"}
PROGRAM_SUFFIXES = (".sh", ".bash", ".zsh", ".command", ".bat", ".cmd", ".ps1", ".exe", ".dll", ".scr", ".vbs", ".jar", ".msi", ".app")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class Refused(Exception):
    """Input that must not be opened or applied. `path` is the file at fault; the message says why, in plain words."""

    def __init__(self, path, message):
        super().__init__(message)
        self.path = path


def _segment(part):
    """A path part as git and Windows see it: case-folded, without trailing dots or spaces, without a ':stream' suffix."""
    return part.split(":", 1)[0].casefold().rstrip(" .")


def verdict(path):
    """(OK | PROGRAM | FORBIDDEN, why) for one vault-relative path from outside. Names that escape the folder are FORBIDDEN."""
    try:
        publish.check_name(path)
    except publish.PublishError as exc:
        return FORBIDDEN, f"its name would write outside the workspace ({str(exc).rstrip('.')})"
    if CONTROL.search(path):
        return FORBIDDEN, "its name holds a control character"
    parts = path.split("/")
    if any(part in ("", ".") for part in parts):
        return FORBIDDEN, "its name has an empty or '.' part"
    segments = [_segment(part) for part in parts]
    if any(seg in (".git", "git~1") for seg in segments):
        return FORBIDDEN, "it is inside git's own folder, which can run commands (fsmonitor, hooks) the next time git is used there"
    lowered = path.casefold()
    if lowered == publish.STAMP_PATH:
        return OK, ""
    if lowered in {kept.casefold() for kept in publish.KEPT}:
        return OK, ""
    private = next((prefix for prefix in publish.EXCLUDED if lowered == prefix.rstrip("/").casefold() or lowered.startswith(prefix.casefold())), None)
    if private:
        return FORBIDDEN, f"a published copy never holds {private} (it is the planner's own, private or generated); this one was not made by planner publish"
    if lowered in {name.casefold() for name in HIDDEN_OK}:
        return OK, ""
    if any(seg.startswith(".") for seg in segments):
        return PROGRAM, "it is a hidden tool or settings file (hooks, workflows, editor plugins and Claude settings live in these)"
    if segments[0] in PROGRAM_FOLDERS or segments[-1].endswith(PROGRAM_SUFFIXES):
        return PROGRAM, "it is a program or script"
    return OK, ""


def check_proposal_path(path):
    """A path a proposal may carry: pages and sources only. Refused, not dropped: the sender must hear it."""
    kind, why = verdict(path)
    if kind != OK:
        raise Refused(path, f"'{path}' cannot be part of a proposal: {why}. A proposal carries pages only.")
    return path


def split_for_open(names):
    """(names to write, [(name, why)] left out) for a received copy. Any forbidden name refuses the whole copy, naming it."""
    keep, left_out = [], []
    for name in names:
        kind, why = verdict(name)
        if kind == FORBIDDEN:
            raise Refused(name, f"I did not open this copy: '{name}' is in it, and {why}.")
        (keep if kind == OK else left_out).append(name if kind == OK else (name, why))
    return keep, left_out


def left_out_line(left_out):
    """One plain line telling a reader what their copy leaves out and why; "" when nothing was left out."""
    if not left_out:
        return ""
    shown = ", ".join(name for name, _ in left_out[:4])
    more = f" and {len(left_out) - 4} more" if len(left_out) > 4 else ""
    return (f"Left out of your copy, because a reader has no use for tools that run commands: {shown}{more}. "
            "The owner's pages are all here.")


def check_entries(entries):
    """Refuse an archive by its table of contents, before any byte is read.

    `entries` are zipfile.ZipInfo-like objects: filename, file_size, external_attr, create_system, flag_bits.
    Limits stop a zip bomb (Python hands back at most the declared size, so the declared size is the cap)."""
    if len(entries) > MAX_ENTRIES:
        raise Refused("", f"the archive holds {len(entries)} entries; the most I will open is {MAX_ENTRIES}.")
    seen, total = {}, 0
    for info in entries:
        name = info.filename
        if info.flag_bits & 0x1:
            raise Refused(name, f"'{name}' is password-protected, so I cannot read it.")
        kind = stat.S_IFMT((info.external_attr >> 16) if info.create_system == 3 else 0)  # 0 when the writer set permissions only (ours does)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise Refused(name, f"'{name}' is a {'symbolic link' if kind == stat.S_IFLNK else 'special file'}, which can point at files outside the folder. I did not open this archive.")
        if info.file_size > MAX_FILE_BYTES:
            raise Refused(name, f"'{name}' unpacks to {info.file_size // (1024 * 1024)} MB; the most I will open for one file is {MAX_FILE_BYTES // (1024 * 1024)} MB.")
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise Refused(name, f"the archive unpacks to more than {MAX_TOTAL_BYTES // (1024 * 1024)} MB (stopped at '{name}'); I did not open it.")
        key = name.casefold().rstrip("/")
        if key in seen:
            raise Refused(name, f"'{name}' appears twice in the archive (as '{seen[key]}' too), so which one wins would depend on the tool that unpacks it.")
        seen[key] = name


def link_refusal(path):
    """The Refused for a symbolic link found on disk (a received folder, or a vault about to be read or served)."""
    return Refused(path, f"'{path}' is a symbolic link. It can point at files outside the vault (a key, a password file), "
                         "so I will not read or serve this vault until the link is replaced by a real file.")


# ------------------------------------------------------------------ patches

_SHA = r"[0-9a-f]{40}"
_INDEX = re.compile(rf"^index {_SHA}\.\.{_SHA}(?: 100644)?$")


def check_patch_head(path, head_lines):
    """Refuse any header a proposal patch should not carry. git honors more than the `diff --git` line: rename, copy,
    mode and symlink headers move or create files the path check never saw. Only what this tool writes is allowed."""
    allowed_exact = {f"diff --git a/{path} b/{path}", "new file mode 100644", "deleted file mode 100644"}
    named = {f"--- a/{path}", f"+++ b/{path}", "--- /dev/null", "+++ /dev/null"}
    for raw in head_lines:
        line = raw.rstrip("\n")
        if line in allowed_exact or _INDEX.match(line) or line.rstrip("\t") in named:
            continue
        raise Refused(path, f"{path}: the patch header '{line[:80]}' is not one this tool writes. Renames, copies, mode changes and links can "
                            "create files the path check never saw, so I did not read this proposal.")


def check_applied(entries, prefix):
    """After git applied a patch in a scratch worktree: refuse anything that is not a plain page. `entries` are
    (status, new_mode, path) from `git diff --raw`; `prefix` is the vault's folder inside the repo ("" for the root).
    This is the net under check_patch_head: git, not our parser, decides what a patch really did."""
    for status, mode, path in entries:
        rel = path[len(prefix):] if prefix and path.startswith(prefix) else path
        if prefix and not path.startswith(prefix):
            raise Refused(path, f"the patch changed '{path}', outside the vault folder.")
        if status != "D" and mode not in ("100644", "000000"):
            raise Refused(rel, f"the patch gives '{rel}' file mode {mode} (a link, a program or a submodule), which a proposal never does.")
        check_proposal_path(rel)
