"""The undisposed-questions block, the digest and the not-applicable counts.

The digest is what the lead sees. It ranks and groups, and it never leaves a question out: the
lead sets the pace, so there is no cap, and whatever is not taken stays visible."""
import json
import shutil

import pytest

from planner import questions
from conftest import REPO, check, edit, findings, run

FIXTURE = REPO / "examples" / "unified-booking"
LEDGER = "11-unknowns-and-risks.md"
TODAY = "2026-11-20"
OPS_KIOSKS = "| Q-OPS-01@APP-kiosks |"
OPS_PRICING = "| Q-OPS-01@APP-pricing |"
DAT_02_ALL = "| Q-DAT-02@APP-* |"
DAT_03_ALL = "| Q-DAT-03@CON-* |"
PTN_02_TIDEPAY = "| Q-PTN-02@PTY-01 |"
DAT_02_PRICING = "| Q-DAT-02@APP-pricing |"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def drop(vault, *prefixes):
    """Remove the one ledger row that starts with each prefix, so the copy it covered is owed again."""
    page = vault / LEDGER
    lines = page.read_text(encoding="utf-8").splitlines(keepends=True)
    for prefix in prefixes:
        hits = [l for l in lines if l.startswith(prefix)]
        assert len(hits) == 1, (prefix, hits)
        lines.remove(hits[0])
    page.write_text("".join(lines), encoding="utf-8")


def block(vault):
    text = (vault / LEDGER).read_text(encoding="utf-8")
    return text[text.index("<!-- generated:undisposed-questions"):text.index("<!-- /generated:undisposed-questions -->")]


def digest(vault, *extra):
    code, out = run("questions", "--vault", str(vault), "--digest", "--json", *extra)
    assert code == 0, out
    return json.loads(out)


# ------------------------------------------------------------------ the block

def test_the_fixture_block_says_nothing_is_undisposed():
    assert block(FIXTURE).splitlines()[1] == "**Questions:** 57 owed, 0 undisposed, against catalogue v1."
    assert "| Copy |" not in block(FIXTURE)


def test_the_template_block_lists_the_twelve_initiative_questions():
    lines = block(REPO / "template").splitlines()
    assert lines[1] == "**Questions:** 12 owed, 12 undisposed, against catalogue v1."
    assert lines[3] == "| Copy | Area | Severity | Subject | Question |"
    assert len([l for l in lines if l.startswith("| Q-")]) == 12


def test_removing_a_row_makes_the_block_stale_and_render_lists_the_copies(ub):
    drop(ub, OPS_KIOSKS)
    assert findings(check(ub, TODAY)[1]) == [("W402", LEDGER)]
    run("render", "--vault", str(ub))
    text = block(ub)
    assert "**Questions:** 57 owed, 1 undisposed, against catalogue v1." in text
    assert "| Q-OPS-01@APP-kiosks | OPS | normal | [[kiosks-building-blocks\\|Port kiosks]] | Who runs it out of hours" in text
    assert "Q-OPS-01@APP-booking" not in text, "booking has its own row"
    assert findings(check(ub, TODAY)[1]) == []


def test_an_open_row_counts_as_undisposed_but_is_not_listed_as_missing(ub):
    drop(ub, DAT_02_PRICING)
    edit(ub / LEDGER, "| Q-DAT-03@CON-* |", "| Q-DAT-02@APP-pricing | open |  |  |  |\n| Q-DAT-03@CON-* |")
    run("render", "--vault", str(ub))
    assert "57 owed, 1 undisposed" in block(ub) and "| Copy |" not in block(ub)


def test_the_block_is_allowed_only_on_the_unknowns_page(ub):
    edit(ub / "12-glossary.md", "# Glossary", "# Glossary\n\n<!-- generated:undisposed-questions sha=00000000: do not edit, "
         "run planner render -->\n<!-- /generated:undisposed-questions -->")
    assert ("E403", "12-glossary.md") in findings(check(ub, TODAY)[1])


def test_render_is_a_no_op_on_the_fixture_and_the_template(tmp_path):
    for source in (FIXTURE, REPO / "template"):
        vault = tmp_path / source.name
        shutil.copytree(source, vault)
        before = {p: p.read_bytes() for p in vault.rglob("*.md")}
        code, out = run("render", "--vault", str(vault))
        assert code == 0 and "0 blocks changed" in out, out
        assert {p: p.read_bytes() for p in vault.rglob("*.md")} == before


# ------------------------------------------------------------------ the digest

def test_the_digest_ranks_high_and_blocking_first_and_groups_one_entry(ub):
    drop(ub, DAT_02_ALL, DAT_03_ALL, PTN_02_TIDEPAY, OPS_KIOSKS, OPS_PRICING)
    answer = digest(ub)
    assert answer["coverage"] == "57 owed, 12 undisposed, against catalogue v1"
    order = [(g["band"], g["entry"]) for g in answer["groups"]]
    assert order == [(1, "Q-DAT-02"), (1, "Q-PTN-02"), (3, "Q-DAT-03"), (3, "Q-OPS-01"), (3, "R-FIN-01")]
    dat = answer["groups"][0]
    assert dat["copies"] == ["Q-DAT-02@APP-call-centre", "Q-DAT-02@APP-kiosks", "Q-DAT-02@APP-website"]
    assert "Q-DAT-02@APP-pricing" not in dat["copies"], "its own not-applicable row still stands"
    assert "Q-DAT-02@APP-booking" not in dat["copies"], "its own unknown row still stands"
    assert dat["blocks"][:2] == ["APP-call-centre", "APP-kiosks"]
    assert answer["groups"][3]["copies"] == ["Q-OPS-01@APP-kiosks", "Q-OPS-01@APP-pricing"]


def test_the_bands_rank_high_and_blocking_above_high_above_the_rest():
    assert [questions._band(s, b) for s, b in (("high", ["APP-x"]), ("high", []), ("normal", ["APP-x"]), ("normal", []))] == [1, 2, 3, 3]


def test_a_broken_row_is_undisposed_and_still_listed_by_the_block(ub):
    edit(ub / LEDGER, "| Q-FIN-03@SV-01 | answered |", "| Q-FIN-03@SV-01 | answered | nonsense |")
    run("render", "--vault", str(ub))
    assert "Q-FIN-03@SV-01 | FIN" in block(ub)
    assert [g["entry"] for g in digest(ub)["groups"]][0] == "Q-FIN-03"


def test_the_digest_text_offers_one_answer_for_a_group(ub):
    drop(ub, OPS_KIOSKS, OPS_PRICING)
    code, out = run("questions", "--vault", str(ub), "--digest")
    assert code == 0
    assert out.splitlines()[0] == ("planner questions --digest: 57 owed, 2 undisposed, against catalogue v1. "
                                   "2 to take, most consequential first.")
    assert "1. [OPS] normal, blocks APP-kiosks, APP-pricing: Who runs it" in out
    assert "Q-OPS-01@APP-kiosks, Q-OPS-01@APP-pricing: one answer for all?" in out
    assert "2. [FIN] normal: Points are earned at reservation" in out


def test_the_digest_never_drops_a_question(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "template", vault)
    answer = digest(vault)
    assert sum(len(g["copies"]) for g in answer["groups"]) == answer["undisposed"] == 12


def test_the_digest_is_the_same_on_every_run(ub):
    drop(ub, OPS_KIOSKS)
    assert digest(ub) == digest(ub)


def test_the_digest_filters_by_area(ub):
    drop(ub, OPS_KIOSKS)
    assert [g["entry"] for g in digest(ub, "--area", "FIN")["groups"]] == ["R-FIN-01"]


# ------------------------------------------------------------------ the counts

def test_stats_count_how_each_entry_ended():
    code, out = run("questions", "--vault", str(FIXTURE), "--stats", "--json")
    assert code == 0
    entries = {e["entry"]: e for e in json.loads(out)["entries"]}
    assert len(entries) == 29
    assert entries["Q-DAT-02"] == {"entry": "Q-DAT-02", "area": "DAT", "owed": 6,
                                   "states": {"answered": 1, "assumed": 3, "unknown": 1, "not-applicable": 1},
                                   "not_applicable": 1, "not_applicable_share": 0.17}
    assert entries["Q-REG-03"]["owed"] == 0 and entries["Q-REG-03"]["not_applicable_share"] == 0.0
    code, out = run("questions", "--vault", str(FIXTURE), "--stats")
    assert "Q-REG-01 | REG | owed 1 | not-applicable 1 of 1 (100%) | not-applicable 1" in out


def test_stats_refuse_filters_they_cannot_honour():
    assert run("questions", "--vault", str(FIXTURE), "--stats", "--open")[0] == 2
    assert run("questions", "--vault", str(FIXTURE), "--stats", "--digest")[0] == 2
