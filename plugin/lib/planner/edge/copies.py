"""Writing and reading published copies and reader workspaces on disk (the periphery for publish and freshness).

Every failure to read or write names the path and the reason. A source that is simply not there is
SourceUnreachable, which freshness reports as a state; one that is there but is not a published copy is
SourceUnreadable, which freshness reports as `unknown` with the reason.
"""
import json
import pathlib
import zipfile

from planner import publish

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
