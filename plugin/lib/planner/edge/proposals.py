"""Proposal folders, zips and patch files on disk: written for a reader, read back for an owner.

The periphery for propose and review. Every failure to read or write names the path and the reason. A proposal is
written to a staging name, read back and scanned for private paths, and only then moved into place, so a hit
leaves nothing half-made for a reader to send by mistake. A zip is read in memory and never extracted, so a name
that climbs out of the folder cannot write anywhere.
"""
import os
import pathlib
import re
import shutil
import zipfile
from dataclasses import dataclass

from planner import proposal, publish

NOTE, PATCH, ANSWER = "proposal.md", "changes.patch", "answer.md"


class ProposalIOError(Exception):
    """The proposal cannot be read or written; the message names the path."""


def folder_name(written, title, parent):
    """<date>-<slug>, with -2, -3 ... when that name is taken in `parent`, so a second proposal never overwrites a first."""
    base = f"{written}-{publish.slug(title)}"
    name, n = base, 1
    while (parent / name).exists() or (parent / f"{name}.zip").exists():
        n += 1
        name = f"{base}-{n}"
    return name


def _scan_zip(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


def _scan_folder(path):
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(path.iterdir()) if p.is_file()}


def write(parent, name, files, as_zip, find_hits):
    """Write {file name: text} as parent/<name>/ or parent/<name>.zip. `find_hits(texts)` is run on what was
    read back from disk; any hit removes the staging copy and raises ProposalIOError with the first line."""
    parent = pathlib.Path(parent)
    target = parent / (f"{name}.zip" if as_zip else name)
    staging = parent / f".{target.name}.writing"
    try:
        parent.mkdir(parents=True, exist_ok=True)
        if staging.exists():
            _remove(staging)
        if as_zip:
            staging.write_bytes(publish.zip_bytes({k: v.encode("utf-8") for k, v in files.items()}, name))
            written = _scan_zip(staging)
        else:
            staging.mkdir()
            for fname, text in files.items():
                (staging / fname).write_bytes(text.encode("utf-8"))
            written = _scan_folder(staging)
        hits = find_hits(written)
        if hits:
            _remove(staging)
            where, number, line = hits[0]
            raise ProposalIOError(f"I stopped before writing the proposal: {where} line {number} holds a private path or name: '{line}'. "
                                  "Reword it (or for a session record, agree to --rewrite-home) and propose again. Nothing was written.")
        os.replace(staging, target)
    except OSError as exc:
        _remove(staging)
        raise ProposalIOError(f"cannot write the proposal at {target}: {exc.strerror or exc}") from exc
    except zipfile.BadZipFile as exc:
        _remove(staging)
        raise ProposalIOError(f"the zip I wrote at {staging} could not be read back: {exc}") from exc
    return target


def _remove(path):
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except OSError as exc:
        raise ProposalIOError(f"cannot remove {path}: {exc.strerror or exc}") from exc


@dataclass(frozen=True)
class Loaded:
    patch: bytes
    note: str  # proposal.md's text, "" when the source was a bare patch
    answer_to: pathlib.Path  # where answer.md goes for this source


def _from_zip(source):
    try:
        with zipfile.ZipFile(source) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            for name in names:
                publish.check_name(name)
            patch = next((n for n in names if n.split("/")[-1] == PATCH and len(n.split("/")) <= 2), None)
            note = next((n for n in names if n.split("/")[-1] == NOTE and len(n.split("/")) <= 2), None)
            if patch is None:
                raise ProposalIOError(f"{source} holds no {PATCH}, so it is not a proposal.")
            return Loaded(archive.read(patch), archive.read(note).decode("utf-8", "replace") if note else "",
                          source.with_name(f"{source.stem}-{ANSWER}"))
    except zipfile.BadZipFile as exc:
        raise ProposalIOError(f"{source} is not a readable zip: {exc}") from exc
    except publish.PublishError as exc:
        raise ProposalIOError(f"{source} holds a name that would write outside its folder, so I did not read it: {exc}") from exc


def read(source):
    """The Loaded proposal from a folder, a .zip or a bare .patch file. Nothing is written or extracted."""
    source = pathlib.Path(source).expanduser()
    if not source.exists():
        raise ProposalIOError(f"{source} does not exist.")
    try:
        if source.is_dir():
            patch = source / PATCH
            if not patch.is_file():
                raise ProposalIOError(f"{source} holds no {PATCH}, so it is not a proposal.")
            note = source / NOTE
            return Loaded(patch.read_bytes(), note.read_text(encoding="utf-8", errors="replace") if note.is_file() else "", source / ANSWER)
        if zipfile.is_zipfile(source):
            return _from_zip(source)
        return Loaded(source.read_bytes(), "", source.with_name(ANSWER))
    except OSError as exc:
        raise ProposalIOError(f"cannot read {source}: {exc.strerror or exc}") from exc


def write_answer(path, text):
    try:
        pathlib.Path(path).write_bytes(text.encode("utf-8"))
    except OSError as exc:
        raise ProposalIOError(f"cannot write {path}: {exc.strerror or exc}") from exc
    return path


BASE_RE = re.compile(r"^# base: (?P<commit>[0-9a-f]{7,64})\s*$", re.MULTILINE)


def written_against(parent, commit):
    """([proposals in `parent` whose patch says it was written against `commit`], [(path, why it could not be read)]).

    A folder or a .zip beside the workspace. Answers and anything that is not a proposal are not looked at; one that
    is a proposal and cannot be read is returned with the reason, never skipped without a word."""
    parent = pathlib.Path(parent)
    if not parent.is_dir():
        return [], []
    found, unreadable = [], []
    for entry in sorted(parent.iterdir()):
        if entry.name.startswith(".") or not (entry.is_dir() and (entry / PATCH).is_file() or entry.suffix == ".zip"):
            continue
        try:
            head = read(entry).patch[:2000].decode("utf-8", "replace")
        except ProposalIOError as exc:
            unreadable.append((entry.name, str(exc)))
            continue
        match = BASE_RE.search(head)
        if commit and match and (commit.startswith(match["commit"]) or match["commit"].startswith(commit)):
            found.append(entry.name)
    return found, unreadable
