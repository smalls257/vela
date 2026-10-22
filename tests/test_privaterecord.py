from vela import privaterecord as pr

FULL = """---
id: 2026-10-22-booking-api
type: session
title: "Grill: Booking API"
date: 2026-10-22
modes: [grill]
status: closed
summary: "Decided the booking API."
branch: vela/booking-api
start_commit: 3ede2873
---

# 2026-10-22 Grill: Booking API

## Ready to decide

- CON-004: the lead said yes in 2026-10-22-booking-api (^c03)

## Captures
Harvest declined: PR 41 apps/kiosk.md 4be1c09a7d2e

- [idea] (@maria) "Yes, one booking API." → keep: [[05#CON-003 Booking|CON-003]] (decided) ^c07

## Changes

| ID | From | To | Source |
|---|---|---|---|
| CON-003 | assumption | decided | [[2026-10-22-booking-api#^c07]] |
"""


def test_split_keeps_the_header_and_moves_every_word():
    split = pr.split_record(FULL)
    meta = pr.stub_meta(split.stub)
    assert pr.listed(meta, "ready") == ("CON-004",)
    assert pr.listed(meta, "harvest_declined") == ("PR 41 apps/kiosk.md 4be1c09a7d2e",)
    assert pr.parts(meta) == {1: pr.fingerprint(split.private)}
    assert "summary" not in meta and split.stub.rstrip().endswith("---")
    assert "Yes, one booking API." in split.private and pr.part_of(split.private) == 1
    assert pr.summary_of(split.private) == "Decided the booking API."


def test_reference_grammar_round_trips_and_refuses_anchors():
    assert pr.citation("2026-10-22-booking-api", 2, 7) == "[[2026-10-22-booking-api]] 2.c07"
    assert pr.parse_citation('"[[2026-10-22-booking-api]] c12"') == ("2026-10-22-booking-api", pr.Ref(1, 12))
    assert pr.parse_ref("^2.c07") is None and pr.parse_ref("2.c07") == pr.Ref(2, 7)


def test_anchor_links_rewrite_with_or_without_an_alias():
    text, n = pr.rewrite_anchor_links("see [[2026-10-12-x#^c09]] and [[2026-10-12-x#^c12\\|the lead's account]]")
    assert (text, n) == ("see [[2026-10-12-x]] c09 and [[2026-10-12-x]] c12", 2)


def test_parts_and_claims():
    stub = pr.new_stub("2026-10-22-x", "Grill: x", "2026-10-22", ["grill"])
    assert pr.parts(pr.stub_meta(stub)) == {1: pr.PENDING}
    two = pr.with_part(stub, 2, pr.PENDING)
    assert pr.next_part(pr.stub_meta(two)) == 3


def test_is_private_at_any_depth_and_case():
    assert pr.is_private("sessions/private/x.md") and pr.is_private("plans/a/Sessions/Private/x.md")
    assert not pr.is_private("sessions/x.md")


def test_new_stub_key_order_and_quoting():
    stub = pr.new_stub("2026-10-22-x", 'Grill: "x"', "2026-10-22", ["grill", "challenge"], "vela/x", "abc123", ["CON-1"])
    keys = [line.split(":")[0] for line in stub.split("\n")[1:-2]]
    assert keys == ["id", "type", "title", "date", "modes", "status", "branch", "start_commit", "captures_sha256",
                    "challenges"]
    assert 'title: "Grill: \\"x\\""' in stub and 'captures_sha256: {1: "pending"}' in stub
    meta = pr.stub_meta(stub)
    assert meta["title"] == 'Grill: "x"' and meta["modes"] == ["grill", "challenge"]


def test_new_private_and_summary_round_trip():
    text = pr.new_private("2026-10-22-x", "Grill: x", "2026-10-22", 2)
    assert pr.part_of(text) == 2 and pr.summary_of(text) == "In progress."
    assert "# 2026-10-22 Grill: x\n\n## Captures\n\n## Changes\n" in text
    again = pr.with_summary(text, "Done: it works.")
    assert pr.summary_of(again) == "Done: it works." and again.endswith(text.split("---\n", 2)[2])


def test_part_of_refuses_a_file_that_does_not_say():
    import pytest
    with pytest.raises(ValueError):
        pr.part_of("---\nid: x\n---\n")
    with pytest.raises(ValueError):
        pr.stub_meta("no frontmatter")


def test_synced_stub_on_one_combined_file_keeps_the_body():
    synced = pr.synced_stub(FULL, FULL)
    assert synced.endswith(FULL.split("---\n", 2)[2])
    assert pr.listed(pr.stub_meta(synced), "ready") == ("CON-004",)
    assert pr.stub_meta(synced)["summary"] == "Decided the booking API."


def test_with_lists_drops_an_emptied_list():
    split = pr.split_record(FULL)
    cleared = pr.with_lists(split.stub, {"ready": [], "harvest_declined": []})
    assert "ready" not in pr.stub_meta(cleared) and "harvest_declined" not in pr.stub_meta(cleared)


def test_challenge_session_records_its_item():
    full = FULL.replace("modes: [grill]", "modes: [challenge]").replace("Grill: Booking API", "Challenge: CON-003 booking")
    assert pr.listed(pr.stub_meta(pr.split_record(full).stub), "challenges") == ("CON-003",)


def test_second_part_is_keyed_by_its_number():
    assert list(pr.parts(pr.stub_meta(pr.split_record(FULL, 2).stub))) == [2]
