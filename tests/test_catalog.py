"""The question catalogue: the seeded entries, the loader, and the trigger language.

A catalogue that cannot be read must stop the tool (exit 2), never load as empty, because an
empty catalogue makes every vault look as if it owed nothing. A trigger is read, never run."""
import copy
import pathlib
import re

import pytest
import yaml

from conftest import REPO, check, run
from planner import catalog, cli

SEED = REPO / "plugin" / "catalog" / "questions.yaml"


def seed():
    return yaml.safe_load(SEED.read_text(encoding="utf-8"))


def problems(data):
    with pytest.raises(catalog.CatalogueError) as exc:
        catalog.parse_catalogue(data)
    return str(exc.value)


def test_the_seed_loads_with_five_areas_and_about_twenty_entries():
    cat = catalog.parse_catalogue(seed())
    assert cat.version == 1
    assert cat.area_codes == ("FIN", "DAT", "PTN", "REG", "OPS")
    assert 18 <= len(cat.entries) <= 30
    assert {e.area for e in cat.entries} == set(cat.area_codes)
    assert [e.id for e in cat.entries] == sorted(e.id for e in cat.entries)


def test_every_entry_cites_why_it_is_there():
    for entry in catalog.parse_catalogue(seed()).entries:
        assert len(entry.why) >= 40, f"{entry.id} needs a why: a regulation, a practice or a simulation miss"


def test_the_eight_existence_questions_are_initiative_scope_and_always_owed():
    cat = catalog.parse_catalogue(seed())
    words = {"FIN-01": "hold value", "DAT-01": "new party", "PTN-01": "ownership, operation or payment",
             "REG-01": "sold or promised across parties", "REG-02": "regulated or licensed",
             "OPS-04": "more than one system, scheme, map or team doing the same job? Name them", "OPS-05": "retired", "OPS-06": "not yet in the room"}
    for short, phrase in words.items():
        entry = cat.entry(f"Q-{short}")
        assert entry.scope == "initiative" and entry.trigger.text == "exists", short
        assert phrase in entry.question, short


def test_the_high_severity_entries_are_lawful_basis_partner_clauses_and_stored_value():
    cat = catalog.parse_catalogue(seed())
    assert sorted(e.id for e in cat.entries if e.severity == "high") == [
        "Q-DAT-01", "Q-DAT-02", "Q-DAT-05", "Q-FIN-01", "Q-FIN-03", "Q-PTN-01", "Q-PTN-02", "Q-PTN-05"]


def test_every_scope_has_an_entry_and_the_new_kinds_are_created_by_a_yes():
    cat = catalog.parse_catalogue(seed())
    assert {e.scope for e in cat.entries} == set(catalog.SCOPES)
    assert {e.creates for e in cat.entries if e.creates} == {"party", "stored-value"}
    assert "points" in cat.entry("Q-FIN-01").mentions and "licence" in cat.entry("Q-REG-02").mentions


def test_no_entry_names_a_persona_or_an_archetype():
    text = SEED.read_text(encoding="utf-8").lower()
    for pattern in (r"\bpersonas?\b", r"\barchetypes?\b", r"\byou are an? \b", r"\bas (?:the|a) (?:cfo|dpo|regulator)\b"):
        assert not re.search(pattern, text), pattern


def test_the_questions_and_whys_assume_no_merger_and_no_rail_except_as_a_cited_example():
    for entry in catalog.parse_catalogue(seed()).entries:
        for word in (r"merger", r"mergers", r"post-merger", r"ferry", r"ferries", r"rail", r"ticket", r"tickets",
                     r"passengers?", r"carriers?"):
            assert not re.search(rf"\b{word}\b", entry.question, re.I), (entry.id, word)
        assert not re.search(r"\b(merger|mergers|post-merger|ferry|ferries|tickets?|passengers?)\b", entry.why, re.I), entry.id
        if re.search(r"\brail\b", entry.why, re.I):
            assert "e.g. EU 2021/782 for rail" in entry.why, entry.id


def test_each_split_question_asks_one_thing_and_its_follow_up_is_its_own_entry():
    cat = catalog.parse_catalogue(seed())
    assert not re.search(r"purpose", cat.entry("Q-DAT-01").question) and "purpose" in cat.entry("Q-DAT-05").question
    assert not re.search(r"expiry|closure|conversion", cat.entry("Q-FIN-03").question)
    assert "expiry" in cat.entry("Q-FIN-05").question
    assert not re.search(r"who sets", cat.entry("Q-FIN-04").question) and "rate" in cat.entry("Q-FIN-06").question
    assert not re.search(r"assign|notice", cat.entry("Q-PTN-02").question)
    assert "assigned" in cat.entry("Q-PTN-05").question and "notice" in cat.entry("Q-PTN-06").question
    assert not re.search(r"liable", cat.entry("Q-REG-01").question) and "liable" in cat.entry("Q-REG-05").question
    for entry in cat.entries:
        assert entry.question.count("?") <= 1 or entry.id == "Q-OPS-04", entry.id


def test_every_contract_entry_filters_on_change_so_a_settled_contract_owes_nothing():
    for entry in catalog.parse_catalogue(seed()).entries:
        if entry.scope == "contract":
            assert any(c.field == "change" for c in entry.trigger.conditions), entry.id


# ------------------------------------------------------------------ the trigger language

@pytest.mark.parametrize("text, scope, facts, expected", [
    ("exists", "initiative", {}, True),
    ("change in [new, changed]", "app", {"change": "new"}, True),
    ("change in [new, changed]", "app", {"change": "unchanged"}, False),
    ("change in [new, changed]", "app", {}, False),
    ("change: retired", "app", {"change": "retired"}, True),
    ("change in [new, changed, new consumers]", "contract", {"change": "new consumers"}, True),
    ("provider: external", "contract", {"provider": "app"}, False),
    ("relationship: customer group", "party", {"relationship": "customer group"}, True),
    ("change: new and state: inkling", "app", {"change": "new", "state": "decided"}, False),
    ("change: new and state: inkling", "app", {"change": "new", "state": "inkling"}, True),
    ("change   in [New,  changed]", "app", {"change": "new"}, True),
])
def test_triggers_match_facts(text, scope, facts, expected):
    assert catalog.parse_trigger(text, scope).matches(facts) is expected


def test_a_fact_that_is_not_text_never_matches():
    trigger = catalog.parse_trigger("change: new", "app")
    assert trigger.matches({"change": ["new"]}) is False
    assert trigger.matches({"change": None}) is False


@pytest.mark.parametrize("text, scope, said", [
    ("change == 'new'", "app", "is not 'field: value' or 'field in [a, b]'"),
    ("__import__('os').system('x')", "app", "is not 'field: value'"),
    ("colour: red", "app", "trigger field 'colour' is not one a app subject has"),
    ("change: brand-new", "app", "trigger value 'brand-new' is not one change can take"),
    ("change in [new, ]", "app", "has an empty value"),
    ("change: new", "initiative", "fields: none: use exists"),
    ("", "app", "trigger must be text"),
    ("change: new", "bogus", "trigger scope 'bogus' is not one of"),
    ("exists", "bogus", "trigger scope 'bogus' is not one of"),
    ("change: new and change: changed", "app", "trigger field 'change' appears twice"),
    ("change in [new, New]", "app", "lists 'new' twice"),
    ("domain: finance and", "capability", "has a stray 'and'"),
    ("domain: and finance", "capability", "trigger part 'domain:' is not 'field: value'"),
    (["exists"], "app", "trigger must be text"),
])
def test_a_trigger_outside_the_grammar_is_refused_with_its_reason(text, scope, said):
    with pytest.raises(catalog.CatalogueError) as exc:
        catalog.parse_trigger(text, scope)
    assert said in str(exc.value)


def test_the_trigger_code_never_evaluates_text():
    source = (REPO / "plugin" / "lib" / "planner" / "catalog.py").read_text(encoding="utf-8")
    assert not re.search(r"(?<![.\w])(eval|exec|compile|getattr|__import__)\s*\(", source)


# ------------------------------------------------------------------ the loader

def test_every_problem_is_named_at_once():
    data = seed()
    data["version"] = 0
    data["entries"][0]["severity"] = "urgent"
    data["entries"][1]["area"] = "XYZ"
    data["entries"][2]["id"] = "Q-1"
    data["entries"][3]["trigger"] = "colour: red"
    data["entries"][4]["blocks"] = ["vibes"]
    data["entries"][5]["extra"] = 1
    said = problems(data)
    for part in ("'version' must be a whole number", "severity 'urgent'", "area 'XYZ'", "id must look like Q-FIN-01",
                 "trigger field 'colour'", "'blocks' has 'vibes'", "unknown field extra"):
        assert part in said, part


def test_a_duplicate_id_and_a_mismatched_area_are_refused():
    data = seed()
    data["entries"][1]["id"] = data["entries"][0]["id"]
    assert "Q-FIN-01 is used by two entries" in problems(data)
    data = seed()
    data["entries"][0]["area"] = "DAT"
    assert "does not carry its area DAT" in problems(data)


def test_creates_and_mentions_belong_to_initiative_entries_only():
    data = seed()
    entry = next(e for e in data["entries"] if e["scope"] == "app")
    entry["creates"] = "party"
    assert "only an initiative-scope entry may create a subject" in problems(data)
    data = seed()
    entry = next(e for e in data["entries"] if e["id"] == "Q-FIN-02")
    entry["mentions"] = ["money"]
    assert "mentions need a creates" in problems(data)


def test_a_creates_that_is_null_says_it_is_empty():
    data = seed()
    data["entries"][0]["creates"] = None
    assert "'creates' is empty" in problems(data)
    data = seed()
    data["entries"][1]["mentions"] = None
    assert "'mentions' is empty" in problems(data)


def test_a_mention_group_needs_a_reason_and_a_reason_needs_a_mention():
    data = seed()
    entry = next(e for e in data["entries"] if e["id"] == "Q-FIN-01")
    del entry["mention_why"]["voucher"]
    assert "no reason for 'voucher'" in problems(data)
    data = seed()
    entry = next(e for e in data["entries"] if e["id"] == "Q-FIN-01")
    entry["mention_why"]["pointer"] = "not a mention"
    assert "names 'pointer', which 'mentions' does not list" in problems(data)
    data = seed()
    entry = next(e for e in data["entries"] if e["id"] == "Q-FIN-01")
    entry["mentions"] = ["Point/Points!"]
    assert "'mentions' has 'Point/Points!'" in problems(data)


def test_mention_forms_expand_from_groups_and_exceptions_are_phrases():
    cat = catalog.parse_catalogue(seed())
    assert {"licensed", "licensing", "credited", "deposited", "point"} <= set(
        cat.entry("Q-REG-02").mentions + cat.entry("Q-FIN-01").mentions)
    data = seed()
    next(e for e in data["entries"] if e["id"] == "Q-FIN-01")["mention_except"] = ["Credit Card!"]
    assert "'mention_except' must be a list of lower-case phrases" in problems(data)
    data = seed()
    next(e for e in data["entries"] if e["id"] == "Q-FIN-02")["mention_except"] = ["credit card"]
    assert "mention_except needs mentions" in problems(data)


def test_an_area_no_entry_uses_is_refused():
    data = seed()
    data["areas"]["ZZZ"] = "Nobody asks these"
    assert "area ZZZ is listed in 'areas' but no entry uses it" in problems(data)


def test_a_key_written_twice_is_an_error_at_every_depth(tmp_path):
    for text in ("version: 1\nversion: 2\n", "areas:\n  FIN: a\n  FIN: b\n",
                 "entries:\n  - id: Q-FIN-01\n    severity: high\n    severity: normal\n"):
        with pytest.raises(yaml.YAMLError) as exc:
            catalog.load_yaml(text)
        assert "duplicate key" in str(exc.value)
    assert catalog.load_yaml("a: 1\nb: [1, 2]\n") == {"a": 1, "b": [1, 2]}


@pytest.mark.parametrize("data", [None, [], {"version": 1}, {"version": 1, "areas": {"FIN": "x"}, "entries": []}])
def test_a_catalogue_with_no_entries_is_refused(data):
    with pytest.raises(catalog.CatalogueError):
        catalog.parse_catalogue(data)


def test_the_cli_stops_with_exit_2_on_a_broken_catalogue(mini, tmp_path, monkeypatch):
    broken = tmp_path / "questions.yaml"
    data = seed()
    data["entries"][0]["severity"] = "urgent"
    broken.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(cli, "CATALOGUE", broken)
    code, out = check(mini)
    assert code == 2
    assert "is not a valid question catalogue" in out and "severity 'urgent'" in out
    monkeypatch.setattr(cli, "CATALOGUE", tmp_path / "missing.yaml")
    code, out = check(mini)
    assert code == 2 and "missing.yaml is missing" in out
    broken.write_text("version: [1\n", encoding="utf-8")
    monkeypatch.setattr(cli, "CATALOGUE", broken)
    assert check(mini)[0] == 2


def test_the_cli_stops_with_exit_2_on_a_duplicate_key(mini, tmp_path, monkeypatch):
    broken = tmp_path / "questions.yaml"
    broken.write_text(SEED.read_text(encoding="utf-8").replace("version: 1\n", "version: 1\nversion: 1\n", 1),
                      encoding="utf-8")
    monkeypatch.setattr(cli, "CATALOGUE", broken)
    code, out = check(mini)
    assert code == 2 and "duplicate key" in out


def test_the_vault_carries_the_catalogue(mini):
    vault = cli.load_vault(mini)
    assert vault.catalogue.version == 1 and vault.catalogue.entry("Q-FIN-01") is not None


def test_the_installed_plugin_finds_its_catalogue(tmp_path):
    import shutil
    import subprocess
    import sys
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "template", vault)
    shutil.copytree(REPO / "plugin", vault / ".claude" / "skills" / "planner")
    assert (vault / ".claude" / "skills" / "planner" / "catalog" / "questions.yaml").is_file()
    result = subprocess.run([sys.executable, ".claude/skills/planner/scripts/planner", "check"], cwd=vault,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
