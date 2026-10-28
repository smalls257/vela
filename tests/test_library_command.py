"""`vela library add` and `vela library list`: a link is a row, a file is kept only with the lead's yes, nothing is
overwritten, and the commit holds exactly the new file and sources.md. Each test names a rule the skill would
otherwise carry in prose."""
import json
import subprocess

import pytest

from conftest import run
from test_apply_add import make_vault
from test_library_register import TEN, with_rows
from vela import library

CAPTURES = ['- [thought] (@priya) "The Figma mock is what we build from." ^c01',
            '- [answer] (@priya) "Yes, keep the file in the plan." ^c02',
            '- [answer] (@priya) "ok" ^c03']
OPENAPI = "openapi: 3.0.0\ninfo:\n  title: Sale\n  version: 2.1.0\npaths: {}\n"


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture
def vault(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    with_rows(root, "| SRC-01 | Read | @a | 2026-01-02 | exists | document | | | | local only |")
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test Lead")
    git(root, "config", "user.email", "lead@example.com")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    return root


@pytest.fixture
def outside(tmp_path):
    folder = tmp_path / "outside"
    folder.mkdir()
    return folder


def add(root, source, *more):
    return run("library", "add", str(source), "--vault", str(root), "--today", "2026-10-20", "--json", *more)


def committed(root):
    return sorted(p for p in git(root, "show", "--name-only", "--format=", "HEAD").split("\n") if p)


# ------------------------------------------------------------ links

@pytest.mark.parametrize("url,kind", [
    ("https://www.figma.com/design/abc/Till", "design"),
    ("https://acme.atlassian.net/wiki/spaces/ENG/pages/1/Till", "wiki"),
    ("https://acme.atlassian.net/browse/TILL-12", "tracker"),
    ("https://acme.atlassian.net/jira/software/projects/TILL/boards/1", "tracker"),
    ("https://example.com/api/sale.openapi.yaml", "spec"),
    ("https://example.com/asyncapi.json", "spec"),
    ("https://example.com/handbook", "link")])
def test_a_link_is_typed_from_its_address(vault, url, kind):
    code, said = add(vault, url, "--title", "Thing")
    assert code == 0, said
    assert json.loads(said)["type"] == "source"
    row = [r for r in library.rows((vault / "sources.md").read_text(encoding="utf-8")) if r.title == "Thing"][0]
    assert (row.type, row.location, row.stored) == (kind, url, "")
    assert committed(vault) == ["sources.md"]


def test_type_overrides_the_guess(vault):
    code, said = add(vault, "https://example.com/handbook", "--title", "Thing", "--type", "wiki")
    assert code == 0, said
    assert library.rows((vault / "sources.md").read_text(encoding="utf-8"))[-1].type == "wiki"


def test_a_token_in_a_link_is_stripped(vault):
    code, said = add(vault, "https://sam:ghp_secret123@github.com/acme/till", "--title", "Till repo")
    assert code == 0, said
    assert "ghp_secret123" not in (vault / "sources.md").read_text(encoding="utf-8")
    assert "ghp_secret123" not in git(vault, "show", "HEAD")


def test_the_same_link_twice_is_refused_and_names_the_first(vault):
    assert add(vault, "https://example.com/handbook", "--title", "One")[0] == 0
    code, said = add(vault, "https://example.com/handbook", "--title", "Two")
    assert code == 1 and "SRC-002" in said, said
    assert len(library.rows((vault / "sources.md").read_text(encoding="utf-8"))) == 2


# ------------------------------------------------------------ files

def test_a_file_is_kept_with_the_leads_yes_and_the_commit_holds_two_paths(vault, outside):
    (vault / "stray.txt").write_text("not part of this\n", encoding="utf-8")
    source = outside / "Guide.pdf"
    source.write_bytes(b"%PDF guide")
    code, said = add(vault, source, "--title", "Till guide", "--keep-file", "--yes", "^c02")
    assert code == 0, said
    assert (vault / "library" / "documents" / "till-guide.pdf").read_bytes() == b"%PDF guide"
    assert committed(vault) == ["library/documents/till-guide.pdf", "sources.md"]
    assert "stray.txt" in git(vault, "status", "--porcelain")
    assert json.loads(said)["stored"] == "library/documents/till-guide.pdf"


def test_a_file_without_a_yes_asks_and_writes_nothing(vault, outside):
    source = outside / "Guide.pdf"
    source.write_bytes(b"x")
    before = git(vault, "status", "--porcelain")
    for extra in ((), ("--keep-file",)):
        code, said = add(vault, source, "--title", "Till guide", *extra)
        assert code == 3, said
        assert "company material" in json.dumps(json.loads(said)["lines"]), said
    assert not (vault / "library").exists() and git(vault, "status", "--porcelain") == before


def test_a_bare_ok_is_not_a_yes(vault, outside):
    source = outside / "Guide.pdf"
    source.write_bytes(b"x")
    code, said = add(vault, source, "--title", "Till guide", "--keep-file", "--yes", "^c03")
    assert code == 1 and not (vault / "library").exists(), said


def test_a_missing_capture_is_not_a_yes(vault, outside):
    source = outside / "Guide.pdf"
    source.write_bytes(b"x")
    code, said = add(vault, source, "--title", "Till guide", "--keep-file", "--yes", "^c99")
    assert code == 1 and not (vault / "library").exists(), said


def test_a_file_in_the_inbox_is_copied_and_the_inbox_copy_stays_ignored(vault):
    (vault / ".gitignore").write_text(".inbox/\n", encoding="utf-8")
    git(vault, "add", ".gitignore")
    git(vault, "commit", "-q", "-m", "ignore")
    inbox = vault / ".inbox"
    inbox.mkdir()
    (inbox / "notes.md").write_text("meeting\n", encoding="utf-8")
    code, said = add(vault, inbox / "notes.md", "--title", "Meeting notes", "--keep-file", "--yes", "^c02")
    assert code == 0, said
    assert committed(vault) == ["library/documents/meeting-notes.md", "sources.md"]
    assert (inbox / "notes.md").exists() and ".inbox" not in git(vault, "ls-files")


def test_a_large_library_file_is_added_with_a_note(vault, outside, monkeypatch):
    monkeypatch.setattr(library, "MAX_BYTES", 10)
    source = outside / "Big.zip"
    source.write_bytes(b"0123456789ABC")
    code, said = add(vault, source, "--title", "Big", "--keep-file", "--yes", "^c02")
    assert code == 0, said
    assert (vault / "library" / "documents" / "big.zip").exists()
    assert "a link is usually the better row" in json.dumps(json.loads(said)["lines"]), said


def test_a_name_clash_is_refused_and_named(vault, outside):
    first = outside / "a.pdf"
    first.write_bytes(b"one")
    assert add(vault, first, "--title", "Till guide", "--keep-file", "--yes", "^c02")[0] == 0
    second = outside / "b.pdf"
    second.write_bytes(b"two")
    code, said = add(vault, second, "--title", "Till guide", "--keep-file", "--yes", "^c02")
    assert code == 1 and "library/documents/till-guide.pdf" in said, said
    assert (vault / "library" / "documents" / "till-guide.pdf").read_bytes() == b"one"


def test_the_same_bytes_under_another_title_are_refused(vault, outside):
    first = outside / "a.pdf"
    first.write_bytes(b"same")
    assert add(vault, first, "--title", "Till guide", "--keep-file", "--yes", "^c02")[0] == 0
    code, said = add(vault, first, "--title", "Another name", "--keep-file", "--yes", "^c02")
    assert code == 1 and "till-guide.pdf" in said, said
    assert len(library.rows((vault / "sources.md").read_text(encoding="utf-8"))) == 2


def test_a_spec_file_gets_its_version_and_keeps_its_name(vault, outside):
    source = outside / "till.openapi.yaml"
    source.write_text(OPENAPI, encoding="utf-8")
    code, said = add(vault, source, "--title", "Sale API", "--keep-file", "--yes", "^c02", "--relates", "CON-001")
    assert code == 0, said
    row = library.rows((vault / "sources.md").read_text(encoding="utf-8"))[-1]
    assert (row.type, row.version, row.stored, row.relates) == (
        "spec", "v2.1.0", "library/specs/till.openapi.yaml", ("CON-001",))
    code, out = run("check", "--vault", str(vault))
    assert "E313" not in out and "E307" not in out, out


def test_a_figma_export_file_is_a_document_unless_told_otherwise(vault, outside):
    source = outside / "mock.png"
    source.write_bytes(b"png")
    code, said = add(vault, source, "--title", "Till mock", "--type", "design", "--keep-file", "--yes", "^c02")
    assert code == 0, said
    assert (vault / "library" / "designs" / "till-mock.png").exists()


def test_a_refused_row_leaves_no_orphan_file(vault, outside):
    source = outside / "a.pdf"
    source.write_bytes(b"one")
    code, said = add(vault, source, "--title", "Till guide", "--keep-file", "--yes", "^c02", "--relates", "APP-nowhere")
    assert code == 1, said
    assert not (vault / "library" / "documents" / "till-guide.pdf").exists()


def test_unsaved_edits_to_the_register_are_not_swept_into_the_commit(vault):
    with (vault / "sources.md").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    code, said = add(vault, "https://example.com/handbook", "--title", "Thing")
    assert code == 1 and "uncommitted" in said, said


def test_a_local_spec_content_is_read():
    assert library.type_of_file("a.yaml", OPENAPI) == ("spec", "2.1.0")
    assert library.type_of_file("a.json", '{"asyncapi": "2.6.0", "info": {"version": "1.0"}}') == ("spec", "1.0")
    assert library.type_of_file("notes.yaml", "title: x\n") == ("document", "")


# ------------------------------------------------------------ list

def test_list_groups_rows_by_type_in_json(vault):
    with_rows(vault,
              "| SRC-01 | Read | @a | 2026-01-02 | exists | | | | | local only |",
              "| SRC-02 | Sale API | @a | 2026-01-02 | exists | spec | CON-001 | v1.0 (latest v1.1) | | https://x.example/s |",
              "| SRC-03 | Mock | @a | 2026-01-02 | exists | design | | | | https://figma.com/x |")
    code, said = run("library", "list", "--vault", str(vault), "--json")
    assert code == 0, said
    data = json.loads(said)
    assert data["count"] == 3
    assert [g["type"] for g in data["groups"]] == ["spec", "design", "document"]
    spec = data["groups"][0]["items"][0]
    assert spec == {"id": "SRC-02", "title": "Sale API", "owner": "@a", "date": "2026-01-02", "kind": "exists",
                    "type": "spec", "relates": ["CON-001"], "version": "v1.0", "newer": "v1.1", "stored": "",
                    "location": "https://x.example/s"}
    code, said = run("library", "list", "--vault", str(vault), "--type", "design", "--json")
    assert [g["type"] for g in json.loads(said)["groups"]] == ["design"]


def test_list_reads_a_six_column_register_as_documents(tmp_path):
    root = make_vault(tmp_path)
    code, said = run("library", "list", "--vault", str(root), "--json")
    assert code == 0 and {g["type"] for g in json.loads(said)["groups"]} == {"document"}, said


def test_list_for_lead_speaks_plainly(vault):
    code, said = run("library", "list", "--vault", str(vault), "--for-lead")
    assert code == 0 and "SRC" not in said, said


def test_the_asks_pass_the_lead_voice_check(vault, outside, monkeypatch):
    source = outside / "Guide.pdf"
    source.write_bytes(b"0123456789ABC")
    code, said = run("library", "add", str(source), "--vault", str(vault), "--title", "Till guide", "--for-lead")
    assert code == 3 and "company material" in said, said
    monkeypatch.setattr(library, "MAX_BYTES", 10)
    code, said = run("library", "add", str(source), "--vault", str(vault), "--title", "Till guide", "--keep-file",
                     "--yes", "^c02", "--for-lead")
    assert code == 0 and "A link to where it lives is usually better." in said, said
    code, said = run("library", "add", "https://example.com/h", "--vault", str(vault), "--title", "Handbook",
                     "--for-lead")
    assert code == 0 and "added" in said, said


def test_the_bash_hook_lets_vela_library_add_through():
    from vela import hookverdict
    command = 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/run-vela" library add ./Guide.pdf --title "Guide" --keep-file --yes ^c2'
    assert hookverdict.bash_verdict(command) is None
