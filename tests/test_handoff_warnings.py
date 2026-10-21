"""At handoff the lead, and through the manifest the senior, hear what is not firm: drafts, missing case tables, providers
nobody has designed, and a manifest pinned to a commit that is gone."""
import shutil
import subprocess

import pytest

from conftest import REPO, check, findings, run
from vela import cli, handoff, handoffwarn

HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron"
APP = "APP-desktop-agent"
TODAY = "2026-10-13"


@pytest.fixture
def heron(tmp_path):
    dest = tmp_path / "heron"
    shutil.copytree(HERON, dest)
    return dest


def codes(out):
    return [code for code, _ in findings(out)]


def test_the_gaps_name_each_unfirm_item_each_missing_table_and_each_undesigned_provider(heron):
    vault = cli.load_vault(heron)
    app = next(a for a in vault.apps if a.id == APP)
    found = handoffwarn.gaps(vault, app)
    assert {g.kind for g in found} == {"unfirm", "no-case-table", "no-designer"}
    text = "\n".join(g.sentence for g in found)
    assert "Consent check (CON-003) is not decided yet" in text
    assert "acceptance criteria" in text  # epics and requirements say their criteria are not firm either
    assert "on Consent and identity, but no team has taken Consent and identity or designed it yet" in text


def test_check_warns_for_an_app_at_handoff(heron):
    _, out = check(heron, TODAY)
    assert {"W386", "W387", "W380"} <= set(codes(out))


def test_an_app_not_at_handoff_draws_no_handoff_warning(heron):
    # the same vault with the app taken off the handoff stage: its drafts are ordinary work in progress
    page = heron / "05-building-blocks" / "desktop-agent-building-blocks.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace("stage: handoff\n", "stage: target\n").replace('handed_off: "@agent-lead, 2026-10-12"\nhanded_off_pr: pending\n', ""),
                    encoding="utf-8")
    _, out = check(heron, TODAY)
    assert "W386" not in codes(out) and "W387" not in codes(out)


def test_next_prints_what_is_not_firm(heron):
    _, out = run("next", "--vault", str(heron), "--today", TODAY)
    assert "vela next: Desktop agent has been handed to its team, but" in out and "not settled yet:" in out
    assert "  - Consent check (CON-003) is not decided yet" in out


def test_handoff_says_it_and_writes_it_into_the_manifest(heron):
    code, out = run("handoff", APP, "--vault", str(heron), "--today", TODAY, "--commit", "abc1234", "--replace")
    assert code == 0, out
    assert "not settled yet. Tell the app's team before they accept it" in out and "Consent check (CON-003)" in out
    manifest = (heron / "handoffs" / f"{APP}.md").read_text(encoding="utf-8")
    assert handoff.NOT_FIRM_HEADING in manifest and "Consent check (CON-003) is not decided yet" in manifest
    facts, entries = handoff.read(manifest)  # the senior's reader still parses a manifest with the list in it
    assert facts["App"] == APP and entries


def vcs(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def test_a_manifest_must_pin_a_commit_that_exists(heron):
    vcs(heron, "init", "-q")
    vcs(heron, "add", "-A")
    vcs(heron, "commit", "-q", "-m", "start")
    real = vcs(heron, "rev-parse", "--short", "HEAD")
    run("handoff", APP, "--vault", str(heron), "--today", TODAY, "--commit", real, "--replace")
    assert "W388" not in codes(check(heron, TODAY)[1])
    run("handoff", APP, "--vault", str(heron), "--today", TODAY, "--commit", "0f0b523", "--replace")
    _, out = check(heron, TODAY)
    assert ("W388", f"handoffs/{APP}.md") in findings(out)


def test_the_guide_and_conventions_agree_that_epics_follow_handoff():
    guide = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
    conventions = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert 'H --> J["handoff' in guide and 'J --> I["/vela:epics' in guide
    assert "Epics come after handoff" in guide and "Epics come after handoff" in conventions
