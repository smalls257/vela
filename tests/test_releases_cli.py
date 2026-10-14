"""`vela releases brief` and `vela releases tracer-candidates` (overhaul Task 21f): the lookup and the count a releases
session starts from, so the skill relays them instead of reading five kinds of page and counting by hand."""
import json
import shutil

from conftest import REPO, run
from test_releases import FR, LINK, release, vault_with
from test_tracer import BOOKING, CON1, PRICING, WEBSITE, add_flows, flow_page

from vela import say

FIXTURE = REPO / "examples" / "unified-booking"
CAP = "capabilities/CAP-014-hold-a-seat.md"


def rich(tmp_path):
    """The example with one requirement, allocated, on one release, its four slice pages, and four drawn flows."""
    vault = vault_with(tmp_path, release("Release one: pilot", [f"{LINK} | all | "]).replace(
        "- **State:** assumption\n", "- **State:** assumption\n- **Slices:** SLC-001\n", 1))
    add_flows(vault)
    flows = vault / "06-runtime" / "flows"
    (flows / "FLO-904-booking-api-to-pricing.md").write_text(
        flow_page(904, f"{BOOKING} → {PRICING}: books the fare, over {CON1}."), encoding="utf-8")
    first = flows / "FLO-901-site-to-booking.md"
    first.write_text(first.read_text(encoding="utf-8").replace(
        "# Tracer flow 901\n\n", "# Tracer flow 901\n\nThe first thin path: a person holds a seat on the website.\n\n"),
        encoding="utf-8")
    return vault


def as_json(*argv):
    code, out = run(*argv, "--json")
    return code, json.loads(out)


def test_tracer_candidates_rank_by_apps_and_new_contracts(tmp_path):
    code, data = as_json("releases", "tracer-candidates", "--vault", str(rich(tmp_path)))
    assert code == 0
    ranked = [(c["flow"], len(c["apps"]), len(c["new_contracts"])) for c in data["candidates"]]
    # 901 crosses three apps; 904 and 903 two each, and 904 wins the tie on its new contract; 902's outside payment
    # page is not an app, so it crosses one. Quote a fare (CON-003) is a changed contract, not a new one.
    assert ranked[:4] == [("FLO-901", 3, 1), ("FLO-904", 2, 1), ("FLO-903", 2, 0), ("FLO-902", 1, 0)], ranked
    # The example's own flows were drawn before steps named a sender and receiver: listed last, said uncounted.
    assert [c["countable"] for c in data["candidates"][4:]] == [False, False, False]
    assert data["candidates"][0]["new_contracts"] == ["CON-001"]
    assert data["candidates"][0]["recorded_first_path"] is True
    assert data["recommended"] == "FLO-901"
    code, out = run("releases", "tracer-candidates", "--vault", str(rich(tmp_path / "again")))
    assert code == 0 and out.index("FLO-901") < out.index("FLO-904") < out.index("FLO-903") < out.index("FLO-902")


def test_tracer_candidates_say_a_tie_is_the_leads_call(tmp_path):
    vault = rich(tmp_path)
    (vault / "06-runtime" / "flows" / "FLO-904-booking-api-to-pricing.md").write_text(flow_page(
        904, f"{WEBSITE} → {BOOKING}: holds a seat, over {CON1}.", f"{BOOKING} → {PRICING}: asks the fare."), encoding="utf-8")
    code, data = as_json("releases", "tracer-candidates", "--vault", str(vault))
    assert code == 0 and data["tied"] == ["FLO-901", "FLO-904"]
    code, out = run("releases", "tracer-candidates", "--vault", str(vault), "--for-lead")
    assert "sees first" in out


def test_a_new_contract_an_outside_party_provides_is_not_counted(tmp_path):
    vault = rich(tmp_path)
    app = vault / "05-building-blocks" / "booking-building-blocks.md"
    before, outside = app.read_text(encoding="utf-8").split("- **Provider:** Tidepay (external)\n", 1)
    outside = outside.replace("- **Change:** new consumers", "- **Change:** new", 1)  # Tidepay's API, new to us
    app.write_text(before + "- **Provider:** Tidepay (external)\n" + outside, encoding="utf-8")
    outcome = "[[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]]"
    (vault / "06-runtime" / "flows" / "FLO-905-paid.md").write_text(
        flow_page(905, f"{BOOKING} → {PRICING}: reports the payment, over {outcome} and {CON1}."), encoding="utf-8")
    code, data = as_json("releases", "tracer-candidates", "--vault", str(vault))
    paid = next(c for c in data["candidates"] if c["flow"] == "FLO-905")
    assert paid["new_contracts"] == ["CON-001"], paid


def test_brief_says_missing_prerequisites(tmp_path):
    bare = tmp_path / "bare"
    shutil.copytree(FIXTURE, bare)
    code, data = as_json("releases", "brief", "--vault", str(bare))
    assert code == 0
    assert [m["offer"] for m in data["missing"]][0] == "/vela:requirements"
    code, out = run("releases", "brief", "--vault", str(bare), "--for-lead")
    assert code == 0 and "/vela:requirements" in out and "no functional requirements" in out

    unallocated = tmp_path / "unallocated"
    shutil.copytree(FIXTURE, unallocated)
    cap = unallocated / CAP
    cap.write_text(cap.read_text(encoding="utf-8").rstrip("\n") + "\n" + FR, encoding="utf-8")
    code, data = as_json("releases", "brief", "--vault", str(unallocated))
    offers = [m["offer"] for m in data["missing"]]
    assert "/vela:allocate" in offers and "/vela:requirements" not in offers
    assert data["requirements"]["unallocated"] == ["CAP-014.FR1"]

    code, data = as_json("releases", "brief", "--vault", str(rich(tmp_path / "rich")))
    assert code == 0 and data["missing"] == []


def test_brief_names_slices_in_order(tmp_path):
    code, data = as_json("releases", "brief", "--vault", str(rich(tmp_path)))
    assert code == 0
    assert [s["id"] for s in data["slices"]] == ["SLC-001", "SLC-002", "SLC-003", "SLC-004"]
    assert data["slices"][0]["tracer"] is True and data["slices"][1]["after"] == ["SLC-001"]
    assert data["releases"][0]["name"] == "Release one: pilot"
    assert data["releases"][0]["slices"] == ["SLC-001"]
    assert data["releases"][0]["delivers"] == [{"requirement": "CAP-014.FR1", "criteria": "all"}]
    assert data["first_path"][0]["flow"] == "FLO-901"
    assert "first thin path" in data["first_path"][0]["words"]
    code, out = run("releases", "brief", "--vault", str(rich(tmp_path / "again")))
    assert out.index("SLC-001") < out.index("SLC-002") < out.index("SLC-003") < out.index("SLC-004")


def test_for_lead_passes_the_leak_check(tmp_path):
    vault = rich(tmp_path)
    for command in ("brief", "tracer-candidates"):
        code, out = run("releases", command, "--vault", str(vault), "--for-lead")
        assert code == 0, out
        assert out.strip()
        for line in out.splitlines():
            assert say.leak_in(line) is None, line
    code, out = run("releases", "brief", "--vault", str(vault), "--for-lead")
    assert "Release one: pilot" in out and "A customer books on the website through Booking" in out
    code, out = run("releases", "tracer-candidates", "--vault", str(vault), "--for-lead")
    assert "Tracer flow 901" in out and "Public website" in out and "Booking API" in out
    assert "Hold, pay, confirm: not counted" in out


def test_an_unreadable_vault_is_exit_2(tmp_path):
    code, out = run("releases", "brief", "--vault", str(tmp_path / "nowhere"))
    assert code == 2, out
