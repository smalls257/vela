"""E316: a decided item an open question blocks. A decision that noted a question excuses that question only."""
import shutil

from conftest import REPO, edit, findings, run
import session_files

FIXTURE = REPO / "examples" / "unified-booking"
BOOKING = "05-building-blocks/booking-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
TODAY = "2026-11-21"
RECORD_ID = "2026-11-21-challenge-con-001"
RECORD = f"""---
id: {RECORD_ID}
type: session
title: "Challenge: CON-001"
date: 2026-11-21
modes: [challenge]
status: closed
summary: A challenge on CON-001.
---

# 2026-11-21 Challenge: CON-001

## Captures

- [worry] (@hl-port-senior) Does the hold survive a kiosk queue? ^c01
"""


def unknown(number, question):
    return f"""### UNK-{number} {question}

- **Question:** {question}
- **Owner:** @hl-port-senior (Port Systems senior)
- **Opened:** 2026-11-21 challenge by @hl-port-senior
- **State:** open
- **Ask by:** 2026-12-05
- **Blocks:** [[booking-building-blocks#CON-001 Booking API|CON-001]]

"""


def vault_with(tmp_path, noted, *questions):
    """CON-001, decided, with these open questions blocking it; `noted` is what its Decided with open bullet lists."""
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / UNKNOWNS, "## Risks\n", "\n".join(unknown(n, q) for n, q in questions) + "## Risks\n")
    if noted:
        page = vault / BOOKING
        page.write_text(page.read_text(encoding="utf-8") + f"\n## History\n\n#### CON-001\n\n"
                        f"- **Decided with open:** {noted}\n", encoding="utf-8")
    session_files.write_record(vault, RECORD_ID, RECORD)
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def test_e316_skips_a_question_the_decision_noted(tmp_path):
    vault = vault_with(tmp_path, "UNK-009", ("009", "Does the hold survive a queue?"))
    code, out = run("check", "--vault", str(vault), "--today", TODAY)
    assert findings(out) == [] and code == 0, out


def test_e316_still_fires_for_a_question_opened_later(tmp_path):
    vault = vault_with(tmp_path, "UNK-009", ("009", "Does the hold survive a queue?"),
                       ("010", "Can a kiosk renew a hold?"))
    code, out = run("check", "--vault", str(vault), "--today", TODAY)
    assert code == 1 and findings(out) == [("E316", BOOKING)], out
    assert "open unknown UNK-010 blocks it" in out and "UNK-009 blocks" not in out, out


def test_an_unlisted_question_is_not_excused_by_a_missing_bullet(tmp_path):
    vault = vault_with(tmp_path, "", ("009", "Does the hold survive a queue?"))
    code, out = run("check", "--vault", str(vault), "--today", TODAY)
    assert code == 1 and findings(out) == [("E316", BOOKING)], out
