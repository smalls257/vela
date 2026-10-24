"""`vela check --fix W326` (overhaul Task 21b): close's "Check, then finish and send" sets a page's `state` as W326 says. One right answer, so
code does it and the model never hand-edits a state line."""
import json
import shutil

import pytest

from conftest import REPO, findings, run

GOALS = "01-goals.md"
CONSTRAINTS = "02-constraints.md"


@pytest.fixture
def booking(tmp_path):
    """The unified-booking example with its goals page set back to inkling: every goal on it is decided, so W326."""
    vault = tmp_path / "v"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    lower(vault / GOALS, "decided", "inkling")
    return vault


def lower(path, was, now):
    text = path.read_text(encoding="utf-8")
    assert f"\nstate: {was}\n" in text
    path.write_text(text.replace(f"\nstate: {was}\n", f"\nstate: {now}\n", 1), encoding="utf-8")


def cite_every_constraint(vault):
    """Two of the example's constraints cite nothing a check can see; give them a source so W326 can apply."""
    page = vault / CONSTRAINTS
    text = page.read_text(encoding="utf-8")
    for cell in ("Security and the existing Tidepay contract", "Transformation program standard"):
        assert text.count(cell) == 1
        text = text.replace(cell, f"{cell}, SRC-02")
    page.write_text(text, encoding="utf-8")


def state_of(path):
    head = path.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    return [line.split(":", 1)[1].strip() for line in head.splitlines() if line.startswith("state:")]


def w326(vault):
    return [p for code, p in findings(run("check", "--vault", str(vault))[1]) if code == "W326"]


def test_fix_w326_sets_state(booking):
    cite_every_constraint(booking)
    lower(booking / CONSTRAINTS, "fact", "assumption")
    assert sorted(w326(booking)) == [GOALS, CONSTRAINTS]
    code, out = run("check", "--fix", "W326", "--vault", str(booking))
    assert code == 0, out
    assert state_of(booking / GOALS) == ["decided"]
    assert state_of(booking / CONSTRAINTS) == ["fact"]
    assert w326(booking) == []


def test_fix_prints_what_changed(booking):
    before = (booking / GOALS).read_text(encoding="utf-8")
    code, out = run("check", "--fix", "W326", "--vault", str(booking))
    assert code == 0, out
    assert f"{GOALS}:" in out and "state: inkling -> decided" in out, out
    after = (booking / GOALS).read_text(encoding="utf-8")
    changed = [(a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b]
    assert changed == [("state: inkling", "state: decided")]  # the state line and nothing else

    code, out = run("check", "--fix", "W326", "--vault", str(booking))
    assert code == 0 and "nothing to change" in out.lower(), out


def test_fix_json_and_for_lead(booking):
    shutil.copytree(booking, booking.parent / "b")
    code, out = run("check", "--fix", "W326", "--json", "--vault", str(booking))
    assert code == 0, out
    data = json.loads(out)
    assert data["wrote"] == [GOALS]
    assert data["changed"] == [{"path": GOALS, "page": "goals", "from": "inkling", "to": "decided",
                                        "line": 7}]
    code, out = run("check", "--fix", "W326", "--for-lead", "--vault", str(booking.parent / "b"))
    assert code == 0, out
    assert "Unified Booking" in out and "W326" not in out


def test_fix_reports_what_the_new_state_still_owes(booking):
    """A constraints page moved to fact must list its sources (E304). The fix sets the state and says what is left,
    rather than reporting a clean page that check then fails (Silent Fallback)."""
    page = booking / CONSTRAINTS
    cite_every_constraint(booking)
    lower(page, "fact", "inkling")
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace('sources: ["session 2026-07-09 Discover", SRC-02, SRC-03]\n', "", 1), encoding="utf-8")
    code, out = run("check", "--fix", "W326", "--vault", str(booking))
    assert code == 1, out
    assert state_of(page) == ["fact"]
    assert "E304" in out and CONSTRAINTS in out, out


def test_fix_other_code_refused(booking):
    before = (booking / GOALS).read_text(encoding="utf-8")
    code, out = run("check", "--fix", "W390", "--vault", str(booking))
    assert code == 1, out
    assert "W326" in out and "W390" in out, out
    assert (booking / GOALS).read_text(encoding="utf-8") == before
    code, out = run("check", "--fix", "W326", "--gate", "epics", "--vault", str(booking))
    assert code == 1, out
    assert (booking / GOALS).read_text(encoding="utf-8") == before


def test_check_without_fix_unchanged(booking):
    before = (booking / GOALS).read_text(encoding="utf-8")
    code, out = run("check", "--vault", str(booking))
    assert "W326" in out and out.startswith("vela check:"), out
    assert (booking / GOALS).read_text(encoding="utf-8") == before
    code, out = run("check", "--json", "--vault", str(booking))
    assert code == 2, out  # --json still belongs to the grill verdicts (and now --fix) only


def test_set_state_touches_only_the_frontmatter_line():
    from vela import w326fix
    text = "---\nid: goals\nstate: inkling\n---\n\nstate: inkling in the body stays\n"
    assert w326fix.set_state(text, "decided") == "---\nid: goals\nstate: decided\n---\n\nstate: inkling in the body stays\n"
    with pytest.raises(w326fix.NoStateLine):
        w326fix.set_state("---\nid: goals\n---\n\nstate: inkling\n", "decided")


def test_target_is_read_from_the_finding_or_fails_loudly():
    from vela import w326fix
    from vela.model import Finding
    ok = Finding("01-goals.md", 7, "W326", "goals is inkling, but every goal on it is at least decided.",
                 "Set state: decided, the least settled goal, with the page's Decision in its History.")
    assert w326fix.target(ok) == "decided"
    with pytest.raises(w326fix.FixDrift):
        w326fix.target(Finding("01-goals.md", 7, "W326", "x", "Raise the page's state."))


def test_set_state_changes_only_the_state_line_and_keeps_line_endings_and_escaped_links():
    """A report said the fix broke links in table cells. It rewrites only the frontmatter state line: an escaped
    label pipe in a table cell, and a page saved with Windows line endings, come back byte for byte."""
    from vela import w326fix
    row = "| G1 | Stop it (see [[02-constraints#Constraints\\|the constraints]]) | decided |"
    for nl in ("\n", "\r\n"):
        text = nl.join(["---", "id: goals", "state: inkling", "---", "", "| ID | Goal | State |", "|---|---|---|", row, ""])
        after = w326fix.set_state(text, "decided")
        assert after == text.replace("state: inkling", "state: decided")
