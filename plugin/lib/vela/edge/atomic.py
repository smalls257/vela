"""Writing generated files so a reader never sees half of one (Sensor: a truncated manifest looks like "no manifest").

A file is written to a temporary name in its own folder and renamed over the target, so a kill, a full disk or a sync
client mid-write leaves the old file whole or the new file whole. This is the periphery: the pure modules decide what
to write and ask here to put it on the disk.
"""
import os
import pathlib


class WriteFailed(OSError):
    """Some files could not be written. `written` and `unwritten` are the paths, so the caller says which."""

    def __init__(self, reason, written, unwritten):
        super().__init__(reason)
        self.written, self.unwritten = list(written), list(unwritten)


def _temp_name(path):
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def write_atomic(path, data):
    """Write `data` (bytes, or text as UTF-8) to `path` whole or not at all."""
    write_all_atomic({path: data})


def write_all_atomic(files):
    """Write every {path: data} whole, all or nothing as far as a disk allows: every file is first written to a
    temporary name, and only when all of those are on the disk are they renamed over their targets. A failure while
    staging leaves every target untouched. A failure while renaming (rare: a locked file) raises WriteFailed naming
    what was written and what was not."""
    staged = []
    try:
        for path, data in files.items():
            path = pathlib.Path(path)
            temp = _temp_name(path)
            staged.append((temp, path))
            temp.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    except OSError as exc:
        _discard(staged)
        raise WriteFailed(f"{exc.strerror or exc}: nothing was changed", [], [p for _, p in staged]) from exc
    written = []
    for temp, path in staged:
        try:
            os.replace(temp, path)
        except OSError as exc:
            _discard(staged)
            raise WriteFailed(f"{path}: {exc.strerror or exc}", written, [p for _, p in staged if p not in written]) from exc
        written.append(path)


def _discard(staged):
    for temp, _ in staged:
        try:  # nosemgrep: except-pass -- a stray temp file is harmless; the write error is what the caller reports
            temp.unlink(missing_ok=True)
        except OSError:
            continue
