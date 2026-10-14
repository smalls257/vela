"""`vela handoff preview APP` (overhaul Task 21h): what a handoff would leave unmet, read before anyone hands over.

The grill's HANDOFF.md had the model work out the checklist and the not-settled list by hand from `ladder`, `next`
and `check`; these tests hold the command that lists them instead, from the same readers the handoff record uses."""
import json
import shutil

import pytest

from conftest import MINI, REPO, edit, run
from test_slices import with_kiosk_flow

from vela import say

EXAMPLE = REPO / "examples" / "unified-booking"
TODAY = "2026-10-14"
SHOP = "05-building-blocks/shop-building-blocks.md"


@pytest.fixture
def example(tmp_path):
    vault = tmp_path / "ex"
    shutil.copytree(EXAMPLE, vault)
    with_kiosk_flow(vault)
    return vault


@pytest.fixture
def draft_shop(tmp_path):
    """The mini vault with its Shop app set back to draft: the checklist's "the app itself is decided" fails, and the
    not-settled list says nobody has said yes to it."""
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    edit(vault / SHOP, "state: decided\nchange: new", "state: draft\nchange: new")
    return vault


def preview(vault, app, *extra):
    return run("handoff", "preview", app, "--vault", str(vault), "--today", TODAY, *extra)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_preview_lists_unmet_checklist(draft_shop):
    code, out = preview(draft_shop, "APP-shop")
    assert code == 1, out
    assert out.startswith("vela handoff preview APP-shop: Shop (APP-shop) doesn't meet the handoff checklist yet: ")
    assert "- the app itself is still a draft" in out
    assert "- its runtime page has no section on what happens when things fail" in out
    data = json.loads(preview(draft_shop, "APP-shop", "--json")[1])
    assert data["ready"] is False and "the app itself is still a draft" in data["checklist_not_met"]


def test_preview_meets_the_checklist_and_exits_0(example):
    code, out = preview(example, "APP-kiosks")
    assert code == 0, out
    assert out.startswith("vela handoff preview APP-kiosks: Port kiosks (APP-kiosks) meets the handoff checklist.")


def test_preview_lists_not_settled(draft_shop):
    code, out = preview(draft_shop, "APP-shop")
    assert "not settled at handoff" in out and "the app's team" in out
    assert "still a draft or not decided yet" in out
    assert "- Shop (APP-shop) is still a draft: nobody has said yes to it." in out
    data = json.loads(preview(draft_shop, "APP-shop", "--json")[1])
    assert data["not_settled"] == ["Shop (APP-shop) is still a draft: nobody has said yes to it."]


def test_preview_includes_flow_check_standing(example):
    code, out = preview(example, "APP-kiosks")
    assert "- SLC-003 Kiosks book through Booking in the March image: not checked. No full flow check of it has been recorded yet." in out
    run("check-slice", "SLC-003", "--vault", str(example), "--today", TODAY)  # writes the record the preview reads
    code, out = preview(example, "APP-kiosks")
    assert "Flow checks, as recorded:" in out
    assert f"- SLC-003 Kiosks book through Booking in the March image: not fully checked, recorded {TODAY}" in out
    data = json.loads(preview(example, "APP-kiosks", "--json")[1])
    assert data["flow_checks"] == [{"slice": "SLC-003", "name": "Kiosks book through Booking in the March image",
                                    "state": "not fully checked", "words": "not fully checked", "checked": TODAY,
                                    "open": [], "line": f"not fully checked, recorded {TODAY}"}]


def test_preview_says_when_the_app_is_on_no_slice(draft_shop):
    out = preview(draft_shop, "APP-shop")[1]
    assert "Shop is on no slice, so there is no flow check to report." in out


def test_preview_writes_nothing(example, draft_shop):
    for vault, app in ((example, "APP-kiosks"), (draft_shop, "APP-shop")):
        before = snapshot(vault)
        for mode in ((), ("--json",), ("--for-lead",)):
            preview(vault, app, *mode)
        assert snapshot(vault) == before  # the example's own handoff records included
        assert not (vault / ".vela").exists()


def test_preview_refuses_an_id_that_is_not_an_app(example):
    code, out = preview(example, "CON-001")
    assert code == 2 and "is not the id of an app's building-blocks page" in out


def test_preview_refuses_the_handoffs_own_flags(draft_shop):
    code, out = preview(draft_shop, "APP-shop", "--replace")
    assert code == 2 and "--replace" in out and not (draft_shop / "handoffs").exists()


def test_handoff_and_verify_unchanged(tmp_path):
    vault = tmp_path / "mini"
    shutil.copytree(MINI, vault)
    code, out = run("handoff", "APP-shop", "--vault", str(vault), "--today", "2026-01-15", "--commit", "abc1234")
    assert code == 0, out
    assert out == ("vela handoff: wrote the handoff record for Shop (APP-shop), handoffs/APP-shop.md: 3 things its team "
                   "takes on, as of commit abc1234.\n")
    code, out = run("handoff", "verify", "APP-shop", "--vault", str(vault))
    assert code == 0
    assert out == ("vela handoff verify APP-shop: since Shop was handed off on 2026-01-15 at abc1234, 0 things changed, "
                   "0 added and 0 removed.\n")
    code, out = run("handoff", "--vault", str(vault))
    assert code == 2
    # the output flags are the preview's; on the handoff itself they would be ignored, so they are refused
    code, out = run("handoff", "APP-shop", "--vault", str(vault), "--json")
    assert code == 2 and "preview" in out


def test_for_lead_passes_the_leak_check(example, draft_shop):
    run("check-slice", "SLC-003", "--vault", str(example), "--today", TODAY)
    for vault, app in ((example, "APP-kiosks"), (draft_shop, "APP-shop")):
        code, out = preview(vault, app, "--for-lead")
        assert code in (0, 1), out
        assert "vela bug" not in out
        for line in out.splitlines():
            assert say.leak_in(line) is None, line
    out = preview(draft_shop, "APP-shop", "--for-lead")[1]
    assert "- Shop is still a draft: nobody has said yes to it." in out
    assert "still a draft or not decided yet" in out
    out = preview(example, "APP-kiosks", "--for-lead")[1]
    assert f"- Kiosks book through Booking in the March image: not fully checked, recorded {TODAY}" in out
