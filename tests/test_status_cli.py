"""planner status and planner next: the progress grid on the command line."""
from conftest import REPO, edit, run

FIXTURE = REPO / "examples" / "unified-booking"


def test_status_prints_one_line_per_app_with_ages(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing", "- **Blocks:** [[till-building-blocks|Till]]")
    code, out = run("status", "--vault", str(mini), "--today", "2026-02-03")
    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == "planner status: 3 apps. Today is 2026-02-03 (--today)."
    assert lines[1].startswith("APP-till | stage baseline | inkling 0, assumption 1, fact 0, decided 0 | "
                               "oldest open unknown: UNK-001, open 24 days (opened 2026-01-10) | next: probe UNK-001.")


def test_next_names_one_app_and_mode(mini):
    code, out = run("next", "--vault", str(mini), "--today", "2026-01-15")
    assert code == 0
    assert out == "planner next: APP-till, discover APP-till. APP-till lists no sources. Today is 2026-01-15 (--today).\n"


def test_next_on_an_empty_vault_suggests_a_dump(tmp_path):
    (tmp_path / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("planner next: initiative, dump.")


def test_status_with_a_bad_date_is_a_tool_failure(mini):
    assert run("status", "--vault", str(mini), "--today", "soon")[0] == 2
    assert run("next", "--vault", str(mini), "--today", "2026-13-01")[0] == 2


def test_the_fixture_has_nothing_left_to_do():
    code, out = run("next", "--vault", str(FIXTURE), "--today", "2026-11-20")
    assert code == 0
    assert out == "planner next: nothing to do. Every app's items are settled and its epics decided. Today is 2026-11-20 (--today).\n"
    code, out = run("status", "--vault", str(FIXTURE), "--today", "2026-11-20")
    assert out.splitlines()[0] == "planner status: 9 apps. Today is 2026-11-20 (--today)."


def test_next_suggests_a_boundary_once_the_strategy_is_decided_and_no_app_exists(tmp_path):
    (tmp_path / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "04-solution-strategy.md").write_text(
        "---\nid: solution-strategy\ntype: initiative-section\ntitle: Solution strategy\nstate: decided\n"
        "owner: \"@lead\"\nauthored: authored\n---\n# Solution strategy\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("planner next: initiative, boundary.")


def test_a_stub_app_page_with_no_containers_goes_back_to_boundary(tmp_path):
    (tmp_path / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "links-building-blocks.md").write_text(
        "---\nid: APP-links\ntype: app-building-blocks\ntitle: Links\nstate: inkling\nchange: new\nstage: baseline\n"
        "owner: \"@lead\"\nauthored: authored\n---\n# Links\n\nIts boundary sheet is still to be read back.\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("planner next: APP-links, boundary APP-links.")


def test_an_unchanged_app_at_assumption_goes_to_discover_not_shape(tmp_path):
    (tmp_path / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "rail-building-blocks.md").write_text(
        "---\nid: APP-rail\ntype: app-building-blocks\ntitle: Rail\nstate: assumption\nchange: unchanged\n"
        "owner: \"@lead\"\nauthored: authored\nsources: [SRC-01]\n---\n# Rail\n\nRail sells rail tickets.\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("planner next: APP-rail, discover APP-rail."), out


def test_check_warns_when_the_vaults_conventions_are_not_the_plugins_and_upgrade_replaces_them(tmp_path):
    (tmp_path / ".planner.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "CONVENTIONS.md").write_text("# Conventions\n\nAn old copy.\n", encoding="utf-8")
    code, out = run("check", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert "CONVENTIONS.md:1: W717" in out
    code, out = run("upgrade", "--vault", str(tmp_path))
    assert code == 0 and out.startswith("planner upgrade: CONVENTIONS.md replaced with the plugin's copy")
    assert (tmp_path / "CONVENTIONS.md").read_bytes() == (REPO / "template" / "CONVENTIONS.md").read_bytes()
    assert "W717" not in run("check", "--vault", str(tmp_path), "--today", "2026-01-15")[1]
    assert run("upgrade", "--vault", str(tmp_path))[1].startswith("planner upgrade: CONVENTIONS.md is already")
