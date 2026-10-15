"""The seal on the persona answer keys (tests/sim/seal.py) and the failure report built behind it (failures.py).

The Paper Tiger these guard against is teaching to the test: a skill that scores better on a persona because it
learned that persona's names, keywords or brief, while real leads see no change. So the plugin may not gain a key
term, the failure report may not carry one, and a holdout's per-item results stay sealed unless --reveal is given.
Nothing here calls a model. A failure names files and counts, never a holdout's term.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import REPO

SIM = REPO / "tests" / "sim"
MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]


def load(name):
    spec = importlib.util.spec_from_file_location(f"sim_{name}", SIM / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"sim_{name}"] = module
    spec.loader.exec_module(module)
    return module


seal = load("seal")


@pytest.fixture(scope="module")
def terms():
    return seal.persona_terms()


def keys(terms, kind):
    return {t.key for t in terms if t.kind == kind}


# ------------------------------------------------------------------ the split

def test_a_persona_is_sealed_unless_its_file_says_dev(tmp_path):
    assert seal.sealed("heron-desk") == (False, "heron-desk is a dev persona")
    for name in ("coastal-merger", "holdout-hospitals", "trading-coach"):
        assert seal.sealed(name)[0] is True, name
    (tmp_path / "unlabeled.yaml").write_text("name: Nobody\n", encoding="utf-8")
    assert seal.sealed("unlabeled", tmp_path)[0] is True, "no split is sealed, never open"
    assert seal.sealed("nobody-at-all", tmp_path)[0] is True and seal.sealed(None)[0] is True
    assert seal.split_of({"holdout": True}) == "holdout", "the old flag still reads as holdout"


# ------------------------------------------------------------------ the terms

def test_the_terms_hold_names_keywords_and_brief_runs_and_leave_ordinary_words_out(terms):
    names, words = keys(terms, "name"), keys(terms, "keyword")
    assert {"Priya Menon", "Menon", "Heron", "Marlowe", "TickerTalk"} <= names
    assert {"works council", "identity team"} <= words
    assert keys(terms, "brief"), "runs of brief text are terms too"
    assert not {"Consent", "Microsoft", "Teams", "CIO", "Regulation"} & names, "real products and ordinary words"
    assert not {"handoff", "release one", "capability map", "consent"} & words, "Vela's own vocabulary is not a key"


def test_terms_an_example_vault_holds_are_the_examples_not_a_key(terms):
    """examples/unified-booking is in the repo on purpose and coastal-merger borrows from it; the plugin quotes it."""
    allowed = seal.allowlisted_by_examples()
    assert {"Harborline", "FERRYMASTER"} <= set(allowed)
    assert not {"Harborline", "FERRYMASTER"} & keys(terms, "name")


# ------------------------------------------------------------------ redaction

def test_redaction_removes_every_kind_of_term_and_counts_it(terms):
    text = ("Priya Menon asked whether the WORKS COUNCIL reads it; Menon's team at Marlowe owns Heron. "
            "Consent and the capability map stay, as ordinary words do.")
    out, count = seal.redact(text, terms)
    assert seal.leaks_in(out, terms) == set(), out
    assert count >= 4 and out.count(seal.REDACTED) == count
    assert "Consent and the capability map stay" in out


# ------------------------------------------------------------------ the leak scan of plugin/**

@pytest.fixture(scope="module")
def plugin_leaks():
    return seal.plugin_leaks()


def test_the_plugin_gains_no_persona_term(plugin_leaks):
    """Today's plugin already holds key terms (seal-known-leaks.txt lists each one, to remove). Any other is new."""
    new = plugin_leaks - seal.read_known()
    where = sorted({f"plugin/{f} ({k})" for f, k, _ in new})
    assert not new, (f"{len(new)} persona terms are new in the plugin, in {', '.join(where)}. Run "
                     "`python3 tests/sim/seal.py --leaks` to see them, and write the skill in its own words")


def test_the_known_leaks_list_only_shrinks(plugin_leaks):
    gone = seal.read_known() - plugin_leaks
    assert not gone, (f"{len(gone)} listed leaks are gone from the plugin: run `python3 tests/sim/seal.py --prune` "
                      "so the list cannot hide them coming back")


def test_the_scan_finds_a_planted_term_and_skips_vendored_files(tmp_path):
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "x").mkdir(parents=True)
    (plugin / "skills" / "x" / "SKILL.md").write_text("Ask whether the works council has to agree.\n", encoding="utf-8")
    (plugin / "lib" / "yaml").mkdir(parents=True)
    (plugin / "lib" / "yaml" / "vendored.py").write_text("# Priya Menon\n", encoding="utf-8")
    (plugin / "lib" / "a.min.js").write_text("Heron", encoding="utf-8")
    found = seal.plugin_leaks(plugin)
    assert found == {("skills/x/SKILL.md", "keyword", "works council")}


# ------------------------------------------------------------------ the failure report

def stub_run(tmp_path, persona, reply):
    """A stub run of the smoke script whose assistant says `reply` first in every session."""
    reply_file = tmp_path / "reply.txt"
    reply_file.write_text(reply, encoding="utf-8")
    env = {**os.environ, "SIM_STUB_REPLY": str(reply_file)}
    done = subprocess.run([sys.executable, str(SIM / "run.py"), persona, "--stub", *MODELS, "--budget", "5",
                           "--arms", "vela", "--script", "smoke", "--out", str(tmp_path / "out")],
                          capture_output=True, text=True, env=env, timeout=600)
    assert done.returncode == 0, done.stderr[-2000:]
    return next((tmp_path / "out").iterdir())


LEAKY_REPLY = ("Priya Menon, the works council at Marlowe will want to read Heron's design. Who owns the DPIA? "
               "When is it due? Is UNK-004 open? Does K27 matter? Shall I write it down?")


def failures(run_dir, *extra):
    done = subprocess.run([sys.executable, str(SIM / "failures.py"), str(run_dir), *extra],
                          capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_the_failure_report_names_behaviors_and_turns_and_no_key_term(tmp_path, terms):
    run_dir = stub_run(tmp_path, "heron-desk", LEAKY_REPLY)
    out = failures(run_dir)
    assert "asked the lead more than 3 questions in one turn" in out
    assert re.search(r"showed the lead internal codes, IDs, file paths or tool commands \(\d+ times?: T\d", out)
    assert "## Scores" in out and "precision:" in out
    found = seal.leaks_in(out, terms)
    assert not found, f"{len(found)} key terms in the failure report"
    assert not re.search(r"(?<![\w-])[KWUCD]\d{1,2}(?![\w-])", out), "no key item ID"
    assert "Priya" not in out and "works council" not in out.lower()


def test_run_py_failures_is_the_same_report(tmp_path):
    run_dir = stub_run(tmp_path, "heron-desk", LEAKY_REPLY)
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--failures", str(run_dir)],
                          capture_output=True, text=True, timeout=300)
    assert done.returncode == 0 and done.stdout.strip() == failures(run_dir).strip()


def test_a_holdout_gets_scores_only_unless_revealed(tmp_path, terms):
    run_dir = stub_run(tmp_path, "coastal-merger", LEAKY_REPLY)
    sealed = failures(run_dir)
    assert "Sealed: coastal-merger is a holdout persona" in sealed and "## Scores" in sealed
    assert "What went wrong" not in sealed
    revealed = failures(run_dir, "--reveal")
    assert "What went wrong" in revealed and not seal.leaks_in(revealed, terms), "revealed patterns are still redacted"


def test_a_term_that_survives_redaction_stops_the_report(monkeypatch):
    failures_mod = load("failures")
    monkeypatch.setattr(failures_mod.seal, "redact", lambda text, terms: (text, 0))
    with pytest.raises(RuntimeError, match="survived the redaction pass"):
        failures_mod.redacted("Priya Menon said so.", seal.persona_terms())


def test_the_lead_unsure_then_an_owner_filed_is_a_pattern(tmp_path):
    """The example the report exists for: the lead didn't know, and the next turn filed an owner without asking."""
    failures_mod = load("failures")

    class FakeRun:
        wrappers = frozenset()
        turn_tools = {2: [{"name": "Bash", "input": "vela add unknown --name x --owner @sim-lead", "result": "",
                           "error": False}],
                      4: [{"name": "Bash", "input": "vela add unknown --name y --owner @sim-lead", "result": "",
                           "error": False}]}

        def spoken(self):
            return [{"turn": 1, "session": 1, "speaker": "lead", "text": "Honestly not sure who'd own that."},
                    {"turn": 2, "session": 1, "speaker": "assistant", "text": "Logged it as open."},
                    {"turn": 3, "session": 1, "speaker": "lead", "text": "No idea, really."},
                    {"turn": 4, "session": 1, "speaker": "assistant",
                     "text": "I'd put the endpoint lead down as owner. Is that right?"}]

    assert failures_mod.unsure_filed(FakeRun()).where == [2], "proposing an owner and asking is the right move"
