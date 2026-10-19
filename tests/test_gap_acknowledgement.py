"""A design gap's `acknowledged_by` claims a person accepted it. The Violation this guards is a Silent Fallback: a
session copied the lead's handle onto 21 gaps when the lead had accepted one. `designchoice.unnamed_gaps` is the one
rule; `vela team commit` and `vela check` both apply it, against the said log (`.vela/said/`)."""
import json

from conftest import run
from test_close_stage import change, git
from test_team_commit import commit, repo  # noqa: F401  (the fixture)
from vela import designchoice, say
from vela.edge import saidlog

DOC = """---
slug: heron
status: complete-with-gaps
last_session: 2026-10-14T09:00:00Z
gaps:
  - id: G-001
    what: "The quiet install has no weekend check-ins"
    acknowledged_by: "@sam"
    why: "weekday only"
    revisit: "if the pilot grows"
  - id: G-002
    what: "Calendar sync timing is open"
    acknowledged_by: "@sam"
    why: "later"
    revisit: "after the pilot"
---

# Heron design
"""
DESIGN = "docs/tech-design/heron.md"


def said(root, text):
    saidlog.append(root, "design", "2026-10-14T09:00:00Z", text)


def test_a_gap_the_lead_named_is_valid_and_one_they_never_named_is_refused(repo):
    change(repo, DESIGN, DOC)
    said(repo, "I accept the quiet install with no weekend check-ins.")
    code, out = commit(repo, "--about", "gaps", "--json")
    answer = json.loads(out)
    assert code == 3
    assert [n["ask"] for n in answer["needs_lead"]] == ["gap-yes"]
    assert "Calendar sync timing is open" in answer["needs_lead"][0]["gap"]


def test_naming_a_gap_by_its_id_counts(repo):
    change(repo, DESIGN, DOC)
    said(repo, "G-001 and G-002 are fine by me, accepted.")
    assert commit(repo, "--about", "gaps")[0] == 0


def test_every_gap_named_commits_and_the_refusal_is_plain_words(repo):
    change(repo, DESIGN, DOC)
    code, out = commit(repo, "--about", "gaps", "--for-lead")
    assert code == 3 and say.leak_in(out) is None, out
    head = git(repo, "rev-parse", "HEAD")
    said(repo, "Accept the quiet install with no weekend check-ins.")
    said(repo, "Calendar sync timing is open, and I accept that.")
    assert commit(repo, "--about", "gaps")[0] == 0
    assert git(repo, "rev-parse", "HEAD") != head


def test_with_no_said_log_the_gaps_are_unverified_and_listed_for_confirmation(repo):
    change(repo, DESIGN, DOC)
    code, out = commit(repo, "--about", "gaps", "--json")
    answer = json.loads(out)
    assert code == 3
    assert [n["ask"] for n in answer["needs_lead"]] == ["gap-confirm", "gap-confirm"]
    assert "unverified" in answer["lines"][0]


def test_a_gap_already_committed_is_not_asked_for_again(repo):
    change(repo, DESIGN, DOC)
    said(repo, "G-001 G-002 accepted")
    assert commit(repo, "--about", "gaps")[0] == 0
    change(repo, DESIGN, DOC + "\nMore prose.\n")
    assert commit(repo, "--about", "prose")[0] == 0


def test_check_errors_on_a_gap_nobody_named_and_is_quiet_on_one_they_did(repo):
    change(repo, DESIGN, DOC)
    said(repo, "I accept the quiet install with no weekend check-ins.")
    code, out = run("check", "--vault", str(repo))
    lines = [l for l in out.splitlines() if "gap G-" in l]
    assert len(lines) == 1 and "E821 gap G-002" in lines[0] and code == 1, out


def test_check_warns_not_errors_when_there_is_no_said_log(repo):
    change(repo, DESIGN, DOC)
    code, out = run("check", "--vault", str(repo))
    lines = [l for l in out.splitlines() if "gap G-" in l]
    assert len(lines) == 2 and all("W821" in l for l in lines), out
    assert "E821" not in out


def test_the_rule_is_pure_and_shared():
    gaps = designchoice.acknowledged_gaps(DOC)
    assert [g[0] for g in gaps] == ["G-001", "G-002"]
    assert designchoice.unnamed_gaps(gaps, ["g-002 ok"]) == [gaps[0]]
    assert designchoice.unnamed_gaps(gaps, None) == gaps
    assert designchoice.acknowledged_gaps("no frontmatter") == []


def test_a_background_agents_notice_in_the_log_is_not_the_leads_yes(repo):
    """The short run's log held `<task-notification>` summaries that named all 19 gaps; the model's own words must not
    back a handle."""
    change(repo, DESIGN, DOC)
    said(repo, "<task-notification>\n<result>G-001 and G-002 are accepted: the quiet install with no weekend "
               "check-ins, calendar sync timing is open</result>\n</task-notification>")
    code, out = commit(repo, "--about", "gaps", "--json")
    assert code == 3 and json.loads(out)["needs_lead"][0]["ask"] == "gap-yes"


def test_the_log_reader_drops_host_injected_notices_and_keeps_what_was_typed():
    from vela import said as said_words
    log = "\n".join([said_words.log_line("t", "<task-notification>x</task-notification>"),
                     said_words.log_line("t", "Yes, accepted.")])
    assert said_words.messages([log]) == ["Yes, accepted."]
