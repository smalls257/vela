"""The plan digest: made from the dashboard's own data, by every build, and by prepare."""
import json
import shutil

from conftest import REPO, run
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
    assert companionstore.plan_digest(root)["version"] == 1


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
