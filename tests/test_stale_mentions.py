"""W334: a page that still calls an answered question open."""
import shutil

from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"
LINK = "[[11-unknowns-and-risks#UNK-001 Ledger write latency|{label}]]"


def vault_saying(tmp_path, sentence):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "04-solution-strategy.md"
    text = page.read_text(encoding="utf-8")
    head, rest = text.split("\n# ", 1)
    title, body = rest.split("\n", 1)
    page.write_text(f"{head}\n# {title}\n\n{sentence}\n{body}", encoding="utf-8")
    return vault


def check(vault):
    return run("check", "--vault", str(vault), "--today", "2026-11-20")[1]


def test_a_sentence_calling_a_resolved_unknown_open_warns(tmp_path):
    out = check(vault_saying(tmp_path, "How fast the ledger writes is " + LINK.format(label="still open") + "."))
    assert "W334" in out and "UNK-001" in out, out


def test_the_question_named_by_its_own_heading_is_not_a_claim(tmp_path):
    out = check(vault_saying(tmp_path, "The team measured " + LINK.format(label="ledger write latency") + " in September."))
    assert "W334" not in out, out


def test_history_is_left_alone(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "04-solution-strategy.md"
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n")
                    + "\n\n## History\n\n- In August, " + LINK.format(label="ledger write latency") + " was still open.\n",
                    encoding="utf-8")
    assert "W334" not in check(vault)
