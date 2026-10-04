"""planner handoff: the manifest of what a senior accepted, and verify against it. Plus the
reopened epic state a senior's challenge leads to."""
from conftest import check, edit, findings, run
from planner import viewer

SHOP = "05-building-blocks/shop-building-blocks.md"
MANIFEST = "handoffs/APP-shop.md"


def hand_off(mini, *extra):
    return run("handoff", "APP-shop", "--vault", str(mini), "--today", "2026-01-15", "--commit", "abc1234", *extra)


def verify(mini):
    return run("handoff", "verify", "APP-shop", "--vault", str(mini))


def test_manifest_lists_the_slice_with_states_and_hashes(mini):
    code, out = hand_off(mini)
    assert code == 0, out
    assert out == "planner handoff: wrote handoffs/APP-shop.md, 3 items, at abc1234.\n"
    text = (mini / MANIFEST).read_text(encoding="utf-8")
    assert text.startswith("# Handoff manifest: APP-shop\n\n- **App:** APP-shop\n- **Commit:** abc1234\n- **Written:** 2026-01-15\n")
    rows = [line for line in text.splitlines() if line.startswith("| ") and "---" not in line][1:]
    assert [r.split(" | ")[:4] for r in rows] == [
        ["| APP-shop", "app", SHOP, "decided"],
        ["| CON-001", "provides", SHOP, "decided"],
        ["| CON-002", "consumes", "05-building-blocks/stock-building-blocks.md", "fact"]]


def test_check_never_reads_the_manifest(mini):
    hand_off(mini)
    code, out = check(mini)
    assert code == 0 and "in 12 pages" in out


def test_verify_is_clean_right_after_and_exits_0(mini):
    hand_off(mini)
    code, out = verify(mini)
    assert code == 0
    assert out == "planner handoff verify APP-shop: 0 changed, 0 added, 0 removed since the handoff at abc1234 on 2026-01-15.\n"


def test_a_changed_contract_is_listed_and_exits_1(mini):
    hand_off(mini)
    edit(mini / SHOP, "- **Change policy:** versioned.", "- **Change policy:** versioned, kept 3 months.")
    code, out = verify(mini)
    assert code == 1
    assert f"changed: CON-001 (provides, {SHOP}): text changed" in out


def test_a_state_change_is_named(mini):
    hand_off(mini)
    edit(mini / "05-building-blocks/stock-building-blocks.md", "- **State:** fact", "- **State:** assumption")
    code, out = verify(mini)
    assert code == 1
    assert "changed: CON-002 (consumes, 05-building-blocks/stock-building-blocks.md): state fact -> assumption, text changed" in out


def test_render_reverify_and_handed_off_are_not_changes(mini):
    hand_off(mini)
    edit(mini / SHOP, "authored: mixed\n", "authored: mixed\nlast_verified: 2026-01-15\nverified_by: \"@mini-lead\"\n"
         "handed_off: \"Shop senior, 2026-01-15, PR #4\"\n")
    edit(mini / "05-building-blocks/stock-building-blocks.md", "the existing read API, no change.", "the existing read API.")
    run("render", "--vault", str(mini))  # rewrites Shop's contracts-consumed block
    code, out = verify(mini)
    assert "changed: APP-shop" not in out
    assert "changed: CON-002" in out and code == 1


def test_a_new_blocking_unknown_is_added_but_does_not_fail(mini):
    hand_off(mini)
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing", "- **Blocks:** [[shop-building-blocks#CON-001 Sale API|CON-001]]")
    code, out = verify(mini)
    assert code == 0
    assert "added: UNK-001 (unknown, 11-unknowns-and-risks.md, open)" in out


def test_an_item_gone_from_the_slice_is_removed_and_fails(mini):
    hand_off(mini)
    edit(mini / "05-building-blocks/stock-building-blocks.md", "[[shop-building-blocks|Shop]]", "none")
    code, out = verify(mini)
    assert code == 1
    assert "removed: CON-002 (consumes, 05-building-blocks/stock-building-blocks.md, was fact)" in out


def test_an_existing_manifest_is_kept_unless_replaced(mini):
    hand_off(mini)
    before = (mini / MANIFEST).read_bytes()
    edit(mini / SHOP, "- **Change policy:** versioned.", "- **Change policy:** versioned, kept 3 months.")
    code, out = hand_off(mini)
    assert code == 1 and "is what the senior accepted" in out
    assert (mini / MANIFEST).read_bytes() == before
    assert hand_off(mini, "--replace")[0] == 0
    assert verify(mini)[0] == 0


def test_two_writes_give_the_same_bytes(mini):
    hand_off(mini)
    first = (mini / MANIFEST).read_bytes()
    hand_off(mini, "--replace")
    assert (mini / MANIFEST).read_bytes() == first


def test_a_vault_with_errors_is_not_handed_off(mini):
    edit(mini / "README.md", "authored: authored", "authored: by hand")
    code, out = hand_off(mini)
    assert code == 1 and "wrote nothing, planner check has 1 errors" in out
    assert not (mini / "handoffs").exists()


def test_tool_failures_exit_2(mini):
    assert run("handoff", "APP-nowhere", "--vault", str(mini))[0] == 2
    assert run("handoff", "goals", "--vault", str(mini))[0] == 2
    assert verify(mini)[0] == 2  # no manifest yet
    (mini / "handoffs").mkdir()
    (mini / MANIFEST).write_text("# not a manifest\n", encoding="utf-8")
    code, out = verify(mini)
    assert code == 2 and "cannot be read as a manifest" in out
    assert run("handoff", "verify", "--vault", str(mini))[0] == 2
    assert run("handoff", "APP-shop", "APP-till", "--vault", str(mini))[0] == 2


def test_a_hand_edited_row_is_a_tool_failure(mini):
    hand_off(mini)
    edit(mini / MANIFEST, "| CON-001 | provides |", "| CON-001 | provided |")
    code, out = verify(mini)
    assert code == 2 and "not a manifest row" in out


# reopened: a senior's challenge after handoff can send an epic back.

EPIC = """---
id: EPC-001
type: epic
title: Sell
state: reopened
owner: "@mini/shop-team"
authored: mixed
apps: [APP-shop]
delivers: [CON-001]
---

# EPC-001 Sell
"""


def test_reopened_is_an_epic_state_and_counts_as_not_decided(mini):
    (mini / "13-epics").mkdir()
    (mini / "13-epics" / "EPC-001-sell.md").write_text(EPIC, encoding="utf-8")
    edit(mini / SHOP, "authored: mixed\n", "authored: mixed\nsources: [SRC-01]\n")
    assert "E105" not in [c for c, _ in findings(check(mini)[1])]
    _, out = run("status", "--vault", str(mini), "--today", "2026-01-15")
    assert "next: epics EPC-001. Every contract of APP-shop is settled, and EPC-001 is reopened." in out
    assert "reopened" in viewer.DRAFT_STATES


def test_a_manifest_saved_with_crlf_still_reads(mini):
    hand_off(mini)
    path = mini / MANIFEST
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert verify(mini)[0] == 0
