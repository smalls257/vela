"""Read the demo tech design docs, and check the reader neither crashes on a malformed doc nor hides what it skipped.

    python3 -m pytest tests/test_explorer_design.py

The fixtures under demo_designs/ are written as three teams' repositories for the booking demo vault. Booking and
Pricing follow TECH-DESIGN-FORMAT.md and read with no problems. Notifications is deliberately incomplete, and every
problem it carries is listed in NOTIFICATIONS_PROBLEMS. Every vault ID the fixtures cite must exist in the demo
vault, built here by make_demo_vault.py, except the one deliberate bad trace.
"""
import json
import shutil
import sys

import pytest

from conftest import REPO
from vela import cli
from vela.explorer import design_data

sys.path.insert(0, str(REPO / "tests" / "fixtures" / "explorer"))

import make_demo_vault  # noqa: E402

DESIGNS = REPO / "tests" / "fixtures" / "explorer" / "demo_designs"
BOOKING = DESIGNS / "booking/docs/tech-design/booking.md"
PRICING = DESIGNS / "pricing/docs/tech-design/pricing.md"
NOTIFICATIONS = DESIGNS / "notifications/docs/tech-design/notifications.md"
APPS = {"APP-booking": BOOKING, "APP-pricing": PRICING, "APP-notifications": NOTIFICATIONS}
DELIBERATE_BAD_IDS = {"EPC-037.AC9"}  # EPC-037 has seven criteria
NOTIFICATIONS_PROBLEMS = [  # (section, part of the message)
    ("frontmatter", "gaps entry G-001 has no why, revisit"),
    ("frontmatter", "gap G-002 names OQ-002, which is not in the doc"),
    ("vault link", "more than one vault commit: 7d41e0c, 9e02b11"),
    ("Integration points", "the design has no 'Integration points' section (## Integration points)"),
    ("NFRs", "row has 2 cells, the header 3"),
    ("Operations", "no '**Scale:**' bullet"),
    ("Components › Channel suppressor", "no 'Exposes:' bullet"),
    ("Components › Booking event consumer", "depends on 'Message sender'"),
    ("Components › Template renderer", "no Responsibility-matrix row"),
    ("ADRs", "ADR-0002 links to ../adr/0002-notifications-dedupe-store.md, which is not there"),
]


@pytest.fixture(scope="module")
def booking():
    return design_data.read_design(BOOKING)


@pytest.fixture(scope="module")
def demo_vault(tmp_path_factory):
    out = tmp_path_factory.mktemp("demo") / "vault"
    make_demo_vault.main(out)
    return cli.load_vault(out)


def write(tmp_path, text, name="doc.md"):
    folder = tmp_path / "repo" / "docs" / "tech-design"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
    return path


def messages(design):
    return [p["message"] for p in design["problems"]]


# --- each section -----------------------------------------------------------------------------------------------

def test_frontmatter_and_vault_link(booking):
    fm = booking["frontmatter"]
    assert (fm["slug"], fm["status"]) == ("booking", "complete-with-gaps")
    assert [g["id"] for g in fm["gaps"]] == ["G-001", "G-002", "G-003"]
    assert fm["gaps"][0]["acknowledged_by"] == "@hl-booking-senior"
    assert [d["id"] for d in fm["deferred"]] == ["D-001"]
    assert fm["last_session"].startswith("2026-11-24T16:40")
    assert booking["vault"] == {"mode": "vault", "source": "inferred", "app": "APP-booking",
                                "vault_path": "../harborline-vault",
                                "building_blocks": "../harborline-vault/05-building-blocks/booking-building-blocks.md",
                                "commits": ["7d41e0c"]}
    assert booking["title"] == "Booking"


def test_the_good_fixtures_read_with_no_problems():
    for path in (BOOKING, PRICING):
        design = design_data.read_design(path)
        assert design["problems"] == [], path
        json.dumps(design)  # plain data, ready for the page


def test_overview_boundaries_and_diagrams_keep_their_mermaid_source(booking):
    assert booking["overview"]["text"].startswith("Booking is one deployable service")
    assert booking["overview"]["mermaid"][0].startswith("flowchart LR")
    assert booking["boundaries"]["inside"].startswith("the Booking API")
    assert "FERRYMASTER" in booking["boundaries"]["outside"]
    flows = booking["flows"]
    assert [f["title"] for f in flows] == ["Hold, pay, confirm (FLO-001)", "Ledger write fails (EPC-031.AC3)"]
    assert flows[0]["kind"] == "sequenceDiagram"
    assert {"id": "API", "name": "Booking API"} in flows[0]["participants"]
    assert [d["kind"] for d in booking["diagrams"]] == ["stateDiagram-v2"]


def test_components_and_matrix(booking):
    names = [c["name"] for c in booking["components"]]
    assert names == ["Booking API", "Booking lifecycle", "Hold keeper", "Upstream readers", "Ledger adapter",
                     "Event publisher"]
    hold = booking["components"][2]
    assert hold["responsibility"].startswith("Keeps an unpaid seat held")
    assert hold["owns"].startswith("hold expiry")
    assert hold["depends_on_components"] == ["Upstream readers"]
    assert hold["exposes"].startswith("reserve()")
    assert hold["container"] is None  # the format has no component -> container link (DESIGN-INSIDE.md)
    assert [r["component"] for r in booking["matrix"]] == names
    assert booking["matrix"][4]["writes_to"] == "FERRYMASTER, bookings"


def test_data_model_from_the_er_diagram(booking):
    model = booking["data_model"]
    assert model["parsed_from"] == "erDiagram"
    assert [e["name"] for e in model["entities"]] == ["BOOKING", "HOLD", "OUTBOX_ROW", "PAYMENT_OUTCOME"]
    booking_entity = model["entities"][0]
    assert {"type": "string", "name": "reference", "keys": ["PK"]} in booking_entity["fields"]
    assert {"from": "BOOKING", "cardinality": "||--o|", "to": "HOLD", "label": "is held by"} in model["relationships"]
    assert model["stores"][0].startswith("Postgres 16")
    assert "erDiagram" in model["raw"]


def test_data_model_without_a_diagram_reads_bullets():
    model = design_data.read_design(PRICING)["data_model"]
    assert model["parsed_from"] == "headings and bullets"
    assert [e["name"] for e in model["entities"]] == ["Quote token", "Fare rule"]
    assert model["stores"] == ["the existing Fare rules store (Oracle 19c), read only from the Quote service."]


def test_api_and_integration_points(booking):
    assert [(a["component"], a["component_found"]) for a in booking["api"]] == [
        ("Booking API", True), ("Booking lifecycle", True)]
    assert booking["api"][0]["operations"][0].startswith("`POST /v1/bookings/holds`")
    rows = booking["integrations"]
    assert len(rows) == 7
    assert rows[5] == {"system": "FERRYMASTER", "direction": "out", "protocol": "IBM MQ, CON-006",
                       "auth": "MQ channel certificate", "line": rows[5]["line"]}


def test_tables_tech_stack_nfrs_constraints_risks(booking):
    assert booking["tech_stack"][0]["choice"] == "Kotlin on the JVM 21"
    assert booking["nfrs"][1]["concern"] == "Ledger write latency"
    assert booking["constraints"][0]["source"] == "vault CST-1"
    assert booking["risks"][0]["severity"] == "high"


def test_adrs_are_read_from_the_team_repo(booking):
    adrs = booking["adrs"]
    assert [(a["id"], a["found"], a["status"]) for a in adrs] == [("ADR-0001", True, "accepted"),
                                                                  ("ADR-0002", True, "accepted")]
    outbox = adrs[0]
    assert outbox["adr_title"] == "A transactional outbox for ledger writes and events"
    assert outbox["decision"].startswith("Booking lifecycle writes the new state")
    assert [a["option"] for a in outbox["alternatives"]][0] == "Call FERRYMASTER inside the request"
    assert outbox["consequences"]["reversibility cost"].startswith("high")


def test_operations_keep_extra_bullets(booking):
    ops = booking["operations"]
    assert ops["deploy"].startswith("container image")
    assert ops["scale"].startswith("horizontal")
    assert "On-call" in ops["other"]


def test_open_questions_carry_their_challenge(booking):
    [oq] = booking["open_questions"]
    assert (oq["id"], oq["challenges"], oq["challenges_form"]) == ("OQ-001", ["CAP-014.FR1"], "plain")
    assert oq["affects_ids"] == ["EPC-031.AC1", "EPC-037.AC2"]
    assert oq["what_would_unblock"].startswith("the solution lead")
    assert oq["other"]["Scenario"].startswith("a customer on Tidepay's page")
    notifications = design_data.read_design(NOTIFICATIONS)["open_questions"]
    assert [(o["challenges"], o["challenges_form"]) for o in notifications] == [(["CON-002"], "bold")]


def test_context_glossary(booking):
    assert [t["term"] for t in booking["context"]["glossary"]] == ["Hold", "Confirming"]
    assert booking["context"]["boundaries"]["this_project_owns"].startswith("booking state")
    assert design_data.read_design(PRICING)["context"] is None  # created lazily; absence is not a problem


# --- the trace map ----------------------------------------------------------------------------------------------

def test_trace_map_names_where_each_id_was_found(booking):
    assert booking["trace_source"] == "inferred"
    hold = {e["id"]: e["via"] for e in booking["trace"]["Hold keeper"]}
    assert hold["CAP-014.FR1@APP-booking"] == ["owns"]
    api = {e["id"]: e["via"] for e in booking["trace"]["Booking API"]}
    assert api["CON-001"] == ["owns", "exposes", "api contracts"]
    # cited under Operations, owned by no component: in mentions, never in the trace
    assert "Operations" in booking["mentions"]["EPC-039.AC1"]
    assert all(e["id"] != "EPC-039.AC1" for entries in booking["trace"].values() for e in entries)


def test_a_recorded_trace_table_is_read_first(tmp_path):
    doc = PRICING.read_text(encoding="utf-8") + (
        "\n## Trace\n| Target | Component |\n|---|---|\n| CON-003 | Quote API |\n"
        "| EPC-038.AC2 | Fare engine, Nobody |\n")
    design = design_data.read_design(write(tmp_path, doc))
    assert design["trace_source"] == "recorded"
    assert {"id": "EPC-038.AC2", "via": ["trace table", "owns"]} in design["trace"]["Fare engine"]
    assert "'Nobody' is not a ### component" in messages(design)


def test_a_doc_in_the_proposed_format_is_read_as_recorded(tmp_path, demo_vault):
    """integrations/tech-design-grill/inside-view.patch: a vault block, Container bullets, a Trace table, gaps' oq."""
    doc = PRICING.read_text(encoding="utf-8")
    doc = doc.replace("status: complete\n", "status: complete-with-gaps\ngaps:\n  - id: G-001\n    what: rotation\n"
                      "    acknowledged_by: x\n    why: y\n    revisit: z\n    oq: OQ-001\n")
    doc = doc.replace("---\n\n# Tech", "vault:\n  app: APP-pricing\n  initiative: INI-002\n  commit: 7d41e0c\n"
                      "  origin: git@example.invalid:harborline/vault.git\n---\n\n# Tech")
    doc = doc.replace("- Exposes: CON-003 at /v2/quotes", "- Exposes: CON-003 at /v2/quotes\n- Container: Quote service")
    doc += ("\n## Trace\n| Target | Component |\n|--------|-----------|\n| CON-003 | Quote API |\n"
            "| EPC-038.AC4 | Operations |\n\n## Open questions\n\n### OQ-001: Key rotation?\n"
            "**What we know:** a\n**Challenges:** CON-003\n")
    path = write(tmp_path, doc)
    shutil.copytree(PRICING.parents[1] / "adr", path.parents[1] / "adr")
    design = design_data.read_design(path)
    assert design["problems"] == []
    assert (design["vault"]["source"], design["vault"]["commits"]) == ("recorded", ["7d41e0c"])
    assert design["trace_source"] == "recorded"
    assert design["components"][0]["container"] == "Quote service"
    assert design["trace"]["Operations"] == [{"id": "EPC-038.AC4", "via": ["trace table"]}]
    assert design_data.resolve(design, design_data.vault_ids(demo_vault))["unresolved"] == []


def test_untraced_targets_are_split_into_acknowledged_and_missed(booking, demo_vault):
    targets = design_data.trace_targets(demo_vault, "APP-booking")
    found = design_data.resolve(booking, design_data.vault_ids(demo_vault), targets)
    assert found["unresolved"] == []
    assert found["untraced"], "the booking fixture leaves other teams' criteria to them"
    assert set(found["untraced"]) == set(found["acknowledged"])
    assert found["acknowledged"]["EPC-039.AC3"] == "G-003"
    assert found["acknowledged"]["EPC-033.AC4"] == "G-002"
    assert "EPC-036.AC1" not in found["untraced"]  # traced, and G-003's EPC-036.AC5 does not acknowledge its siblings


# --- every fixture against the demo vault -----------------------------------------------------------------------

def test_every_fixture_id_exists_in_the_demo_vault(demo_vault):
    known = design_data.vault_ids(demo_vault)
    for app, path in APPS.items():
        design = design_data.read_design(path)
        assert design["vault"]["app"] == app
        assert app in known
        cited = set(design["mentions"])
        cited |= {e["id"] for entries in design["trace"].values() for e in entries}
        cited |= {i for oq in design["open_questions"] for i in oq["challenges"] + oq["affects_ids"]}
        assert cited - known == (DELIBERATE_BAD_IDS if app == "APP-notifications" else set()), app
        unresolved = design_data.resolve(design, known)["unresolved"]
        assert [u["id"] for u in unresolved] == sorted(DELIBERATE_BAD_IDS if app == "APP-notifications" else [])


def test_the_deliberately_incomplete_doc_lists_each_problem():
    design = design_data.read_design(NOTIFICATIONS)
    assert design["frontmatter"]["status"] == "complete-with-gaps"
    found = [(p["section"], p["message"]) for p in design["problems"]]
    for section, part in NOTIFICATIONS_PROBLEMS:
        assert any(s == section and part in m for s, m in found), (section, part, found)
    assert len(found) == len(NOTIFICATIONS_PROBLEMS), found
    assert design["integrations"] == []
    assert design["nfrs"][1]["how_enforced"] == ""  # the short row is kept, padded, and reported


# --- malformed input never crashes, and says what it skipped ----------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("", "doesn't start with its --- header"),
    ("# Tech Design — X\n", "doesn't start with its --- header"),
    ("---\nslug: x\n", "frontmatter is never closed"),
    ("---\nslug: [x\n---\n", "frontmatter is not valid YAML"),
    ("---\n- a\n- b\n---\n", "frontmatter is not a mapping"),
    ("---\nslug: x\nstatus: done\nlast_session: 2026-01-01\n---\n# Tech Design — X\n", "status 'done' is not one of"),
    ("---\nslug: x\nstatus: complete-with-gaps\nlast_session: 2026-01-01\n---\n", "gaps[] is empty"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\ngaps: oops\n---\n", "gaps is not a list"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n# Design\n", "is not '# Tech Design — <Title>'"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Components\n## Components\n",
     "## Components appears twice"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Components\nprose only\n",
     "no ### component under ## Components"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Context boundaries\nWe build it.\n",
     "no '**Inside the app:**' line"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Tech stack\nwe use Go\n",
     "no table, where the format has one"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Tech stack\n| A | B |\n|---|---|\n| x | y |\n",
     "table header is A | B; the format has Layer | Choice | Rationale"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Open questions\n### Why?\n",
     "### Why? is not 'OQ-XXX: <question>'"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Open questions\n### OQ-001: A\n"
     "challenges: the vault\n",
     "challenges: names no vault ID"),
    ("---\nslug: x\nstatus: complete\nlast_session: 2026-01-01\n---\n## Open questions\n### OQ-001: A\n",
     "status is complete with open questions: OQ-001"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\nprereqs:\n"
     "  - path: v/05-building-blocks/booking-building-blocks.md\n    expected_status: complete\n---\n",
     "the vault prereq expects status 'complete', not handed_off"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\nprereqs:\n"
     "  - path: v/05-building-blocks/booking-building-blocks.md\n    expected_status: handed_off\n---\n",
     "doesn't say which version of the plan it used"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\nprereqs:\n"
     "  - path: v/05-building-blocks/booking-building-blocks.md\n    expected_status: handed_off\n---\n",
     "no component cites a trace target"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\n---\n## Responsibility matrix\n"
     "| Component | Owns | Reads from | Writes to |\n|---|---|---|---|\n| Ghost | a | b | c |\n",
     "row for 'Ghost', which is not a ### component"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\n---\n## API contracts\n### Ghost public surface\n",
     "### Ghost public surface names no component"),
    ("---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\n---\n## ADRs\n- [Outbox](../adr/0009-x.md) — t\n",
     "link text 'Outbox' is not ADR-NNNN"),
])
def test_malformed_docs_are_read_with_a_problem(tmp_path, text, expected):
    design = design_data.read_design(write(tmp_path, text))
    assert any(expected in m for m in messages(design)), messages(design)
    json.dumps(design)


def test_a_doc_that_is_not_utf8_is_read_and_reported(tmp_path):
    design = design_data.read_design(write(tmp_path, BOOKING.read_bytes().replace(b"Hold keeper", b"Hold k\xe9eper")))
    assert any("is not UTF-8" in m for m in messages(design))
    assert design["components"]


def test_random_markdown_reports_every_template_section_missing(tmp_path):
    design = design_data.read_design(write(tmp_path, "just some notes\n\n```\n## Components\n```\n"))
    missing = [m for m in messages(design) if m.startswith("the design has no '")]
    assert len(missing) == len(design_data.TEMPLATE_SECTIONS)  # the ## inside a fence is not a section


def test_an_adr_file_the_doc_does_not_list_and_a_malformed_adr(tmp_path):
    path = write(tmp_path, "---\nslug: x\nstatus: in-progress\nlast_session: 2026-01-01\n---\n"
                           "## ADRs\n- [ADR-0001](../adr/0001-x-a.md) — A\n")
    adr = path.parent.parent / "adr"
    adr.mkdir()
    (adr / "0001-x-a.md").write_text("# A decision\n\nno fields\n", encoding="utf-8")
    (adr / "0002-x-b.md").write_text("# ADR-0002: B\n", encoding="utf-8")
    found = messages(design_data.read_design(path))
    assert "0002-x-b.md is in adr/ but not listed under ## ADRs" in found
    assert "first heading is not '# ADR-NNNN: <Title>'" in found
    assert "no **Status:** line" in found
    assert "no ## Decision section" in found


# --- designs_for, as build.py --design will call it ---------------------------------------------------------------

def test_designs_for_reads_each_app():
    found = design_data.designs_for([f"{app}={path}" for app, path in APPS.items()])
    assert list(found) == list(APPS)
    assert design_data.designs_for(None) == {}


def test_designs_for_reports_an_app_mismatch_on_the_design():
    found = design_data.designs_for([f"APP-website={PRICING}"])
    assert "--design gives this doc as APP-website, but its vault prereq is APP-pricing's page" in messages(
        found["APP-website"])


@pytest.mark.parametrize("args, expected", [
    ([f"booking={BOOKING}"], "takes APP-x=path"),
    ([f"APP-booking={BOOKING}", f"APP-booking={BOOKING}"], "names APP-booking twice"),
    (["APP-booking=/nowhere/booking.md"], "no tech design doc at"),
])
def test_designs_for_refuses_what_the_caller_got_wrong(args, expected):
    with pytest.raises(design_data.DesignError, match=expected):
        design_data.designs_for(args)


def test_a_named_adr_dir_or_context_that_is_missing_raises(tmp_path):
    with pytest.raises(design_data.DesignError, match="no ADR directory"):
        design_data.read_design(BOOKING, adr_dir=tmp_path / "none")
    with pytest.raises(design_data.DesignError, match="no CONTEXT.md"):
        design_data.read_design(BOOKING, context=tmp_path / "CONTEXT.md")
