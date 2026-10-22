"""The one way a test writes or reads a session record by id, so a change in where records live touches this
file and not thirty test files. Today both functions use `sessions/<id>.md`. Task 4 makes them split a record
into its committed stub and its private file, and read the private file back."""
import pathlib


def write_record(root, record_id, text):
    path = pathlib.Path(root) / "sessions" / f"{record_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def record_text(root, record_id):
    return (pathlib.Path(root) / "sessions" / f"{record_id}.md").read_text(encoding="utf-8")


def edit_record(root, record_id, old, new):
    """Replace `old` with `new` in a record. `old` must occur exactly once."""
    text = record_text(root, record_id)
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in record {record_id}, expected exactly 1"
    return write_record(root, record_id, text.replace(old, new))
