"""The plan digest: made from the dashboard's own data, by every build, and by prepare."""
import json
import shutil

from conftest import REPO, run
from vela import companionplan
from vela.edge import companionstore, vaultfiles

EXAMPLE = REPO / "examples" / "unified-booking"


def test_explore_writes_the_digest_beside_the_dashboard(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(EXAMPLE, root)
    code, text = run("explore", str(root), "--today", "2026-10-24")
    assert code == 0, text
    got = companionstore.plan_digest(root)
    assert got["fingerprint"] == vaultfiles.fingerprint(root)
    assert got["names"]["FLO-001"]["name"] == "Hold, pay, confirm"
    assert any(a["id"] == "UNK-008" and a["ask_by"] == "2026-12-15" for a in got["asks"])
    assert {f["key"] for f in got["flows"]} >= {"FLO-001", "FLO-002", "FLO-003"}


def test_prepare_makes_the_same_digest_without_a_page(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(EXAMPLE, root)
    code, text = run("companion", "prepare", "--vault", str(root), "--today", "2026-10-24")
    assert code == 0 and "Prepared the plan's data" in text, text
    assert not (root / "dashboard.html").exists()
    assert companionstore.plan_digest(root)["version"] == companionplan.VERSION


def test_a_publish_leaves_no_digest_in_the_owners_vault(tmp_path):
    from sharing import make_vault
    vault = make_vault(tmp_path)
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "copy.zip"), "--today", "2026-10-24")
    assert code == 0, text
    assert not (vault / ".vela" / "companion" / "plan.json").exists()


def test_opening_a_copy_prepares_it_once(tmp_path):
    from sharing import make_vault
    vault = make_vault(tmp_path)
    run("publish", "--vault", str(vault), "--out", str(tmp_path / "copy"), "--today", "2026-10-24")
    code, text = run("open", str(tmp_path / "copy"), "--into", str(tmp_path / "ws"), "--author", "Dana", "--today", "2026-10-24")
    assert code == 0, text
    got = companionstore.plan_digest(tmp_path / "ws")
    assert got["made"]["from"] == "a published copy" and got["fingerprint"] == vaultfiles.fingerprint(tmp_path / "ws")


RELEASES = ("---\nid: releases\ntype: initiative-section\ntitle: Releases\nstate: assumption\nowner: \"@hl-solution-lead\"\n"
            "authored: authored\n---\n\n# Releases\n\nTwo dates.\n\n## Release one: website\n\n- **Target:** 2026-10-01\n"
            "- **State:** assumption\n- **Slices:** SLC-001\n\n## Release two: call center\n\n- **Target:** 2027-02-01\n"
            "- **State:** assumption\n- **Slices:** SLC-002, SLC-004\n")


def test_each_release_carries_the_slices_that_name_it_and_each_slice_what_it_can_be_held_up_through(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(EXAMPLE, root)
    (root / "04b-releases.md").write_text(RELEASES, encoding="utf-8")
    assert run("companion", "prepare", "--vault", str(root), "--today", "2026-10-24")[0] == 0
    digest = companionstore.plan_digest(root)
    assert {r["name"]: r["slices"] for r in digest["releases"]} == {
        "Release one: website": ["SLC-001"], "Release two: call center": ["SLC-002", "SLC-004"]}
    assert all(s["reach"] for s in digest["slices"])
