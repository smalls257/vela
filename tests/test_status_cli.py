"""vela status and vela next: the progress grid on the command line."""
from conftest import REPO, edit, run

FIXTURE = REPO / "examples" / "unified-booking"


def test_status_prints_one_line_per_app_with_ages(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Opened:** 2026-01-10", "- **Opened:** 2026-01-10\n- **Blocks:** [[till-building-blocks|Till]]")
    code, out = run("status", "--vault", str(mini), "--today", "2026-02-03")
    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == "vela status: 3 apps, as of 2026-02-03 (the date you gave)."
    assert lines[1].startswith("Till (APP-till) | stage: baseline | 0 early ideas, 1 assumption, 0 facts, 0 decided | "
                               "oldest open question: Till test rig (UNK-001), open 24 days (since 2026-01-10) | "
                               "next: ask about Till test rig (UNK-001). It was due an answer by 2026-02-01")


def test_next_names_one_app_and_mode(mini):
    code, out = run("next", "--vault", str(mini), "--today", "2026-01-15")
    assert code == 0
    assert out == "vela next: Till: find sources for Till (APP-till). Till lists no sources yet. As of 2026-01-15 (the date you gave).\n"


def test_next_on_an_empty_vault_suggests_a_dump(tmp_path):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("vela next: for the whole plan: no app page exists yet") and "/vela:dump" in out


def test_status_with_a_bad_date_is_a_tool_failure(mini):
    assert run("status", "--vault", str(mini), "--today", "soon")[0] == 2
    assert run("next", "--vault", str(mini), "--today", "2026-13-01")[0] == 2


def test_the_fixture_has_nothing_left_to_do_per_app_only_its_requirements_were_never_written():
    # The fixture predates /vela:requirements: every app is settled, but no capability has a requirement.
    code, out = run("next", "--vault", str(FIXTURE), "--today", "2026-11-20")
    assert code == 0
    assert out.startswith("vela next: for the whole plan: write the requirements for ") and "(CAP-" in out, out
    code, out = run("status", "--vault", str(FIXTURE), "--today", "2026-11-20")
    assert out.splitlines()[0] == "vela status: 9 apps, as of 2026-11-20 (the date you gave)."


def test_next_suggests_a_boundary_once_the_strategy_is_decided_and_no_app_exists(tmp_path):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "04-solution-strategy.md").write_text(
        "---\nid: solution-strategy\ntype: initiative-section\ntitle: Solution strategy\nstate: decided\n"
        "owner: \"@lead\"\nauthored: authored\n---\n# Solution strategy\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("vela next: for the whole plan: write the requirements, with /vela:requirements."), out
    (tmp_path / "capabilities").mkdir()
    (tmp_path / "capabilities" / "CAP-001-hold.md").write_text(
        "---\nid: CAP-001\ntype: capability\ntitle: Hold\nstate: assumption\nowner: \"@lead\"\nauthored: authored\n"
        "origin: proposed\nchange: new\n---\n# Hold\n\n## Functional requirements\n\n### CAP-001.FR1 Hold a seat\n\n"
        "- **State:** assumption\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("vela next: for the whole plan: run a boundary session"), out


def test_a_stub_app_page_with_no_containers_goes_back_to_boundary(tmp_path):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "links-building-blocks.md").write_text(
        "---\nid: APP-links\ntype: app-building-blocks\ntitle: Links\nstate: inkling\nchange: new\nstage: baseline\n"
        "stub: boundary\nowner: \"@lead\"\nauthored: authored\n---\n# Links\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("vela next: Links: read back the boundary of Links (APP-links). Links has only a placeholder page")


def test_an_unchanged_app_at_assumption_goes_to_discover_not_shape(tmp_path):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "05-building-blocks").mkdir()
    (tmp_path / "05-building-blocks" / "rail-building-blocks.md").write_text(
        "---\nid: APP-rail\ntype: app-building-blocks\ntitle: Rail\nstate: assumption\nchange: unchanged\n"
        "owner: \"@lead\"\nauthored: authored\nsources: [SRC-01]\n---\n# Rail\n\nRail sells rail tickets.\n", encoding="utf-8")
    code, out = run("next", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert code == 0 and out.startswith("vela next: Rail: find sources for Rail (APP-rail)."), out


def test_check_warns_when_the_vaults_conventions_are_not_the_plugins_and_upgrade_replaces_them(tmp_path):
    (tmp_path / ".vela.yaml").write_text("initiative: INI-001\ntitle: New\n", encoding="utf-8")
    (tmp_path / "CONVENTIONS.md").write_text("# Conventions\n\nAn old copy.\n", encoding="utf-8")
    code, out = run("check", "--vault", str(tmp_path), "--today", "2026-01-15")
    assert "CONVENTIONS.md:1: W717" in out
    code, out = run("upgrade", "--vault", str(tmp_path))
    assert code == 0 and out.startswith("vela upgrade: CONVENTIONS.md replaced with the plugin's copy")
    assert (tmp_path / "CONVENTIONS.md").read_bytes() == (REPO / "plugin" / "template" / "CONVENTIONS.md").read_bytes()
    assert "W717" not in run("check", "--vault", str(tmp_path), "--today", "2026-01-15")[1]
    assert run("upgrade", "--vault", str(tmp_path))[1].startswith("vela upgrade: CONVENTIONS.md is already")


def test_status_ends_with_a_completeness_line_that_never_says_done():
    code, out = run("status", "--vault", str(FIXTURE), "--today", "2026-11-20")
    last = out.strip().splitlines()[-1]
    assert last.startswith("Completeness: ") and "22 of 22 items settled" in last and "done" not in last.lower()
