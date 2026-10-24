"""Plans with an open session for the companion tests: the example vault in a git repo with a grill open on it, and
the stress vault with a long one. Built in tmp_path; the notes are written the way vela writes them."""
import pathlib
import shutil
import subprocess
import sys

from conftest import REPO
from vela import privaterecord

sys.path.insert(0, str(REPO / "tests" / "fixtures" / "explorer"))
import make_stress_vault  # noqa: E402

EXAMPLE = REPO / "examples" / "unified-booking"
SESSION = "2026-10-24-hold-pay-confirm-again"
TODAY = "2026-10-24"
UNK_009 = ("### UNK-009 Tidepay outcome wording\n\n"
           "- **Question:** What does Tidepay call a payment it is still checking?\n"
           "- **Owner:** @hl-booking-senior (Booking senior)\n- **Opened:** 2026-10-24 Grill\n- **State:** open\n"
           "- **Blocks:** [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007]]\n\n")


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


def notes(session=SESSION, summary="Settle how a crossing is held, paid and confirmed.", captures=14, extra_rows=()):
    lines = [f"- [decision] (@hl-solution-lead) \"Yes, that's how it should work.\" ^c{n:02d}" for n in range(1, captures + 1)]
    rows = [f"| FLO-001 | assumption | decided | [[{session}#^c09]] |",
            f"| RUN-booking | assumption | decided | [[{session}#^c10]] |",
            f"| UNK-009 | - | open | [[{session}#^c13]] |", *extra_rows]
    return (f"---\nid: {session}\npart: 1\nsummary: \"{summary}\"\n---\n\n# {TODAY} Grill: hold, pay, confirm\n\n"
            "## Agenda\n\n- FLO-001: GATE-3 confirmed yes, status decided\n"
            "- RUN-booking: GATE-3 confirmed yes, status decided\n"
            "- CON-007: GATE-3 confirmed yes, status off-agenda: UNK-009\n"
            "- RUN-pricing: GATE-3 confirmed yes, status open\n\n"
            f"## Ready to decide\n\n- CON-007: the lead said yes in {session} (^c12)\n\n"
            "## Captures\n\n" + "\n".join(lines) + "\n\n## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"
            + "\n".join(rows) + "\n")


def open_session(root, session=SESSION, text=None, opened=TODAY):
    root = pathlib.Path(root)
    stub = privaterecord.new_stub(session, "Grill: hold, pay, confirm", opened, ["grill"], branch="main",
                                  start_commit=head(root))
    (root / "sessions" / "private").mkdir(parents=True, exist_ok=True)
    (root / privaterecord.stub_path(session)).write_text(stub, encoding="utf-8")
    (root / privaterecord.private_path(session)).write_text(text if text is not None else notes(session), encoding="utf-8")
    return root


def head(root):
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def grill_session(tmp_path, opened=TODAY):
    """The example in a repo, committed; then the session's own edits, uncommitted: UNK-009 added, two pages decided."""
    root = pathlib.Path(tmp_path) / "plan"
    shutil.copytree(EXAMPLE, root)
    git(root.parent, "init", "-q", str(root))
    git(root, "add", "-A")
    git(root, "commit", "-qm", "plan")
    open_session(root, opened=opened)
    unknowns = root / "11-unknowns-and-risks.md"
    unknowns.write_text(unknowns.read_text(encoding="utf-8").replace("## Risks", UNK_009 + "## Risks", 1), encoding="utf-8")
    flow = root / "06-runtime/flows/FLO-001-hold-pay-confirm.md"
    flow.write_text(flow.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return root


def stress_session(tmp_path):
    """The 24-app synthetic vault in a repo with a long grill open: 40 captures, a 10-item agenda, 12 Changes rows."""
    root = pathlib.Path(tmp_path) / "stress"
    make_stress_vault.main(root)
    git(root.parent, "init", "-q", str(root))
    git(root, "add", "-A")
    git(root, "commit", "-qm", "stress")
    from vela import pageindex  # the ids the generator wrote, so the rows name real items
    from vela.edge import companionstore
    ids = sorted(pageindex.names(companionstore.page_index(root)))
    contracts = [i for i in ids if i.startswith("CON-")][:12]
    rows = [f"| {c} | assumption | decided | [[{SESSION}#^c{n + 10:02d}]] |" for n, c in enumerate(contracts)]
    text = notes(captures=40).replace("| UNK-009 | - | open |", "\n".join(rows) + "\n| UNK-009 | - | open |", 1)
    agenda = "".join(f"- {c}: GATE-3 confirmed yes, status {'decided' if n < 6 else 'open'}\n" for n, c in enumerate(contracts[:10]))
    text = text.replace("## Agenda\n\n", "## Agenda\n\n" + agenda, 1)
    open_session(root, text=text)
    return root


def run_companion(root, *args, today=TODAY, now="10:41"):
    """(exit code, stdout) of `vela companion ...` in-process through the fast entry."""
    import io
    from vela.commands import fast
    out = io.StringIO()
    code = fast.main(["companion", *args, "--vault", str(root), "--today", today, "--now", now], out)
    return code, out.getvalue()
