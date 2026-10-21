"""Build one eval workspace in the current directory. Called by each case's fixture.sh.

Usage: python3 scaffold.py <vault> <arm>
  vault: template | discover-docs | close-dump | fixture | grill-refused | epics-empty
  arm:   plugin (the full plugin is installed at .claude/skills/vela)
         stub   (only bin/, lib/ and catalog/ are installed, so the baseline arm can run vela but sees no skill text)

The workspace ends as a git repository on main with one commit, as a real vault would be.
Any failure exits non-zero, which plugin eval reports as "scaffold failed".
"""
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path.cwd()
CAPTURES = """---
id: 2026-10-05-mainframe-breaks-booking
type: session
date: 2026-10-05
modes: [dump]
status: open
summary: In progress.
---

# 2026-10-05 Dump: mainframe breaks booking

## Captures

- [thought] (solution lead) Every time the mainframe team changes a screen, all three front ends break. ^c01
- [unknown] (solution lead) We don't know whether the mainframe team has any capacity in Q1. ^c02
- [idea] (claude) What if every channel called one booking service instead of scraping screens? ^c03
- [wild] (claude) What if the kiosks stopped selling and only printed tickets? ^c04
- [worry] (Head of Contact Center) Agents fix failed bookings by hand every morning, and nobody counts them. ^c05
- [idea] (solution lead) The website could go first; it has the most traffic and the newest code. ^c06
- [unknown] (claude) We don't know whether the mainframe team can host a booking service. ^c07

## Changes

| ID | From | To | Source |
|---|---|---|---|
"""


INBOX = {
    "ferrymaster-mq-transactions.md": """# FERRYMASTER MQ transactions

Owner: mainframe team lead. Written 2026-06-02.

FERRYMASTER accepts four booking transactions over MQ today: BKHOLD, BKCONF, BKAMND and BKCANC. The nightly finance job already sends BKCONF and reads the replies. Each transaction answers within 3 seconds at the 95th percentile on the production region. The test region is refreshed once a year, in January.
""",
    "program-deck-2026.md": """# Transformation program: 2026 roadmap

Slide 4. Every new application publishes its events to the Harborline event bus.

Slide 7. The event bus will be ready in Q4. Teams can plan to publish from October.

Slide 9. Payment stays with Tidepay until the contract ends in 2028.
""",
    "call-center-fix-queue.md": """# Call center: the morning fix queue

Owner: Head of Contact Center. Written 2026-08-20.

Each morning two agents work through bookings the website took payment for but never confirmed. In August that was between 30 and 50 bookings a day. Agents re-enter each one on the mainframe screen and email the customer.
""",
}


def fail(message):
    print(f"scaffold: {message}", file=sys.stderr)
    sys.exit(1)


def copy_tree(src, dest):
    if not src.is_dir():
        fail(f"{src} is missing; run the eval from a full toolkit checkout")
    shutil.copytree(src, dest, dirs_exist_ok=True)


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        fail(f"{path.name}: expected one '{old[:50]}', found {text.count(old)}; the fixture changed, update scaffold.py")
    path.write_text(text.replace(old, new), encoding="utf-8")


def grill_refused():
    """UNK-001 reopened and blocking CAP-021, which is back at assumption so the vault starts clean."""
    edit(HERE / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[CAP-021-amend-or-cancel|CAP-021]]\n")
    cap = HERE / "capabilities" / "CAP-021-amend-or-cancel.md"
    edit(cap, "state: decided\n", "state: assumption\n")
    edit(cap, "- **Decision:** [[2026-08-12-goals-and-data]]\n\n", "")


EPIC_LINK = re.compile(r"\[\[(EPC-\d{3}-[a-z0-9-]+)(?:#[^|\]]*)?(?:\\?\|([^\]]+))?\]\]")


def epics_empty():
    """Every epic page goes; links to them become plain text, so the vault starts with no broken link."""
    for path in (HERE / "13-epics").glob("EPC-*.md"):
        path.unlink()
    for path in HERE.rglob("*.md"):
        if ".claude" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        new = EPIC_LINK.sub(lambda m: m.group(2) or m.group(1), text)
        if new != text:
            path.write_text(new, encoding="utf-8")


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("plugin", "stub"):
        fail("usage: scaffold.py <template|discover-docs|close-dump|fixture|grill-refused|epics-empty> <plugin|stub>")
    vault, arm = sys.argv[1:]
    if vault in ("template", "discover-docs", "close-dump"):
        copy_tree(REPO / "plugin" / "template", HERE)
    elif vault in ("fixture", "grill-refused", "epics-empty"):
        copy_tree(REPO / "examples" / "unified-booking", HERE)
        shutil.copy(REPO / "plugin" / "template" / "CLAUDE.md", HERE / "CLAUDE.md")
        if not (HERE / "voice").exists():
            copy_tree(REPO / "plugin" / "template" / "voice", HERE / "voice")
    else:
        fail(f"unknown vault '{vault}'")
    if vault == "discover-docs":
        (HERE / ".inbox").mkdir()
        for name, text in INBOX.items():
            (HERE / ".inbox" / name).write_text(text, encoding="utf-8")
    if vault == "close-dump":
        (HERE / "sessions" / "2026-10-05-mainframe-breaks-booking.md").write_text(CAPTURES, encoding="utf-8")
    if vault == "grill-refused":
        grill_refused()
    if vault == "epics-empty":
        epics_empty()
    target = HERE / ".claude" / "skills" / "vela"
    if arm == "plugin":
        copy_tree(REPO / "plugin", target)
    else:
        copy_tree(REPO / "plugin" / "scripts", target / "scripts")
        copy_tree(REPO / "plugin" / "lib", target / "lib")
        copy_tree(REPO / "plugin" / "catalog", target / "catalog")
    vela = [sys.executable, str(target / "scripts" / "vela")]
    # epics-empty rewrote links inside generated blocks too; render puts those blocks back.
    extra = ["--discard-edits"] if vault == "epics-empty" else []
    render = subprocess.run(vela + ["render"] + extra, capture_output=True, text=True, timeout=120)
    if render.returncode != 0:
        fail("vela render failed:\n" + render.stdout + render.stderr)
    git = ["git", "-c", "user.name=Eval", "-c", "user.email=eval@example.invalid"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "Vault before the eval run"]):
        result = subprocess.run(git + args, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            fail(f"git {args[0]} failed: {result.stderr}")
    if vault == "close-dump":
        result = subprocess.run(git + ["switch", "-q", "-c", "session/2026-10-05-mainframe-breaks-booking"],
                                capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            fail(f"git switch failed: {result.stderr}")


if __name__ == "__main__":
    main()
