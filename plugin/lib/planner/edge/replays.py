"""Writing a replay into a reader's workspace (the periphery for keep-up; replay.py decides, this writes).

The Violation to prevent is a replay that fails half-way and leaves the reader unable to tell which version of
their work is where. So the order is fixed, and the one record that says a replay finished is written last:

  1. the new baseline is built beside the old one (`baseline.next`);
  2. the reader's version of every page the replay changes is kept in `.planner/replay-backup/`;
  3. the reader's side of each conflict is written beside its page;
  4. `.planner/replay.json` lists the conflicts, so they are listed even if the next step fails;
  5. the working pages are changed;
  6. the baseline is swapped, then the stamp and `workspace.json`, which is what freshness reads.

Until step 6 the old baseline stands and the same `planner open` can be run again. Every failure names the path.
"""
import json
import os
import pathlib
import shutil

from planner import opening, publish, replay
from planner.edge import copies

REPLAY = pathlib.Path(".planner") / "replay.json"
BACKUP = pathlib.Path(".planner") / "replay-backup"
FORMAT = 1


def read_record(root):
    """The last replay's record ({} when there never was one). An unreadable record is an error, not 'none'."""
    path = pathlib.Path(root) / REPLAY
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise opening.OpenError(f"{path} cannot be read: {exc}. It lists the conflicts from your last re-open; fix or remove it.") from exc
    if not isinstance(data, dict):
        raise opening.OpenError(f"{path} is not a replay record.")
    return data


def open_conflicts(root):
    """The conflicts of the last replays whose saved side is still there. Deleting the .mine file is how a reader closes one."""
    root = pathlib.Path(root)
    return [c for c in read_record(root).get("conflicts", []) if (root / c["mine"]).is_file()]


def _inside(root, rel):
    try:
        publish.check_name(rel)
    except publish.PublishError as exc:
        raise opening.OpenError(f"a replay would write '{rel}', which is not a vault-relative path: {exc}") from exc
    return root / rel


def _write(root, rel, data):
    target = _inside(root, rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _remove(root, rel):
    target = _inside(root, rel)
    target.unlink()
    for parent in target.parents:
        if parent == root or any(parent.iterdir()):
            break
        parent.rmdir()


def existing_mine(root):
    """Vault-relative paths of every saved side already in the workspace, so a new conflict never overwrites one."""
    root = pathlib.Path(root)
    found = (p.relative_to(root).as_posix() for p in sorted(root.rglob("*")) if p.is_file())
    return {rel for rel in found if not rel.startswith(".planner/") and replay.is_mine_file(rel)}


def record_json(old, new, result, carried, today):
    conflicts = carried + [c.as_dict() for c in result.conflicts]
    return {"format": FORMAT, "replayed": today, "from": old, "to": new, "conflicts": conflicts,
            "merged": [o.path for o in result.outcomes if o.action == "merged"]}


def apply(root, result, files, replay_record, workspace_record, backup_name):
    """Make `root` hold the replay `result` and the new copy `files` ({path: bytes}, with its stamp) as the baseline.

    `replay_record` is the new replay.json; `workspace_record` the new workspace.json. Raises OpenError naming the step that failed."""
    root = pathlib.Path(root)
    baseline, staging, previous = root / copies.BASELINE, root / copies.BASELINE.with_name("baseline.next"), root / copies.BASELINE.with_name("baseline.previous")
    step = "the new baseline"
    try:
        for leftover in (staging, previous):
            if leftover.exists():
                shutil.rmtree(leftover)
        copies.write_folder(files, staging)
        step = "your saved pre-replay pages"
        for rel, data in result.backups.items():
            _write(root, f"{BACKUP.as_posix()}/{backup_name}/{rel}", data)
        step = "your side of each conflict"
        for rel, data in result.mine.items():
            _write(root, rel, data)
        step = ".planner/replay.json"
        _write(root, REPLAY.as_posix(), (json.dumps(replay_record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        step = "your pages"
        for rel, data in result.write.items():
            _write(root, rel, data)
        for rel in result.delete:
            _remove(root, rel)
        step = "the baseline swap"
        if baseline.exists():
            os.replace(baseline, previous)
        os.replace(staging, baseline)
        if previous.exists():
            shutil.rmtree(previous)
        step = "the stamp and workspace record"
        _write(root, publish.STAMP_PATH, files[publish.STAMP_PATH])
        _write(root, copies.WORKSPACE.as_posix(), (json.dumps(workspace_record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    except OSError as exc:
        raise opening.OpenError(f"the re-open stopped while writing {step}: {exc.strerror or exc} ({getattr(exc, 'filename', '') or root}). "
                                "Your old baseline stands until the swap, so run the same planner open again once that is fixed; "
                                f"your own version of each page it changed is in {root / BACKUP}.") from exc
