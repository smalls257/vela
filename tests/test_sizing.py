"""sizing.of: the plan's size from apps, capabilities and releases, ratcheted by the stubs, set by the lead."""
import ast
import re
import subprocess
import sys

import pytest

from conftest import REPO
from sizing_vault import choose, sized, write_plan
from vela import cli, privaterecord, schema, sizing
from vela.sizing import Need

LIB = REPO / "plugin" / "lib" / "vela"
SMALL_STUB = {"id": "2026-10-01-grill-a", "status": "closed", "size": "small; apps 2, capabilities 1, releases 1"}


@pytest.mark.parametrize("n, band", [(0, "small"), (2, "small"), (3, "medium"), (5, "medium"), (6, "large")])
def test_apps_band_at_its_edges(tmp_path, n, band):
    write_plan(tmp_path, apps=[(f"app{i}", "new") for i in range(n)])
    assert sized(tmp_path).measured == band


@pytest.mark.parametrize("n, band", [(2, "small"), (3, "medium"), (6, "large")])
def test_capabilities_band_at_its_edges(tmp_path, n, band):
    write_plan(tmp_path, capabilities=["new"] * n)
    assert sized(tmp_path).measured == band


@pytest.mark.parametrize("n, band", [(1, "small"), (2, "medium"), (3, "large")])
def test_releases_band_at_its_edges(tmp_path, n, band):
    write_plan(tmp_path, releases=["2027-01-15"] * n)
    assert sized(tmp_path).measured == band


def test_what_isnt_changing_isnt_counted(tmp_path):
    write_plan(tmp_path, apps=[("a", "new"), ("b", "changed"), ("c", "unchanged"), ("d", "integrated"), ("e", "retired")],
               capabilities=["new", "unchanged", "unchanged"])
    got = sized(tmp_path)
    assert [(s.name, s.count) for s in got.signals] == [("apps", 2), ("capabilities", 1), ("releases", 0)]


def test_the_highest_signal_wins(tmp_path):
    write_plan(tmp_path, apps=[("a", "new")], capabilities=["new"] * 3)
    assert sized(tmp_path).measured == "medium"


def test_the_example_is_large_and_a_one_app_plan_with_two_suppliers_is_small():
    assert sized(REPO / "examples" / "unified-booking").measured == "large"
    # one app, one capability, one release; two suppliers and three provider contracts never move the band
    assert sized(REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1").measured == "small"


def test_the_owners_shape_is_small_with_the_bus_typed_as_a_provider():
    got = sized(REPO / "tests" / "fixtures" / "small-two-apps")
    assert got.band == "small"
    assert got.counts_text() == "apps 2, capabilities 1, releases 1"


def test_the_band_does_not_drop_on_its_own(tmp_path):
    write_plan(tmp_path, apps=[("a", "new")],
               stubs=[{**SMALL_STUB, "size": "medium; apps 3, capabilities 1, releases 1"}])
    got = sized(tmp_path)
    assert (got.measured, got.recorded, got.shape, got.band) == ("small", "medium", "medium", "medium")


def test_the_leads_choice_sets_the_band_either_way(tmp_path):
    write_plan(tmp_path, apps=[(f"a{i}", "new") for i in range(3)], config=choose("small"))
    got = sized(tmp_path)
    assert (got.measured, got.band) == ("medium", "small")
    assert got.chosen == sizing.Choice("small", "[[2026-10-02-grill-a]] c14", "2026-10-02")
    assert not got.needs(Need.OPTIONS_BEFORE_GRILL)


def test_needs_start_at_their_band(tmp_path):
    write_plan(tmp_path, config=choose("medium"))
    got = sized(tmp_path)
    assert got.needs(Need.OPTIONS_BEFORE_GRILL) and got.needs(Need.READING_LOAD_SHOWN)
    assert not got.needs(Need.REVIEW_EACH_MODE) and not got.needs(Need.DOMAIN_FIELD)


def test_every_need_has_a_band_and_a_reason():
    assert set(Need.__members__) == set(schema.NEEDS)
    for name, (band, why) in schema.NEEDS.items():
        assert band in schema.SIZE_BANDS and len(why.split()) >= 8, name
    for name, (limits, why) in schema.SIZE_SIGNALS.items():
        assert limits[0] < limits[1] and len(why.split()) >= 8, name


def test_the_first_announcement_names_the_counts(tmp_path):
    write_plan(tmp_path, apps=[("scheduler", "new"), ("jobs-api", "new")], capabilities=["new"], releases=["2027-01-15"])
    said = sizing.announcement(sized(tmp_path))
    assert (said.kind, said.band) == ("first", "small")
    assert said.plain == ("I'm treating this as a small plan: two apps, one capability and one release. That means "
                          "fewer steps and quieter checks; say if it's bigger than it looks.")


def test_growth_is_said_once(tmp_path):
    apps = [(f"a{i}", "new") for i in range(3)]
    write_plan(tmp_path, apps=apps, stubs=[SMALL_STUB])
    said = sizing.announcement(sized(tmp_path))
    assert said.kind == "grew" and "three apps" in said.plain and "Nothing already decided changes." in said.plain
    write_plan(tmp_path, apps=apps, stubs=[SMALL_STUB, {"id": "2026-10-02-grill-b", "status": "open",
                                                        "size": "medium; apps 3, capabilities 0, releases 0"}])
    assert sizing.announcement(sized(tmp_path)) is None


def test_a_size_down_is_said_once_per_session_while_the_shape_disagrees(tmp_path):
    apps = [(f"a{i}", "new") for i in range(3)]
    write_plan(tmp_path, apps=apps, stubs=[SMALL_STUB], config=choose("small"))
    said = sizing.announcement(sized(tmp_path))
    assert said.kind == "kept"
    assert said.plain == "Kept small, as you chose; the shape reads medium because of three apps."
    write_plan(tmp_path, apps=apps, config=choose("small"),
               stubs=[SMALL_STUB, {"id": "2026-10-02-grill-b", "status": "open", "size_kept": "medium"}])
    assert sizing.announcement(sized(tmp_path)) is None


def test_a_size_down_against_an_earlier_reading_names_the_record_not_a_signal(tmp_path):
    write_plan(tmp_path, apps=[("a", "new"), ("b", "new")], config=choose("small"),
               stubs=[{**SMALL_STUB, "size": "medium; apps 3, capabilities 1, releases 1"}])
    said = sizing.announcement(sized(tmp_path))
    assert said.kind == "kept"
    assert said.plain == ("Kept small, as you chose; an earlier session read it medium, and the size doesn't come "
                          "down on its own.")


def test_the_stub_keeps_the_size_and_no_names():
    text = privaterecord.render_stub({"id": "2026-10-23-grill-jobs", "type": "session", "date": "2026-10-23",
                                      "modes": ["grill"], "status": "open"})
    text = privaterecord.with_size(text, size="small; apps 2, capabilities 1, releases 1", kept="")
    meta = privaterecord.stub_meta(text)
    assert meta["size"] == "small; apps 2, capabilities 1, releases 1" and "size_kept" not in meta


@pytest.mark.parametrize("config, said", [("size: small\n", "mapping"), (choose("tiny"), "band"),
                                          (choose("small", because="c14"), "because"),
                                          (choose("small", date="soon"), "date")])
def test_a_malformed_choice_is_a_tool_failure(tmp_path, config, said):
    write_plan(tmp_path, config=config)
    with pytest.raises(cli.ToolError, match=said):
        cli.load_config(tmp_path)


def test_only_sizing_compares_a_band():
    bands = set(schema.SIZE_BANDS)
    offenders = []
    for path in LIB.rglob("*.py"):
        if path.name in ("sizing.py", "schema.py"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Compare):
                continue
            parts = [node.left] + list(node.comparators)
            consts = {p.value for p in parts if isinstance(p, ast.Constant)}
            consts |= {e.value for p in parts if isinstance(p, (ast.Tuple, ast.List, ast.Set))
                       for e in p.elts if isinstance(e, ast.Constant)}
            attrs = {p.attr for p in parts if isinstance(p, ast.Attribute)}
            if consts & bands or attrs & {"band", "measured", "shape"}:
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert offenders == [], "ask sizing.of(vault).needs(Need.X) instead"


@pytest.mark.parametrize("module", ["closegate", "closereadback", "receipts", "decisions.consent", "commands.close_push"])
def test_privacy_steps_never_load_the_size(module):
    # The import graph, not a grep: a module that reaches sizing through another import would still be size-aware.
    code = ("import sys, importlib; sys.path.insert(0, %r); importlib.import_module('vela.%s'); "
            "sys.exit(1 if 'vela.sizing' in sys.modules else 0)" % (str(LIB.parent), module))
    assert subprocess.run([sys.executable, "-c", code], capture_output=True).returncode == 0, module
