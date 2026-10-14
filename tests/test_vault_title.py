"""S49: the first session asks for the initiative's short name once, and planner check warns (W718) while the
vault still carries the title the template ships."""
import shutil

from conftest import REPO, edit, findings, run

PLUGIN = REPO / "plugin"
SESSION = "---\nid: 2026-01-10-first\ntype: session\ntitle: First\ndate: 2026-01-10\nmodes: [dump]\nstatus: open\nsummary: In progress.\n---\n\n# First\n"
CONVENTIONS = ("template", "plugin/vault", "examples/unified-booking", "tests/stub-conventions")


def named(tmp_path, title, session=True):
    (tmp_path / ".planner.yaml").write_text(f"initiative: INI-001\ntitle: {title}\n", encoding="utf-8")
    if session:
        (tmp_path / "sessions").mkdir(exist_ok=True)
        (tmp_path / "sessions" / "2026-01-10-first.md").write_text(SESSION, encoding="utf-8")
    return tmp_path


def test_check_warns_while_the_title_is_the_templates_placeholder_and_points_at_its_line(tmp_path):
    named(tmp_path, "New initiative")
    code, out = run("check", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0, out  # a warning, never an error
    assert (".planner.yaml", "W718") in [(p, c) for c, p in findings(out)]
    assert ".planner.yaml:2: W718" in out
    assert "short name" in out and "title:" in out


def test_a_fresh_vault_with_no_session_yet_is_not_warned(tmp_path):
    named(tmp_path, "New initiative", session=False)
    code, out = run("check", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert "W718" not in out


def test_check_is_quiet_once_the_initiative_has_a_name(tmp_path):
    named(tmp_path, "Heron desk assistant")
    code, out = run("check", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert "W718" not in out


def test_the_placeholder_is_the_title_the_template_ships_and_the_template_warns_after_its_first_session(tmp_path):
    from vela import schema
    assert f"title: {schema.PLACEHOLDER_TITLE}\n" in (REPO / "template" / ".planner.yaml").read_text(encoding="utf-8")
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "template", vault)
    code, out = run("check", "--vault", str(vault), "--today", "2026-01-15")
    assert code == 0 and "W718" not in out  # a fresh copy is clean
    (vault / "sessions" / "2026-01-10-first.md").write_text(SESSION, encoding="utf-8")
    code, out = run("check", "--vault", str(vault), "--today", "2026-01-15")
    assert code == 0 and ".planner.yaml:3: W718" in out
    edit(vault / ".planner.yaml", "title: New initiative", "title: Heron")
    assert "W718" not in run("check", "--vault", str(vault), "--today", "2026-01-15")[1]


def test_every_conventions_copy_lists_the_code(tmp_path):
    for folder in CONVENTIONS:
        text = (REPO / folder / "CONVENTIONS.md").read_text(encoding="utf-8")
        assert "| W718 | the initiative's title in .planner.yaml is still the template's placeholder |" in text, folder
        assert "- W718: `.planner.yaml` still has `title: New initiative`" in text, folder


def test_the_first_session_asks_for_the_name_once_and_writes_it():
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert "**Name the initiative, once.**" in start
    paragraph = start.split("**Name the initiative, once.**", 1)[1].split("\n", 1)[0]
    assert "What short name should this initiative go by?" in paragraph
    assert "`title:` in `.planner.yaml`" in paragraph and "never ask again" in paragraph
    assert "Reader copy" in paragraph
    for skill in ("dump", "discover"):
        text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "asks once for the initiative's short name" in text, skill
