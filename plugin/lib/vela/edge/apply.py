"""The disk for `vela apply`: read files for the decision core, and write every file of a decision or none.

The periphery for `vela.decisions`, which decides what to write. What this adds, and why:

- **All or nothing.** The pages, the record and the decision file's `applied` marker go to disk in one
  `atomic.write_all_atomic` call: a file that half-landed would leave the decision file saying "not applied" over
  pages that already changed, and the next apply would file it twice.
- **Nothing outside the vault.** A write's path comes from a kind module, and some of those take a page path from an
  item the model filled in; a path that resolves outside the vault root (`../`, an absolute path, a symlinked folder)
  is refused before anything is written, so a mistyped field can't overwrite a file elsewhere on the machine.
- **No git.** Committing is the checkpoint's and close's work. So `apply` behaves the same in a vault repo and in a
  reader copy, where no git may run at all.
"""
import pathlib

from vela.edge import atomic


class OutsideVault(ValueError):
    """A write named a path outside the vault root. Nothing was written."""


def target(root, path):
    """The absolute path for a vault-relative `path`, refusing any that resolves outside `root`."""
    root = pathlib.Path(root).resolve()
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise OutsideVault(f"{path} is outside the vault, so nothing was written")
    return resolved


def reader(root):
    """read(path) -> the file's text, or None when there is no such file (a new page)."""
    def read(path):
        try:
            return target(root, path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
    return read


def write_all(root, writes, extra=None):
    """Write every `schema.Write` under `root`, plus `extra` ({absolute path: text}), all or nothing. Returns the
    vault-relative paths written. Raises OutsideVault, or atomic.WriteFailed naming what landed."""
    files = {target(root, write.path): write.text for write in writes}
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
    files.update({pathlib.Path(p): text for p, text in (extra or {}).items()})
    atomic.write_all_atomic(files)
    return [write.path for write in writes]
