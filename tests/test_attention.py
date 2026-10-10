"""One light per app, contract and flow: the worst single sign, with its reasons."""
import shutil
import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "plugin" / "lib"))
from planner import attention, cli  # noqa: E402

FIXTURE = REPO / "examples" / "unified-booking"


def lit(vault_dir, as_of="2026-11-20"):
    found, above = attention.lights(cli.load_vault(vault_dir), as_of)
    return found, above


def test_a_settled_vault_is_dark_but_for_the_recorded_override():
    found, above = lit(FIXTURE)
    assert {s for s, l in found.items() if l.level != "dark"} == {"CON-003"}
    assert found["CON-003"].level == "override" and above == []


def test_an_open_question_past_its_date_is_a_warning_and_ranks_first(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "11-unknowns-and-risks.md"
    text = page.read_text(encoding="utf-8")
    text = text.rstrip("\n") + (
        "\n\n### UNK-099 Seat map vendor terms\n\nWhether the seat map vendor allows holds.\n\n"
        "- **Question:** Do the vendor terms allow a ten-minute hold?\n- **Owner:** @hl-solution-lead\n"
        "- **State:** open\n- **Blocks:** [[booking-building-blocks]]\n- **Ask by:** 2026-11-01\n")
    page.write_text(text, encoding="utf-8")
    found, _ = lit(vault)
    assert found["APP-booking"].level == "warning" and found["APP-booking"].urgency == 1.0
    assert attention.ranked(found)[0][0] == "APP-booking"
    assert any(r.get("unknown") == "UNK-099" for r in found["APP-booking"].reasons)


def test_dark_has_to_be_earned(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "05-building-blocks" / "kiosks-building-blocks.md"
    page.write_text("\n".join(l for l in page.read_text(encoding="utf-8").splitlines()
                              if not l.startswith("state:")) + "\n", encoding="utf-8")
    found, _ = lit(vault)
    assert found["APP-kiosks"].level == "unexamined"


def test_ask_names_who_holds_the_answer(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "11-unknowns-and-risks.md"
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + (
        "\n\n### UNK-099 Seat map vendor terms\n\nWhether the seat map vendor allows holds.\n\n"
        "- **Question:** Do the vendor terms allow a ten-minute hold?\n- **Owner:** @hl-solution-lead\n"
        "- **Ask:** @vendor-manager\n- **State:** open\n- **Blocks:** [[booking-building-blocks]]\n- **Ask by:** 2026-12-01\n"),
        encoding="utf-8")
    found, _ = lit(vault)
    held = [r for r in found["APP-booking"].reasons if r.get("unknown") == "UNK-099"]
    assert held and held[0]["ask"] == "@vendor-manager"
    from conftest import run
    import json
    answer = json.loads(run("query", "get", "UNK-099", "--vault", str(vault), "--json")[1])
    assert answer["ask"] == "@vendor-manager"


def test_one_question_light_matches_what_it_holds(tmp_path):
    vault = cli.load_vault(FIXTURE)
    for unknown in vault.unknowns:
        light = attention.question_light(unknown, "2026-11-20")
        assert light.level in attention.LEVELS and light.reasons[0]["unknown"] == unknown.id
