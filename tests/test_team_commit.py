"""`vela team commit` (Task 24's companion): a team session's commit goes through vela by exact path, so design and
breakdown never stage by hand once the hook denies it."""
import json
import shutil

import pytest

from conftest import REPO, run
from test_close_stage import change, committed, git

TEMPLATE = REPO / "template"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(TEMPLATE, root)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Team Lead")
    git(root, "config", "user.email", "team@example.com")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    git(root, "switch", "-q", "-c", "design/heron")
    return root


def commit(root, *extra):
    return run("team", "commit", "--vault", str(root), *extra)


def test_the_teams_files_are_committed_by_path_and_the_plan_is_left_out(repo):
    (repo / ".gitignore").unlink()  # even with the ignore file lost, the inbox can't ride a design commit
    git(repo, "commit", "-q", "-am", "drop ignore")
    change(repo, "docs/tech-design/heron.md", "# Heron design\n")
    change(repo, "CONTEXT.md", "Heron words\n")
    change(repo, "01-goals.md")
    change(repo, ".inbox/call.md")
    code, out = commit(repo, "--about", "the walking skeleton", "--json")
    assert code == 1, out  # something was left out, and it says what
    data = json.loads(out)
    assert committed(repo) == ["CONTEXT.md", "docs/tech-design/heron.md"]
    assert git(repo, "log", "-1", "--format=%s").strip() == "design: the walking skeleton"
    assert [n["rule"] for n in data["never"]] == ["inbox"]
    assert [left["path"] for left in data["left"]] == ["01-goals.md"]


def test_main_is_refused_and_nothing_is_committed(repo):
    git(repo, "switch", "-q", "main")
    change(repo, "docs/plan/heron-breakdown.md", "# Plan\n")
    head = git(repo, "rev-parse", "HEAD")
    code, out = commit(repo, "--about", "story one", "--for-lead")
    assert code == 1 and "main" in out and "review" in out
    assert git(repo, "rev-parse", "HEAD") == head


def test_nothing_of_the_teams_changed_is_said_plainly(repo):
    change(repo, "01-goals.md")
    code, out = commit(repo, "--about", "x", "--for-lead")
    assert code == 1 and "nothing to save" in out


# ---- the yes gate: a design choice is committed only after a person's capture names it ----

from vela import designchoice, say  # noqa: E402
from vela.edge import saidlog  # noqa: E402

CHOICE_DOC = "# Heron design\n\n## Decisions\n\n- We'll keep the calendar key behind a small interface.\n"


def add_yes(root, words, origin=None):
    """The senior's capture, as the design skill writes it: `vela record add` on the design branch."""
    extra = ("--origin", origin) if origin else ("--origin", "@sam")
    if not origin:
        saidlog.append(root, "test-session", "2026-10-14T09:00:00Z", words)  # the senior typed it, as the hook logs it
    return run("record", "add", "--vault", str(root), *extra, "--tag", "decision", words)


def test_a_design_choice_nobody_said_yes_to_is_refused_in_plain_words_and_nothing_changes(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    head = git(repo, "rev-parse", "HEAD")
    code, out = commit(repo, "--about", "the key", "--for-lead")
    assert code == 3, out
    assert out.strip().startswith("This adds a choice nobody has said yes to: ")
    assert "keep the calendar key behind a small interface" in out
    assert out.strip().endswith("Ask, record the yes, then commit.")
    assert say.leak_in(out) is None, out  # no code or ID reaches the person
    assert git(repo, "rev-parse", "HEAD") == head


def test_the_refusal_names_the_choice_in_json_for_the_model(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    code, out = commit(repo, "--about", "the key", "--json")
    assert code == 3 and json.loads(out)["needs_lead"][0]["ask"] == "design-yes"


def test_a_recorded_yes_that_names_the_choice_lets_it_through(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    code, out = add_yes(repo, "Yes, keep the calendar key behind a small interface.")
    assert code == 0, out
    code, out = commit(repo, "--about", "the key", "--json")
    assert code == 0, out
    assert committed(repo) == ["docs/tech-design/heron.md"]


def test_claudes_own_capture_is_not_a_yes(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    add_yes(repo, "I'd keep the calendar key behind a small interface.", origin="claude")
    code, out = commit(repo, "--about", "the key", "--for-lead")
    assert code == 3 and "nobody has said yes" in out


def test_a_yes_to_something_else_does_not_cover_the_choice(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    add_yes(repo, "Yes, ship the weekly report on Fridays.")
    code, out = commit(repo, "--about", "the key", "--for-lead")
    assert code == 3


def test_a_section_with_no_choice_commits_without_a_yes(repo):
    change(repo, "docs/tech-design/heron.md", "# Heron design\n\nThe calendar sends each entry with its time.\n")
    assert commit(repo, "--about", "the facts")[0] == 0


def test_a_choice_already_committed_is_not_asked_for_again(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    add_yes(repo, "Yes, keep the calendar key behind a small interface.")
    assert commit(repo, "--about", "the key")[0] == 0
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC + "\nMore prose.\n")
    assert commit(repo, "--about", "prose")[0] == 0


def test_the_detector_reads_adr_titles_decision_bullets_and_we_will_lines():
    adr = designchoice.added_choices("docs/adr/0001.md", "", "# ADR-0001 Use a queue\n\nDecision: we'll use a queue.\n")
    assert adr == ["# ADR-0001 Use a queue"]  # inside an ADR only the title counts
    doc = "We'll use SQLite for the cache.\n\n### Decisions\n\n- Key stays local\n\nProse.\n"
    assert designchoice.added_choices("docs/x.md", "", doc) == ["We'll use SQLite for the cache.", "- Key stays local"]
    assert designchoice.added_choices("docs/x.md", doc, doc) == []


def test_a_none_yet_bullet_under_decisions_is_no_choice(repo):
    change(repo, "docs/tech-design/heron.md", "# Heron\n\n**Decisions that shape it:**\n\n- None yet. Scope is open.\n")
    assert commit(repo, "--about", "scope")[0] == 0


# ---- the yes must be words the person typed (vela/said.py) ----

def test_an_unverified_yes_is_listed_for_the_lead_to_confirm_and_never_counted_silently(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    code, out = run("record", "add", "--vault", str(repo), "--origin", "@sam", "--tag", "decision",
                    "Yes, keep the calendar key behind a small interface.")  # no log here: hooks didn't fire
    assert code == 0 and "unverified" in out
    head = git(repo, "rev-parse", "HEAD")
    code, out = commit(repo, "--about", "the key", "--json")
    answer = json.loads(out)
    assert code == 3 and answer["needs_lead"][0]["ask"] == "design-confirm"
    assert "unverified" in answer["lines"][0] and "keep the calendar key behind a small interface" in answer["lines"][0]
    code, out = commit(repo, "--about", "the key", "--for-lead")
    assert code == 3 and out.strip().startswith("I couldn't check that you said yes to: ") and say.leak_in(out) is None
    assert git(repo, "rev-parse", "HEAD") == head
    assert run("record", "confirm", "--vault", str(repo), "1")[0] == 0
    assert commit(repo, "--about", "the key")[0] == 0


def test_the_models_own_sentence_cannot_become_the_seniors_yes(repo):
    change(repo, "docs/tech-design/heron.md", CHOICE_DOC)
    saidlog.append(repo, "test-session", "2026-10-14T09:00:00Z", "Sounds reasonable, go on.")
    code, out = add_yes(repo, "Yes, keep the calendar key behind a small interface.", origin="@sam")
    assert code == 3 and "Those aren't words the person typed" in out
    assert commit(repo, "--about", "the key")[0] == 3
