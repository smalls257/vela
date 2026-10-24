"""--for-lead on a small plan: every decision said, wording counted, close's own fixes counted; plain check unchanged."""
import shutil

import pytest

from conftest import REPO, check, findings, run
from sizing_vault import choose
from vela import cli, leadview, rules, say, schema, sizing

FIXTURE = REPO / "tests" / "fixtures" / "small-two-apps"
EXAMPLE = REPO / "examples" / "unified-booking"
TODAY = "2026-10-23"


def copy(src, tmp_path, band=None, name="plan"):
    root = tmp_path / name
    shutil.copytree(src, root)
    if band:
        with (root / ".vela.yaml").open("a", encoding="utf-8") as fh:
            fh.write(choose(band))
    return root


def test_small_for_lead_says_decisions_and_counts_the_rest(tmp_path):
    root = copy(FIXTURE, tmp_path)
    vault = cli.load_vault(root)
    found = rules.check(vault, TODAY)
    view = leadview.split(vault, found, sizing.of(vault))
    assert {schema.WEIGHT[f.code] for f in view.said} <= {"decision"} | {w for w in schema.WEIGHT.values() if w.startswith("scale:")} | {"auto"}
    assert all(schema.WEIGHT[f.code] == "polish" for f in view.wording)
    assert len(view.said) + len(view.wording) + len(view.fixed) == len(found)
    out = run("check", "--vault", str(root), "--today", TODAY, "--for-lead", "--more")[1]
    if view.wording:
        n = len(view.wording)
        count = f"{say.count_words(n)} wording note{'' if n == 1 else 's'}"
        assert f"There {'is' if n == 1 else 'are'} also {count} on the pages; want {'it' if n == 1 else 'them'}?" in out


def test_medium_says_the_wording_notes(tmp_path):
    root = copy(FIXTURE, tmp_path, "medium")
    vault = cli.load_vault(root)
    assert leadview.split(vault, rules.check(vault, TODAY), sizing.of(vault)).wording == ()


@pytest.mark.parametrize("band", ["small", "medium", "large"])
def test_plain_check_is_the_same_at_every_size_but_the_scale_codes(tmp_path, band):
    # both sides are copies, so git state and folder shape match and the band is the only difference
    scale = {c for c, w in schema.WEIGHT.items() if w.startswith("scale:")}
    base = {f for f in findings(check(copy(EXAMPLE, tmp_path, name="measured"), TODAY)[1]) if f[0] not in scale}
    forced = {f for f in findings(check(copy(EXAMPLE, tmp_path, band, name="forced"), TODAY)[1]) if f[0] not in scale}
    assert forced == base


def with_one_domain(root):
    # no example app names a domain today, so W352 is silent; one domain makes the other apps owe theirs
    page = root / "05-building-blocks" / "booking-building-blocks.md"  # an app page; the folder's index also ends -building-blocks
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace("\nchange: ", "\ndomain: Sales\nchange: ", 1), encoding="utf-8")
    return root


def test_domains_are_asked_for_only_on_a_large_plan(tmp_path):
    large = with_one_domain(copy(EXAMPLE, tmp_path, name="large"))  # the example measures large
    assert "W352" in check(large, TODAY)[1]
    medium = with_one_domain(copy(EXAMPLE, tmp_path, "medium", name="medium"))
    assert "W352" not in check(medium, TODAY)[1]
    assert not hasattr(schema, "DOMAIN_MIN_APPS")


def test_the_growth_line_comes_with_the_next_for_lead_once(tmp_path):
    root = copy(FIXTURE, tmp_path)
    # an open session in the fixture copy, as tests/test_size_cli.open_session writes it
    from test_size_cli import open_session
    open_session(root)
    first = run("next", "--vault", str(root), "--today", TODAY, "--for-lead")[1]
    again = run("next", "--vault", str(root), "--today", TODAY, "--for-lead")[1]
    assert "I'm treating this as a small plan" in first and "I'm treating this as a small plan" not in again
