"""Slices: one page each, read by slices.read_slices and nothing else, and the check rules on them.

The example carries four slice pages derived from its rollout text; the flow-check rules (W395, E398, overrides on a
slice page) run on a flow checker fixture with a slice page added, because only there does a flow check finish.
"""
import shutil
import sys

import pytest

from conftest import REPO, run

sys.path.insert(0, str(REPO / "plugin" / "lib"))
from vela import cli, model, parse, slices  # noqa: E402

EXAMPLE = REPO / "examples" / "unified-booking"
FLOWCHECK = REPO / "tests" / "fixtures" / "flowcheck"
TODAY = "2026-11-20"


def page(sid, title, *bullets, extra=""):
    body = "".join(f"- {b}\n" for b in bullets)
    return (f"---\nid: {sid}\ntype: slice\ntitle: {title}\nauthored: authored\n---\n\n# {title}\n\n"
            f"What this slice makes work, in a sentence.\n\n{body}{extra}\n## History\n\n- 2026-11-20: written.\n")


def vault_of(*pages):
    return model.build([parse.parse_page(f"slices/{sid}-x.md", text) for sid, text in pages], {})


@pytest.fixture
def example(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(EXAMPLE, vault)
    return vault


def write(vault, sid, text):
    (vault / "slices").mkdir(exist_ok=True)
    for old in (vault / "slices").glob(f"{sid}-*.md"):
        old.unlink()
    (vault / "slices" / f"{sid}-x.md").write_text(text, encoding="utf-8")


def lines(vault, code, today=TODAY):
    out = run("check", "--vault", str(vault), "--today", today)[1]
    return [line for line in out.splitlines() if f" {code} " in line]


# --- the reader ---------------------------------------------------------------------------------------------------

def test_a_slice_page_is_read_for_every_field():
    v = vault_of(("SLC-002", page("SLC-002", "The digest reaches a pilot user", "**Status:** Journey  passes",
                                  "**Flows:** [[FLO-002-get-morning-digest|FLO-002]], [[FLO-001-a|FLO-001]]",
                                  "**After:** SLC-001 (the tracer)",
                                  "**Ships switched off:** a per-user flag", "**Done when:** the digest journey passes",
                                  "**Owner:** @lead", "**Milestone:** Pilot", "**Journey due:** 2026-11-28",
                                  "**Journey:** passed 2026-11-30 by @desk-senior, [the run](https://ci.example/1)",
                                  extra="\n## Not in this slice\n\n- Transcripts (CAP-001.FR1): waits on the review\n")))
    (s,) = slices.read_slices(v)
    assert (s.id, s.name, s.key, s.flows, s.after, s.joins) == ("SLC-002", "The digest reaches a pilot user", "SLC-002",
                                                                  ("FLO-002", "FLO-001"), ("SLC-001",), ())
    assert s.journey_due == "2026-11-28" and not slices.journey_overdue(s, "2026-12-01")  # the journey is recorded
    assert s.status == "journey passes" and s.at_least("building") and not s.at_least("live but off")
    assert (s.ships_off, s.done_when, s.owner, s.milestone) == ("a per-user flag", "the digest journey passes", "@lead", "Pilot")
    assert s.journey.date == "2026-11-30" and s.journey.by == "@desk-senior" and not s.journey.problem
    assert [(left.ids, left.reason) for left in s.not_in] == [(("CAP-001.FR1",), "waits on the review")]
    assert s.path == "slices/SLC-002-x.md" and s.from_page


def test_slices_come_in_after_order_ties_by_id_and_a_circle_is_found():
    v = vault_of(("SLC-003", page("SLC-003", "c", "**After:** SLC-002")), ("SLC-002", page("SLC-002", "b", "**After:** SLC-001")),
                 ("SLC-001", page("SLC-001", "a")), ("SLC-004", page("SLC-004", "d", "**After:** SLC-001")))
    found = slices.read_slices(v)
    assert [s.id for s in found] == ["SLC-001", "SLC-002", "SLC-003", "SLC-004"]
    assert [s.order for s in found] == [0, 1, 2, 3] and slices.tracer(found).id == "SLC-001"
    assert slices.upstream(found, found[2]) == {"SLC-001", "SLC-002", "SLC-003"}
    assert slices.cycles(found) == []
    loop = vault_of(("SLC-001", page("SLC-001", "a", "**After:** SLC-002")), ("SLC-002", page("SLC-002", "b", "**After:** SLC-001")))
    assert slices.cycles(slices.read_slices(loop)) == [("SLC-001", "SLC-002")]
    assert slices.tracer(slices.read_slices(loop)) is None  # every slice names an After: none is the tracer


def test_the_tracer_is_the_one_slice_with_no_after_whatever_its_id():
    v = vault_of(("SLC-001", page("SLC-001", "a", "**After:** SLC-002")), ("SLC-002", page("SLC-002", "b")))
    assert slices.tracer(slices.read_slices(v)).id == "SLC-002"


def test_w406_two_slices_with_no_after_or_none_at_all(example):
    write(example, "SLC-004", page("SLC-004", "d", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]"))
    assert lines(example, "W406") == [
        "slices/SLC-004-x.md:12: W406 SLC-001 and SLC-004 name no After, and only the tracer comes after nothing, so SLC-001 stands in "
        "as the tracer by its ID. Fix: Give SLC-004 an After line naming the slice it builds on (the tracer, SLC-001, if nothing else)."]
    write(example, "SLC-004", page("SLC-004", "d", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001"))
    assert lines(example, "W406") == []
    write(example, "SLC-001", page("SLC-001", "a", "**Flows:** [[FLO-001-hold-pay-confirm|FLO-001]]", "**After:** SLC-004"))
    found = lines(example, "W406")
    assert len(found) == 1 and "Every slice names an After, so none is the tracer" in found[0]


def test_without_slice_pages_the_releases_page_is_read_and_each_release_comes_after_the_last():
    text = ("---\nid: releases\ntype: initiative-section\ntitle: Releases\n---\n\n# Releases\n\n## Release one: pilot\n\n"
            "- **State:** assumption\n- **Tracer:** [[FLO-001-a|FLO-001]], thin\n\n## Release two: more\n\n"
            "- **State:** assumption\n- **Flows:** [[FLO-002-b|FLO-002]]\n")
    found = slices.read_slices(model.build([parse.parse_page("04b-releases.md", text)], {}))
    assert [(s.key, s.after) for s in found] == [("Release one: pilot", ()), ("Release two: more", ("Release one: pilot",))]
    assert not slices.on_pages(model.build([parse.parse_page("04b-releases.md", text)], {}))


def test_a_release_names_its_slices_as_a_milestone(example):
    vault = cli.load_vault(example)
    assert slices.milestones(vault) == {}
    (example / "04b-releases.md").write_text(
        "---\nid: releases\ntype: initiative-section\ntitle: Releases\nstate: assumption\nowner: \"@hl-solution-lead\"\n"
        "authored: authored\n---\n\n# Releases\n\nOne milestone.\n\n## Release one: website\n\n- **Target:** 2027-02-01\n"
        "- **State:** assumption\n- **Slices:** SLC-001, SLC-004\n", encoding="utf-8")
    marked = slices.milestones(cli.load_vault(example))
    assert sorted(marked) == ["SLC-001", "SLC-004"] and marked["SLC-001"][0].name == "Release one: website"


KIOSK_FLOW = """---
id: FLO-009
type: flow
title: A kiosk books
state: assumption
owner: "@hl-solution-lead"
authored: authored
---

# A kiosk books

A customer at a kiosk holds a seat, and Booking checks capacity.

## Steps

1. [[kiosks-building-blocks|Kiosks]] → [[booking-building-blocks|Booking]]: holds a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]].
2. [[booking-building-blocks|Booking]] → [[vessel-schedule-building-blocks|Vessel schedule]]: checks capacity, over [[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]].
3. [[booking-building-blocks|Booking]] → [[kiosks-building-blocks|Kiosks]]: answers with the hold, over [[booking-building-blocks#CON-001 Booking API|Booking API]].
"""


def with_kiosk_flow(vault):
    """The example's flows predate step pairs, so they name no joins; a kiosk flow in the current form does."""
    (vault / "06-runtime" / "flows" / "FLO-009-a-kiosk-books.md").write_text(KIOSK_FLOW, encoding="utf-8")
    path = next((vault / "slices").glob("SLC-003-*.md"))
    path.write_text(path.read_text(encoding="utf-8").replace("[[FLO-001-hold-pay-confirm|FLO-001]]", "[[FLO-009-a-kiosk-books|FLO-009]]"),
                    encoding="utf-8")
    return path


def test_a_slice_reads_its_joins_from_its_flows_steps_with_both_sides(example):
    with_kiosk_flow(example)
    vault = cli.load_vault(example)
    s = next(x for x in slices.read_slices(vault) if x.id == "SLC-003")
    assert s.joins == ("CON-001", "CON-004")  # in step order, each once: the answer over CON-001 adds nothing
    assert s.sides == (("CON-001", "Kiosks", "Booking"), ("CON-004", "Booking", "Vessel schedule"))


def test_the_slices_an_app_takes_part_in(example):
    with_kiosk_flow(example)
    vault = cli.load_vault(example)
    found = slices.read_slices(vault)
    kiosks = next(a for a in vault.apps if a.id == "APP-kiosks")
    booking = next(a for a in vault.apps if a.id == "APP-booking")
    website = next(a for a in vault.apps if a.id == "APP-website")
    # FLO-001 names who sends in each of its three starts, so the website, the call center and the kiosks are in the slices that hold it
    assert [s.id for s in slices.for_app(vault, found, kiosks)] == ["SLC-001", "SLC-002", "SLC-003"]
    assert [s.id for s in slices.for_app(vault, found, booking)] == ["SLC-001", "SLC-002", "SLC-003"]  # it provides a contract the slices join
    assert [s.id for s in slices.for_app(vault, found, website)] == ["SLC-001", "SLC-002"]
    pricing = next(a for a in vault.apps if a.id == "APP-pricing")
    assert slices.for_app(vault, found, pricing) == []  # FLO-002 names no step pairs, so no joins


# --- the vault rules ---------------------------------------------------------------------------------------------

def test_the_example_slices_are_clean_but_for_their_flow_check():
    out = run("check", "--vault", str(EXAMPLE), "--today", TODAY)[1]
    assert not [line for line in out.splitlines() if "slices/" in line and " W391 " not in line]


def test_e346_a_status_that_is_not_one_of_the_five(example):
    write(example, "SLC-004", page("SLC-004", "d", "**Status:** done", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001"))
    assert lines(example, "E346") == ["slices/SLC-004-x.md:12: E346 SLC-004 has Status 'done'. Fix: Write one of planned, building, "
                                      "journey passes, live but off, on, or leave Status out until a Grill plans the slice."]


def test_w392_a_slice_with_no_flows_and_w345_for_the_tracer(example):
    write(example, "SLC-004", page("SLC-004", "d", "**After:** SLC-001"))
    assert [line.split(": ", 1)[1].split(" Fix:")[0] for line in lines(example, "W392")] == ["W392 SLC-004 names no flows, so it proves no journey and the flow check has nothing to run."]
    write(example, "SLC-001", page("SLC-001", "a", "**Flows:** none, the first cut is a spike"))
    assert lines(example, "W345") == []
    write(example, "SLC-001", page("SLC-001", "a"))
    assert len(lines(example, "W345")) == 1


def test_w393_flows_or_after_naming_nothing(example):
    write(example, "SLC-004", page("SLC-004", "d", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]], FLO-099", "**After:** SLC-009"))
    said = [line.split(" W393 ", 1)[1].split(" Fix:")[0] for line in lines(example, "W393")]
    assert said == ["SLC-004's Flows names FLO-099, which is not in this vault.", "SLC-004's After names SLC-009, which is not in this vault."]


def test_w405_a_joins_line_left_on_a_slice_page_is_said_once_and_not_read(example):
    write(example, "SLC-004", page("SLC-004", "d", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001",
                                   "**Joins:** CON-001, CON-099"))
    found = lines(example, "W405")
    assert found == ["slices/SLC-004-x.md:14: W405 SLC-004 still has a Joins line, which is no longer read: a slice's joins come "
                     "from its flows' steps, which name each contract with its sender and receiver. Fix: Delete the Joins line. "
                     "If a join is missing from the slice, the flow step that crosses it is missing; add it to the flow."]
    assert next(s for s in slices.read_slices(cli.load_vault(example)) if s.id == "SLC-004").joins == ()
    assert lines(example, "W393") == [] and lines(example, "E321") == [] and lines(example, "E322") == []


def test_w400_a_journey_due_date_that_passed_with_nothing_recorded(example):
    base = ("**Status:** building", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001")
    write(example, "SLC-004", page("SLC-004", "Amend online", *base, "**Journey due:** 2026-11-20"))
    assert lines(example, "W400", "2026-11-20") == []  # due today is not late
    assert lines(example, "W400", "2026-11-21") == [
        "slices/SLC-004-x.md:15: W400 SLC-004 Amend online: someone was due to try its journey by November 20, 2026, and nothing says how it went. Fix: Record the run as "
        "'- **Journey:** passed YYYY-MM-DD by @who, <link to the run>', or write the new Journey due date and say in History why it moved."]
    write(example, "SLC-004", page("SLC-004", "Amend online", *base, "**Journey due:** 2026-11-20", "**Journey:** it ran"))
    assert "check its Journey line" in lines(example, "W400", "2026-11-21")[0]
    write(example, "SLC-004", page("SLC-004", "Amend online", *base, "**Journey due:** 2026-11-20",
                                   "**Journey:** passed 2026-11-19 by @qa, [run](https://ci.example/9)"))
    assert lines(example, "W400", "2026-11-21") == []
    write(example, "SLC-004", page("SLC-004", "Amend online", *base, "**Journey due:** end of November"))
    assert lines(example, "W400", "2026-11-21") == ["slices/SLC-004-x.md:15: W400 SLC-004's Journey due says 'end of November', which "
                                                    "is not a YYYY-MM-DD date. Fix: Write the date the team expects the journey to run, "
                                                    "as '- **Journey due:** YYYY-MM-DD'."]


def test_e394_slices_after_each_other_in_a_circle(example):
    write(example, "SLC-001", page("SLC-001", "a", "**Flows:** [[FLO-001-hold-pay-confirm|FLO-001]]", "**After:** SLC-004"))
    found = lines(example, "E394")
    assert len(found) == 1 and "SLC-001, SLC-004 each come after another of them" in found[0]
    code, _ = run("check", "--vault", str(example), "--today", TODAY)
    assert code == 1


def test_w396_journey_passes_needs_a_readable_journey_line(example):
    base = ("**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001")
    write(example, "SLC-004", page("SLC-004", "d", "**Status:** journey passes", *base))
    assert "no Journey line says who ran it" in lines(example, "W396")[0]
    write(example, "SLC-004", page("SLC-004", "d", "**Status:** on", *base, "**Journey:** it went fine"))
    assert "its Journey line is not 'passed YYYY-MM-DD by @who" in lines(example, "W396")[0]
    write(example, "SLC-004", page("SLC-004", "d", "**Status:** journey passes", *base, "**Journey:** passed 2026-11-19 by @qa, [run](https://ci.example/9)"))
    assert lines(example, "W396") == []


def test_w397_building_before_what_it_comes_after_has_passed_is_a_warning_not_a_block(example):
    write(example, "SLC-004", page("SLC-004", "d", "**Status:** building", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001"))
    found = lines(example, "W397")
    assert len(found) == 1 and "SLC-001 it comes after is not planned yet" in found[0]
    write(example, "SLC-001", page("SLC-001", "a", "**Status:** journey passes", "**Flows:** [[FLO-001-hold-pay-confirm|FLO-001]]",
                                   "**Journey:** passed 2026-11-19 by @qa, [run](https://ci.example/9)"))
    assert lines(example, "W397") == []


def test_w399_says_once_that_slices_are_still_on_the_releases_page(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    found = lines(vault, "W399", "2026-10-13")
    assert len(found) == 1 and found[0].startswith("04b-releases.md:13: W399 Slices are still named on the releases page (1 of them)")
    write(vault, "SLC-001", page("SLC-001", "Hold and pay", "**Flows:** [[FLO-005-05-hold-never-released|FLO-005]]"))
    found = lines(vault, "W399", "2026-10-13")
    assert len(found) == 1 and "still names flows on the releases page, but slices now have pages" in found[0]


def test_w348_a_release_slices_bullet_and_a_milestone_that_disagree(example):
    (example / "04b-releases.md").write_text(
        "---\nid: releases\ntype: initiative-section\ntitle: Releases\nstate: assumption\nowner: \"@hl-solution-lead\"\n"
        "authored: authored\n---\n\n# Releases\n\nOne milestone.\n\n## Release one: website\n\n- **Target:** 2027-02-01\n"
        "- **State:** assumption\n- **Slices:** SLC-001, SLC-007\n", encoding="utf-8")
    write(example, "SLC-004", page("SLC-004", "d", "**Flows:** [[FLO-002-amend-or-cancel|FLO-002]]", "**After:** SLC-001",
                                   "**Milestone:** Release one"))
    said = [line.split(" W348 ", 1)[1].split(" Fix:")[0] for line in lines(example, "W348")]
    assert said == ["'Release one: website' lists SLC-007 in its Slices, and there is no slice page SLC-007.",
                    "SLC-004's Milestone says 'Release one', but no release on the releases page lists SLC-004 in its Slices."]


# --- the flow-check rules, on a fixture whose check finishes --------------------------------------------------------

def checked_vault(tmp_path, *bullets, extra=""):
    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    write(vault, "SLC-001", page("SLC-001", "Hold and pay", "**Flows:** [[FLO-005-05-hold-never-released|FLO-005]]", *bullets, extra=extra))
    return vault


def test_w391_on_a_planned_slice_and_w395_once_it_is_building(tmp_path):
    vault = checked_vault(tmp_path, "**Status:** planned")
    assert [line.split(": ", 1)[1].split(" Fix:")[0] for line in lines(vault, "W391", "2026-10-13")] == [
        "W391 SLC-001 Hold and pay: its flow check fails: 1 open finding (stops halfway)."]
    vault = checked_vault(tmp_path / "b", "**Status:** building")
    assert lines(vault, "W391", "2026-10-13") == []
    found = lines(vault, "W395", "2026-10-13")
    assert len(found) == 1 and "SLC-001 Hold and pay is building, but its flow check fails: 1 open finding (stops halfway)" in found[0]
    assert "vela check-slice SLC-001" in found[0]


def test_w395_a_building_slice_with_nothing_drawn_is_not_fully_checked(tmp_path):
    vault = checked_vault(tmp_path, "**Status:** building")
    flow = next((vault / "06-runtime" / "flows").glob("*.md"))
    flow.write_text(flow.read_text(encoding="utf-8").split("```mermaid")[0], encoding="utf-8")
    found = lines(vault, "W395", "2026-10-13")
    assert len(found) == 1 and "is not fully checked" in found[0]


def test_an_override_on_the_slice_page_covers_the_finding_and_e398_when_it_ends(tmp_path):
    rule = '- **Override:** "F8 CON-020 declined until {}" by @lead on 2026-10-13: the refund flow lands next sprint\n'
    vault = checked_vault(tmp_path, "**Status:** building", extra="\n## Overrides\n\n" + rule.format("2026-12-01"))
    assert lines(vault, "W395", "2026-10-13") == [] and lines(vault, "E398", "2026-10-13") == []
    code, out = run("check-slice", "SLC-001", "--vault", str(vault), "--today", "2026-10-13")
    assert "covered until 2026-12-01" in out or "covered" in out.splitlines()[0]
    vault = checked_vault(tmp_path / "b", "**Status:** building", extra="\n## Overrides\n\n" + rule.format("2026-10-01"))
    assert len(lines(vault, "W395", "2026-10-13")) == 1
    found = lines(vault, "E398", "2026-10-13")
    assert found == ["slices/SLC-001-x.md:17: E398 The override for F8 on CON-020 (declined) ended on 2026-10-01, so the finding it "
                     "covered blocks its slice again. Fix: Fix the finding and delete the override, or write a new end date and why it moved."]
    assert run("check", "--vault", str(vault), "--today", "2026-10-13")[0] == 1


def test_an_expired_override_on_a_flow_page_is_e398_too(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    flow = next((vault / "06-runtime" / "flows").glob("*.md"))
    flow.write_text(flow.read_text(encoding="utf-8") + '\n## History\n\n- **Override:** "F8 CON-020 declined until 2026-10-01" '
                    "by @lead on 2026-09-13: next sprint\n", encoding="utf-8")
    assert len(lines(vault, "E398", "2026-10-13")) == 1


def test_f13_reads_earlier_as_what_the_slice_comes_after():
    from vela.flowcheck import properties
    from vela.flowcheck.tables import Catalog
    s1 = slices.Slice("SLC-001", "a", ("FLO-001",), "", 1, 0)
    s2 = slices.Slice("SLC-002", "b", ("FLO-002",), "", 1, 1)  # comes after nothing, so it may not start from SLC-001's leavings
    s3 = slices.Slice("SLC-003", "c", ("FLO-003",), "", 1, 2, after=("SLC-001",))
    catalog = Catalog(slices=[s1, s2, s3])
    assert slices.upstream(catalog.slices, s3) == {"SLC-001", "SLC-003"}
    assert slices.upstream(catalog.slices, s2) == {"SLC-002"}
    assert properties.loose_ends(catalog, 1, []) == []


def test_check_slice_finds_a_slice_by_its_id(tmp_path):
    vault = checked_vault(tmp_path, "**Status:** planned")
    code, out = run("check-slice", "SLC-001", "--vault", str(vault), "--today", "2026-10-13")
    assert code == 1 and out.startswith("vela check-slice: Hold and pay (FLO-005): fails.")


def test_w347_on_a_slice_a_release_lists_and_not_in_this_slice_answers_it(tmp_path):
    from test_tracer import add_flows, with_bullets
    from test_releases import vault_with
    vault = vault_with(tmp_path, with_bullets(["**Slices:** SLC-001"]))
    add_flows(vault)
    flows = "**Flows:** [[FLO-901-site-to-booking|FLO-901]]"
    write(vault, "SLC-001", page("SLC-001", "Hold and quote", flows))
    said = "\n".join(lines(vault, "W347"))
    assert "SLC-001 passes through APP-website" in said and "APP-pricing" in said and "CON-003" in said
    assert "APP-booking" not in said and "CON-001" not in said
    write(vault, "SLC-001", page("SLC-001", "Hold and quote", flows, extra=(
        "\n## Not in this slice\n\n- Website (APP-website): no capacity yet\n- Pricing (APP-pricing, CON-003): waits on the fare review\n")))
    assert lines(vault, "W347") == []


# --- the handoff names the slices an app takes part in --------------------------------------------------------------

def test_the_handoff_lists_the_slices_an_app_takes_part_in_and_verify_sees_a_changed_join_not_a_status_move(example):
    flow = example / "06-runtime" / "flows" / "FLO-009-a-kiosk-books.md"
    with_kiosk_flow(example)
    code, out = run("handoff", "APP-kiosks", "--vault", str(example), "--today", TODAY, "--commit", "abc1234", "--replace")
    assert code == 0, out
    assert "Port kiosks is part of 3 slices: SLC-001 " in out and "SLC-003 Kiosks book through Booking in the March image (not planned yet)." in out
    assert 'What "slice" means' not in out  # definitions come from `vela terms`, not every run
    manifest = (example / "handoffs" / "APP-kiosks.md").read_text(encoding="utf-8")
    assert "| SLC-003 | slice | slices/SLC-003-kiosks-book-in-the-march-image.md |" in manifest and "TRACER-1" not in manifest
    verify = ("handoff", "verify", "APP-kiosks", "--vault", str(example))
    assert run(*verify)[0] == 0
    path = example / "slices" / "SLC-003-kiosks-book-in-the-march-image.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("- **After:** SLC-002\n", "- **Status:** planned\n- **After:** SLC-002\n")
                    .replace("## History\n", "## History\n\n- 2026-11-21: planned by @hl-solution-lead.\n"), encoding="utf-8")
    assert run(*verify)[0] == 0  # a status move is the teams' own, not a change to accept
    flow.write_text(flow.read_text(encoding="utf-8").replace("checks capacity, over", "checks the fare, over")
                    .replace("vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check", "pricing-building-blocks#CON-003 Quote a fare|Quote a fare"), encoding="utf-8")
    code, out = run(*verify)
    assert code == 1 and "changed: slice Kiosks book through Booking in the March image (SLC-003)" in out  # the join changed in the flow, and the slice it is part of says so


# --- vela next -------------------------------------------------------------------------------------------------

def test_next_suggests_the_step_for_the_first_slice_that_can_move():
    v = vault_of(("SLC-001", page("SLC-001", "Tracer", "**Status:** journey passes", "**Flows:** FLO-001",
                                  "**Ships switched off:** a per-user flag")),
                 ("SLC-002", page("SLC-002", "Second", "**Status:** building", "**Flows:** FLO-002", "**After:** SLC-003")),
                 ("SLC-003", page("SLC-003", "Third", "**Flows:** FLO-003", "**After:** SLC-001")))
    found = slices.read_slices(v)
    assert [s.id for s in found] == ["SLC-001", "SLC-003", "SLC-002"]
    assert slices.next_step(found) == ("SLC-001 Tracer passed its journey: deploy it switched off (a per-user flag), "
                                       "then set it to live but off.")
    on = vault_of(("SLC-001", page("SLC-001", "Tracer", "**Status:** on", "**Flows:** FLO-001")),
                  ("SLC-002", page("SLC-002", "Second", "**Status:** building", "**Flows:** FLO-002", "**After:** SLC-003")),
                  ("SLC-003", page("SLC-003", "Third", "**Flows:** FLO-003", "**After:** SLC-001")))
    assert slices.next_step(slices.read_slices(on)).startswith("SLC-003 Third is not planned yet: draw its flows")
    assert slices.next_step([]) == ""


def test_vela_next_prints_the_slice_step_on_a_line_of_its_own():
    out = run("next", "--vault", str(EXAMPLE), "--today", TODAY)[1]
    assert "vela next: for the slices: SLC-001 A customer books on the website through Booking is not planned yet" in out
