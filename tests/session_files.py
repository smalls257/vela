"""The one way a test writes or reads a session record by id, so a change in where records live touches this
file and not thirty test files.

A session is two files: the committed stub `sessions/<id>.md` and the private notes `sessions/private/<id>.md`.
`write_record` takes a whole record, as the fixtures spell it, and splits it. `record_text` reads the private notes
(the words); `stub_text` reads the committed header. Text that is already private-shaped (no `modes`) replaces the
notes and leaves the stub alone, so a test can read the notes, change a line and write them back."""
import pathlib

from vela import privaterecord

IGNORE_LINE = "sessions/private/"


def write_record(root, record_id, text):
    root = pathlib.Path(root)
    if "modes" not in privaterecord.stub_meta(text):
        return write_private(root, record_id, text)
    split = privaterecord.split_record(text)
    stub = root / privaterecord.stub_path(record_id)
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(split.stub, encoding="utf-8")
    ignore_private(root)
    return write_private(root, record_id, split.private)


def write_whole_record(root, record_id, text):
    """A whole record as one committed file, the shape the fixtures still hold until Task 7 splits them: for the
    tests that read a session as a vault page, body and all (the Grills view's `since`)."""
    path = pathlib.Path(root) / privaterecord.stub_path(record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_private(root, record_id, text):
    path = pathlib.Path(root) / privaterecord.private_path(record_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def ignore_private(root):
    ignore = pathlib.Path(root) / ".gitignore"
    held = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if IGNORE_LINE not in held.split("\n"):
        ignore.write_text(held + ("" if held.endswith("\n") or not held else "\n") + IGNORE_LINE + "\n",
                          encoding="utf-8")


def record_text(root, record_id):
    """The notes. The example and mini fixtures still hold whole records in `sessions/<id>.md` with no private file
    (Task 7 splits them), so a record with no notes file reads as that whole file."""
    private = pathlib.Path(root) / privaterecord.private_path(record_id)
    return (private if private.is_file() else pathlib.Path(root) / privaterecord.stub_path(record_id)).read_text(
        encoding="utf-8")


def stub_text(root, record_id):
    return (pathlib.Path(root) / privaterecord.stub_path(record_id)).read_text(encoding="utf-8")


def set_modes(root, record_id, modes):
    """The stub's `modes:` line set to `modes` (a string such as `shape, boundary`): the stub is where modes live."""
    path = pathlib.Path(root) / privaterecord.stub_path(record_id)
    meta = privaterecord.stub_meta(path.read_text(encoding="utf-8"))
    stub = privaterecord.render_stub({**meta, "modes": [m.strip() for m in modes.split(",")]})
    path.write_text(stub, encoding="utf-8")
    return path


def edit_record(root, record_id, old, new):
    """Replace `old` with `new` in a record's notes. `old` must occur exactly once."""
    text = record_text(root, record_id)
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in record {record_id}, expected exactly 1"
    private = pathlib.Path(root) / privaterecord.private_path(record_id)
    if not private.is_file():  # a whole fixture record: edit it where it is
        path = pathlib.Path(root) / privaterecord.stub_path(record_id)
        path.write_text(text.replace(old, new), encoding="utf-8")
        return path
    return write_private(root, record_id, text.replace(old, new))


def edit_stub(root, record_id, old, new):
    """Replace `old` with `new` in the committed stub (modes, date, status and the other header lines live there)."""
    path = pathlib.Path(root) / privaterecord.stub_path(record_id)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in the stub of {record_id}, expected exactly 1"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


def expose_notes(root, record_id):
    """Lay the notes' body under the stub's header in the committed file, so a check that still resolves
    `[[<id>#^cNN]]` against the session as a vault page finds its anchors. Interim: those links move to the
    `[[<id>]] cNN` form with the receipts rules, and then this goes."""
    stub = pathlib.Path(root) / privaterecord.stub_path(record_id)
    head = stub.read_text(encoding="utf-8").split("\n---\n", 1)[0] + "\n---\n"
    stub.write_text(head + record_text(root, record_id).split("\n---\n", 1)[1], encoding="utf-8")
    return stub


def split_whole_records(root):
    """Give every whole record in a copied fixture its private notes and a bare stub, as Task 7 will for the fixtures
    themselves. Only for a copy: the snapshots under tests/sim are sealed."""
    for path in sorted((pathlib.Path(root) / "sessions").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "modes" in privaterecord.stub_meta(text):
            write_record(root, path.stem, text)
