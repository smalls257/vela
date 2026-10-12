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
    assert "changed: CON-002 (consumes, 05-building-blocks/stock-building-blocks.md): text changed, no longer in this app's slice" in out
    assert "removed:" not in out


def test_an_item_deleted_from_the_vault_is_removed(mini):
    hand_off(mini)
    stock = mini / "05-building-blocks/stock-building-blocks.md"
    text = stock.read_text(encoding="utf-8")
    stock.write_text(text[:text.index("### CON-002")], encoding="utf-8")
    code, out = verify(mini)
    assert code == 1
    assert "removed: CON-002 (consumes, 05-building-blocks/stock-building-blocks.md, was fact)" in out


def test_a_resolved_blocking_unknown_is_changed_not_removed(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing", "- **Blocks:** [[stock-building-blocks#CON-002 Stock level|CON-002]]")
    assert hand_off(mini)[0] == 0
    edit(mini / "11-unknowns-and-risks.md", "- **State:** open\n- **Ask by:**", "- **State:** resolved\n- **Ask by:**")
    code, out = verify(mini)
    assert code == 1, out
    assert "changed: UNK-001 (unknown, 11-unknowns-and-risks.md): state open -> resolved, text changed, no longer in this app's slice" in out
    assert "removed:" not in out


def test_a_moved_consumed_contract_is_changed(mini):
    hand_off(mini)
    stock = mini / "05-building-blocks/stock-building-blocks.md"
    text = stock.read_text(encoding="utf-8")
    section = text[text.index("### CON-002"):]
    stock.write_text(text[:text.index("### CON-002")], encoding="utf-8")
    shop = mini / SHOP
    shop.write_text(shop.read_text(encoding="utf-8").rstrip("\n") + "\n\n## Contracts this app consumes\n\n"
                    + section.rstrip("\n") + "\n- **Provider:** Stock\n", encoding="utf-8")
    code, out = verify(mini)
    assert code == 1
    assert f"changed: CON-002 (consumes, {SHOP}): moved from 05-building-blocks/stock-building-blocks.md to {SHOP}" in out


def test_a_damaged_manifest_never_verifies(mini):
    hand_off(mini)
    good = (mini / MANIFEST).read_text(encoding="utf-8")
    lines = good.split("\n")
    damaged = {
        "a deleted row": "\n".join(l for l in lines if not l.startswith("| CON-001 ")),
        "the app row deleted": "\n".join(l for l in lines if not l.startswith("| APP-shop ")),
        "a header-only table": "\n".join(l for l in lines if not (l.startswith("| ") and "| ID |" not in l)),
        "another app": good.replace("- **App:** APP-shop", "- **App:** APP-till"),
        "a duplicated row": good.replace("| CON-001 |", "| CON-002 |", 1),
        "no Commit": good.replace("- **Commit:** abc1234\n", ""),
        "no Written": good.replace("- **Written:** 2026-01-15\n", ""),
        "no Items": good.replace("- **Items:** 3\n", ""),
    }
    for name, text in damaged.items():
        (mini / MANIFEST).write_text(text, encoding="utf-8")
        code, out = verify(mini)
        assert code == 2 and "cannot be read as a manifest" in out, (name, out)


def test_a_row_count_mismatch_names_both_numbers(mini):
    hand_off(mini)
    edit(mini / MANIFEST, "- **Items:** 3", "- **Items:** 4")
    code, out = verify(mini)
    assert code == 2 and "says 4 but the table has 3 rows" in out


def test_write_failures_are_tool_errors_not_tracebacks(mini):
    (mini / "handoffs").write_text("a file where the folder belongs", encoding="utf-8")
    code, out = hand_off(mini)
    assert code == 2 and "cannot write handoffs/APP-shop.md" in out and "Traceback" not in out
    (mini / "handoffs").unlink()
    (mini / "handoffs" / MANIFEST.split("/")[1]).mkdir(parents=True)
    code, out = hand_off(mini, "--replace")
    assert code == 2 and "cannot write handoffs/APP-shop.md" in out
    code, out = verify(mini)
    assert code == 2 and "is a folder, not a manifest file" in out


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


def test_a_reopened_epic_trips_neither_e316_nor_e303(mini):
    (mini / "13-epics").mkdir()
    (mini / "13-epics" / "EPC-001-sell.md").write_text(EPIC, encoding="utf-8")
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing", "- **Blocks:** [[EPC-001-sell|EPC-001]]")
    codes = [c for c, _ in findings(check(mini)[1])]
    assert "E316" not in codes and "E303" not in codes


def test_a_generated_block_inside_an_items_section_does_not_change_its_hash(mini):
    hand_off(mini)
    edit(mini / SHOP, "- **Change policy:** versioned.\n",
         "- **Change policy:** versioned.\n<!-- generated:demo sha=0123abcd: do not edit, run planner render -->\nrendered words\n<!-- /generated:demo -->\n")
    code, out = verify(mini)
    assert "changed: CON-001" not in out


def test_a_manifest_saved_with_crlf_still_reads(mini):
    hand_off(mini)
    path = mini / MANIFEST
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert verify(mini)[0] == 0
