"""The Library register (sources.md) and the spec folder move: the register reads by header name, so a register written
with six columns still reads, and each new column has its own error. Each test names a rule a reader would otherwise
have to discover by tripping on it."""
import json

import pytest

from conftest import MINI, check, run
from test_apply_add import filed, make_vault, plan
from vela import cli, sourcerows
from vela.decisions import add_source

TEN = "| ID | Title | Owner | Date | Kind | Type | Relates to | Version | Stored | Location |\n|" + "---|" * 10 + "\n"


def with_rows(vault, *rows, header=TEN):
    page = (vault / "sources.md").read_text(encoding="utf-8")
    head = page[:page.index("| ID |")]
    (vault / "sources.md").write_text(head + header + "\n".join(rows) + "\n", encoding="utf-8")


def library_file(vault, name, text="Demo material\n"):
    target = vault / "library" / "documents" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


# ------------------------------------------------------------ an older register still reads

def test_a_six_column_register_reads_with_no_new_errors(mini):
    code, out = check(mini)
    assert code == 0 and "0 errors, 0 warnings" in out, out


def test_a_six_column_row_reads_as_a_document():
    header = ("ID", "Title", "Owner", "Date", "Kind", "Location")
    row = sourcerows.read(header, ("SRC-01", "Read API", "@a", "2026-01-02", "exists", "local only"))
    assert (row.type, row.location, row.stored, row.relates, row.version) == ("document", "local only", "", (), "")


def test_the_row_a_fact_cites_is_read_by_name_in_either_shape(mini):
    from vela.decisions import resolve
    from test_apply_add import staged_view
    root = make_vault(mini.parent, name="six")
    assert resolve.source_row(staged_view(root), "SRC-01")["location"] == "local only"
    with_rows(root, "| SRC-01 | Read API | @a | 2026-01-02 | exists | spec | | v1.0 | | https://example.com/a |")
    assert resolve.source_row(staged_view(root), "SRC-01") == {"title": "Read API", "kind": "exists",
                                                                  "location": "https://example.com/a"}


# ------------------------------------------------------------ the new columns

def test_a_library_row_with_every_column_is_clean(mini):
    library_file(mini, "guide.pdf")
    with_rows(mini,
              "| SRC-01 | Guide | @a | 2026-01-02 | exists | document | APP-till UNK-001 | | library/documents/guide.pdf | local only |",
              "| SRC-02 | Sale API | @a | 2026-01-02 | exists | spec | CON-001 | v1.0 (latest v1.1) | | https://example.com/s |")
    code, out = check(mini)
    assert code == 0 and "0 errors, 0 warnings" in out, out


def test_a_type_outside_the_six_is_an_error(mini):
    with_rows(mini, "| SRC-01 | Guide | @a | 2026-01-02 | exists | memo | | | | local only |")
    code, out = check(mini)
    assert code == 1 and "E307" in out and "Use one of: spec, design, document, wiki, tracker, link" in out, out


@pytest.mark.parametrize("stored", ["docs/guide.pdf", "library/guide.pdf", "library/misc/guide.pdf",
                                    "library/documents/../x.pdf", "/library/documents/guide.pdf"])
def test_a_stored_path_must_sit_in_a_library_folder(mini, stored):
    with_rows(mini, f"| SRC-01 | Guide | @a | 2026-01-02 | exists | document | | | {stored} | |")
    code, out = check(mini)
    assert code == 1 and "E307" in out, out


def test_a_spec_is_stored_in_library_specs(mini):
    library_file(mini, "api.yaml")
    with_rows(mini, "| SRC-01 | API | @a | 2026-01-02 | exists | spec | | v1 | library/documents/api.yaml | |")
    code, out = check(mini)
    assert code == 1 and "E307" in out and "library/specs/" in out, out


def test_relates_to_must_name_something_in_the_vault(mini):
    with_rows(mini, "| SRC-01 | Guide | @a | 2026-01-02 | exists | document | APP-till APP-nowhere | | | local only |")
    code, out = check(mini)
    assert code == 1 and "E308" in out and "APP-nowhere" in out and "APP-till," not in out, out


def test_a_row_needs_a_stored_file_or_a_location(mini):
    with_rows(mini, "| SRC-01 | Guide | @a | 2026-01-02 | exists | document | | | | |")
    code, out = check(mini)
    assert code == 1 and "E309" in out, out


def test_a_stored_file_must_exist(mini):
    with_rows(mini, "| SRC-01 | Guide | @a | 2026-01-02 | exists | document | | | library/documents/guide.pdf | |")
    code, out = check(mini)
    assert code == 1 and "E313" in out and "library/documents/guide.pdf" in out, out
    library_file(mini, "guide.pdf")
    assert check(mini)[0] == 0


def test_a_version_on_a_document_is_a_warning(mini):
    with_rows(mini, "| SRC-01 | Guide | @a | 2026-01-02 | exists | document | | v2 | | local only |")
    code, out = check(mini)
    assert code == 0 and "W307" in out, out


def test_the_newer_version_is_exposed_when_the_cell_says_latest():
    header = sourcerows.HEADER
    cells = ("SRC-01", "API", "@a", "2026-01-02", "exists", "spec", "", "v1.0 (latest v1.1)", "", "https://x.example/a")
    row = sourcerows.read(header, cells)
    assert (row.version, row.newer) == ("v1.0", "v1.1")
    assert sourcerows.read(header, cells[:7] + ("v1.0",) + cells[8:]).newer == ""


# ------------------------------------------------------------ vela add source

def source_item(**more):
    return dict({"type": "source", "title": "Sale API", "owner": "@a", "kind": "exists",
                 "location": "https://example.com/s"}, **more)


def test_add_source_writes_the_library_columns_in_header_order(tmp_path):
    root = make_vault(tmp_path)
    with_rows(root, "| SRC-01 | Stock read API documentation | @stock-team | 2026-01-02 | exists | | | | | local only |")
    library_file(root, "a.pdf")
    writes = filed(root, "add", [source_item(source_type="spec", relates="CON-001, APP-till", version="v1.0 (latest v1.1)")])
    assert "| SRC-002 | Sale API | @a | 2026-10-20 | exists | spec | CON-001 APP-till | v1.0 (latest v1.1) | | " \
           "https://example.com/s |" in writes["sources.md"]


def test_add_source_with_a_stored_file(tmp_path):
    root = make_vault(tmp_path)
    with_rows(root, "| SRC-01 | Read | @a | 2026-01-02 | exists | | | | | local only |")
    writes = filed(root, "add", [source_item(location="", source_type="document", stored="library/documents/a.pdf")])
    assert "| document | | | library/documents/a.pdf | |" in writes["sources.md"]


def test_add_source_refuses_library_columns_the_register_lacks(tmp_path):
    root = make_vault(tmp_path)  # the mini register has six columns
    _, refusals = plan(root, "add", [source_item(source_type="spec")])
    assert [r.rule for r in refusals] == ["add-source-columns"]
    assert "Type" in refusals[0].fix


@pytest.mark.parametrize("more,rule", [({"source_type": "memo"}, "add-source-type"),
                                       ({"relates": "APP-nowhere"}, "add-source-relates"),
                                       ({"version": "v1"}, "add-source-version"),
                                       ({"stored": "docs/a.pdf"}, "add-source-stored"),
                                       ({"location": ""}, "add-source-where")])
def test_add_source_refusals(tmp_path, more, rule):
    root = make_vault(tmp_path)
    with_rows(root, "| SRC-01 | Read | @a | 2026-01-02 | exists | | | | | local only |")
    _, refusals = plan(root, "add", [source_item(**more)])
    assert rule in [r.rule for r in refusals]


def test_the_cli_takes_type_relates_version_and_stored(tmp_path):
    root = make_vault(tmp_path)
    with_rows(root, "| SRC-01 | Read | @a | 2026-01-02 | exists | | | | | local only |")
    code, said = run("add", "source", "--vault", str(root), "--today", "2026-10-20", "--title", "Sale API",
                     "--owner", "@a", "--kind", "exists", "--location", "https://example.com/s", "--type", "spec",
                     "--relates", "CON-001", "--version", "v1.0", "--json")
    assert code == 0, said
    assert json.loads(said)["id"] == "SRC-002"


def test_the_token_in_a_location_is_still_stripped_with_the_new_columns(tmp_path):
    root = make_vault(tmp_path)
    with_rows(root, "| SRC-01 | Read | @a | 2026-01-02 | exists | | | | | local only |")
    item = source_item(kind="repo", location="https://sam:ghp_secret123@github.com/acme/till.git@0a1b2c3")
    writes = filed(root, "add", [item])
    assert "ghp_secret123" not in writes["sources.md"] and "sam:" not in writes["sources.md"]
    assert add_source.notices(item)


# ------------------------------------------------------------ specs move to library/specs

def flow_vault(tmp_path):
    import shutil
    dest = tmp_path / "chain"
    shutil.copytree(MINI.parent / "flowcheck" / "04-chain-correct", dest)
    return dest


def test_the_flow_check_reads_specs_from_library_specs(tmp_path):
    from vela.flowcheck import readers
    root = flow_vault(tmp_path)
    assert (root / "library" / "specs" / "registration.asyncapi.yaml").is_file()
    catalog = readers.read_catalog(cli.load_vault(root), cli.spec_texts(root))
    assert any(path.startswith("library/specs/") for path in cli.spec_texts(root))
    assert catalog.problems == []


def test_a_spec_left_in_the_old_specs_folder_is_an_error_naming_the_new_place(tmp_path):
    root = flow_vault(tmp_path)
    (root / "specs").mkdir()
    (root / "library" / "specs" / "registration.asyncapi.yaml").rename(root / "specs" / "registration.asyncapi.yaml")
    code, out = run("check", "--vault", str(root), "--today", "2026-10-21")
    assert "E312" in out and "library/specs/" in out and "specs/registration.asyncapi.yaml" in out, out
    assert code == 1


def test_git_mv_hint_is_a_move_the_checker_accepts(tmp_path):
    root = flow_vault(tmp_path)
    assert [f.code for f in cli.library_file_findings(root)] == []


def test_the_spec_and_register_findings_are_in_the_codes_table():
    from vela import schema
    for code in ("E307", "W307", "E308", "E309", "E312", "E313"):
        assert code in schema.CODES
