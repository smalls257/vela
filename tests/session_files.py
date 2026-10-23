"""The one way a test writes or reads a session record by id, so a change in where records live touches this
file and not thirty test files.

A session is two files: the committed stub `sessions/<id>.md` and the private notes `sessions/private/<id>.md`.
`write_record` takes a whole record, as the fixtures spell it, and splits it. `record_text` reads the private notes
(the words); `stub_text` reads the committed header. Text that is already private-shaped (no `modes`) replaces the
notes and leaves the stub alone, so a test can read the notes, change a line and write them back."""
import pathlib
import re
import shutil

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
    """The notes."""
    return (pathlib.Path(root) / privaterecord.private_path(record_id)).read_text(encoding="utf-8")


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
    return write_private(root, record_id, text.replace(old, new))


def edit_stub(root, record_id, old, new):
    """Replace `old` with `new` in the committed stub (modes, date, status and the other header lines live there)."""
    path = pathlib.Path(root) / privaterecord.stub_path(record_id)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in the stub of {record_id}, expected exactly 1"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


SPLIT_DAY = "2026-10-22"
_SESSION_QUOTE = re.compile(r'quote: "(?P<words>[^"]*)" in \[\[(?P<page>[^\]|#]+)\]\]')
_STOP = frozenset("the a an of to and in is are for on be by it that this with at as or from who what how which does do "
                  "not will can should its their".split())


def split_copy(src, dst):
    """A copy of a vault with its whole session records moved to stubs and private notes, as `vela records split`
    leaves a plan (lead "", so no one's words are kept). For a sealed snapshot or a fixture a test needs split: the
    original is never edited.

    A reviewer question that quotes a session can't stay: a session's notes are private, so E802 refuses the quote.
    The split lists no replacement, because none exists; a lead would requote such a row from a page by hand. This
    does that for the copy, with the page line that shares the most words with the row's question."""
    from vela.commands import private_records
    shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    dst = pathlib.Path(dst)
    private_records.split_folder(dst, "", SPLIT_DAY)
    _stand_in_for_the_hand_requote(dst)
    return dst


def _words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in _STOP and len(w) > 2}


def _page_sentences(vault):
    from vela import questions
    found = []
    for page in vault.pages:
        if page.type == "session" or page.id in ("unknowns-and-risks", "glossary") or vault.page(page.name) is not page:
            continue
        for line in questions.quotable_text(page).split("\n"):
            line = re.sub(r"\*\*|\[\[|\]\]|`", "", re.sub(r"^[-*#>\s|]+", "", line).strip())
            for sentence in re.split(r"(?<=[.;])\s+", line):
                if 5 <= len(sentence.split()) <= 22 and not re.search(r'["|\\\[(<]', sentence):
                    found.append((page.name, sentence.strip()))
    return found


def _stand_in_for_the_hand_requote(root):
    # Test stand-in only: `vela records split` lists these rows as Left and the lead requotes them; a copy can't wait.
    from vela import cli
    ledger = root / "11-unknowns-and-risks.md"
    if not ledger.is_file():
        return
    vault = cli.load_vault(root)
    sessions = {page.name for page in vault.pages if page.type == "session"}
    rows = ledger.read_text(encoding="utf-8").split("\n")
    if not any((m := _SESSION_QUOTE.search(r)) and m["page"].strip() in sessions for r in rows):
        return
    sentences = _page_sentences(vault)
    for index, row in enumerate(rows):
        found = _SESSION_QUOTE.search(row)
        if not found or found["page"].strip() not in sessions:
            continue
        asked = _words((re.search(r"question: (.*?)(?:; quote:|;|\|)", row) or [None, row])[1])
        page, sentence = max(sentences, key=lambda c: (len(asked & _words(c[1])), -len(c[1])))
        rows[index] = row.replace(found[0], f'quote: "{sentence}" in [[{page}]]')
    ledger.write_text("\n".join(rows), encoding="utf-8")
