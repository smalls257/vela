"""Writing and reading published copies and reader workspaces on disk (the periphery for publish and freshness).

Every failure to read or write names the path and the reason. A source that is simply not there is
SourceUnreachable, which freshness reports as a state; one that is there but is not a published copy is
SourceUnreadable, which freshness reports as `unknown` with the reason.
"""
import json
import os
import pathlib
import shutil
import zipfile

from planner import opening, publish, replay

WORKSPACE = pathlib.Path(".planner") / "workspace.json"
STAMP = pathlib.PurePosixPath(publish.STAMP_PATH)


class SourceUnreachable(Exception):
    """The folder or zip a copy was opened from cannot be reached (moved, offline OneDrive)."""


class SourceUnreadable(Exception):
    """The source is reachable but holds no readable published stamp."""


def write_folder(files, out, executable=()):
    """Write the files into `out`, which must not exist or must be empty. Names were validated by publish."""
    out = pathlib.Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise publish.PublishError(f"{out} already exists and is not empty. Publish to a new folder, or to a .zip.")
    for path, data in files.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if path in executable:
            target.chmod(0o755)


def write_zip(data, out):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def read_workspace(root):
    """The reader workspace's .planner/workspace.json as a dict; SourceUnreadable names what is wrong with it."""
    path = pathlib.Path(root) / WORKSPACE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceUnreadable(f"{path} cannot be read: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceUnreadable(f"{path} is not a JSON object.")
    return data


def _stamp_from_text(text, where):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceUnreadable(f"the stamp in {where} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "commit" not in data:
        raise SourceUnreadable(f"the stamp in {where} has no commit.")
    return data


def _folder_stamp(source):
    """The stamp in a published folder, at its root or one folder down (an unzipped copy keeps its top folder)."""
    for base in [source, *sorted(p for p in source.iterdir() if p.is_dir())]:
        candidate = base / STAMP
        if candidate.is_file():
            try:
                return _stamp_from_text(candidate.read_text(encoding="utf-8"), str(candidate))
            except (OSError, UnicodeDecodeError) as exc:
                raise SourceUnreachable(f"{candidate} cannot be read: {exc}") from exc
    raise SourceUnreadable(f"{source} holds no {publish.STAMP_PATH}, so it is not a published copy.")


def _zip_stamp(source):
    try:
        with zipfile.ZipFile(source) as archive:
            for name in archive.namelist():
                parts = name.split("/")
                if name.endswith(publish.STAMP_PATH) and len(parts) <= 3 and parts[-2:] == [".planner", "published.json"]:
                    return _stamp_from_text(archive.read(name).decode("utf-8"), f"{source}:{name}")
    except zipfile.BadZipFile as exc:
        raise SourceUnreadable(f"{source} is not a readable zip: {exc}") from exc
    except OSError as exc:
        raise SourceUnreachable(f"{source} cannot be read: {exc}") from exc
    raise SourceUnreadable(f"{source} holds no {publish.STAMP_PATH}, so it is not a published copy.")


def read_source_stamp(source_path):
    """The published.json at the folder or zip a workspace was opened from. For a zip, only that one entry is read."""
    source = pathlib.Path(source_path).expanduser()
    if not source.exists():
        raise SourceUnreachable(f"{source} does not exist")
    try:
        if source.is_dir():
            return _folder_stamp(source)
        return _zip_stamp(source)
    except OSError as exc:
        raise SourceUnreachable(f"{source} cannot be read: {exc}") from exc


def read_own_stamp(root):
    """The stamp of a reader's own copy (for naming the owner in a refusal), or None when it has none."""
    path = pathlib.Path(root) / STAMP
    if not path.is_file():
        return None
    try:
        return _stamp_from_text(path.read_text(encoding="utf-8"), str(path))
    except (OSError, UnicodeDecodeError, SourceUnreadable) as exc:
        raise SourceUnreadable(f"{path} cannot be read: {exc}") from exc


def _read_zip_files(source):
    """{name: bytes} of a published zip with its one top folder removed. Names are validated before any byte is read."""
    try:
        with zipfile.ZipFile(source) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            opening.check_names(names)
            tops = {n.split("/", 1)[0] for n in names}
            nested = len(tops) == 1 and all("/" in n for n in names) and f"{next(iter(tops))}/{publish.STAMP_PATH}" in names
            strip = len(next(iter(tops))) + 1 if nested else 0
            return {n[strip:]: archive.read(n) for n in names}
    except zipfile.BadZipFile as exc:
        raise opening.OpenError(f"{source} is not a readable zip: {exc}") from exc
    except OSError as exc:
        raise opening.OpenError(f"{source} cannot be read: {exc}") from exc


def _published_root(source):
    for base in [source, *sorted(p for p in source.iterdir() if p.is_dir())]:
        if (base / STAMP).is_file():
            return base
    raise opening.OpenError(f"{source} holds no {publish.STAMP_PATH}, so it is not a published copy.")


def _read_folder_files(source):
    base = _published_root(source)
    files = {}
    try:
        for path in sorted(base.rglob("*")):
            if path.is_file() and not path.is_symlink():
                files[path.relative_to(base).as_posix()] = path.read_bytes()
    except OSError as exc:
        raise opening.OpenError(f"{source} cannot be read: {exc}") from exc
    return files


def read_published(source_path):
    """(files, stamp) of a published folder or zip. Reads only; the source is never written, renamed or locked."""
    source = pathlib.Path(source_path).expanduser()
    if not source.exists():
        raise opening.OpenError(f"{source} does not exist.")
    files = _read_folder_files(source) if source.is_dir() else _read_zip_files(source)
    if publish.STAMP_PATH not in files:
        raise opening.OpenError(f"{source} holds no {publish.STAMP_PATH}, so it is not a published copy.")
    stamp = _stamp_from_text(files[publish.STAMP_PATH].decode("utf-8", "replace"), f"{source}")
    for key in ("initiative", "title", "short", "date"):
        if not stamp.get(key):
            raise opening.OpenError(f"the stamp in {source} has no {key}.")
    return files, stamp


BASELINE = pathlib.Path(".planner") / "baseline"


def read_tree(folder, skip_published=False):
    """{vault-relative path: bytes} of every file under `folder`. With skip_published the generated and private
    parts a publish leaves out (.planner/, .git/, voice/local/, the vendored plugin), OS junk and a replay's saved
    sides of a conflict (`page.mine.md`) are skipped too,
    so a working copy is compared with its baseline on the same footing. An unreadable file raises OpenError."""
    folder = pathlib.Path(folder)
    files = {}
    try:
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(folder).as_posix()
            if skip_published and (publish.is_excluded(rel) or opening.is_junk(rel) or replay.is_mine_file(rel)):
                continue
            files[rel] = path.read_bytes()
    except OSError as exc:
        raise opening.OpenError(f"cannot read {folder}: {exc}") from exc
    return files


def read_existing_workspace(folder):
    """The workspace.json already in `folder`, or None when there is none. Unreadable is an error, not 'none'."""
    path = pathlib.Path(folder) / WORKSPACE
    if not path.exists():
        return None
    try:
        return read_workspace(folder)
    except SourceUnreadable as exc:
        raise opening.OpenError(f"{folder} holds a workspace whose record cannot be read, so I stopped: {exc}") from exc


def write_workspace(folder, files, record):
    """Write the copy, the pristine baseline (a full copy: propose needs the old text) and workspace.json into `folder`.

    Built beside the target and moved into place, so a failure halfway leaves no half-made workspace.
    """
    folder = pathlib.Path(folder)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise opening.OpenError(f"{folder} already exists and is not empty.")
    folder.parent.mkdir(parents=True, exist_ok=True)
    staging = folder.parent / f".{folder.name}.opening"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        write_folder(files, staging)
        write_folder(files, staging / ".planner" / "baseline")
        (staging / WORKSPACE).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if folder.exists():
            folder.rmdir()
        os.replace(staging, folder)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise opening.OpenError(f"cannot write the workspace at {folder}: {exc.strerror or exc}") from exc
