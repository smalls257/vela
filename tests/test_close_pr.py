"""`vela close pr` (overhaul Task 12): reviewers, the PR body, `gh pr create` (or `gh pr comment` on the challenge PR
for an answer session), the saved body when `gh` fails, and the handoff's PR number. `gh` is always a fake on PATH:
the sim's stub (only `pr create` works) or the one below, which logs each call with the body it was given."""
import importlib.util
import json
import re
import sys

from conftest import REPO, run
from sharing import git
from test_close_push import BRANCH, RECORD, TODAY, YES_WORDS, add_yes, push, remote_has, sent_session
from vela import prbody, say

FAKE_GH = """#!{python}
import json, os, sys
args = sys.argv[1:]
body = ""
if "--body-file" in args:
    body = open(args[args.index("--body-file") + 1], encoding="utf-8").read()
with open({log!r}, "a", encoding="utf-8") as out:
    out.write(json.dumps({{"args": args, "body": body}}) + "\\n")
mode = os.environ.get("FAKE_GH", "ok")
if args[:2] == ["api", "user"]:
    sys.exit(1)
if args[:2] == ["pr", "view"]:
    if os.environ.get("FAKE_GH_OPEN_PR"):
        print(json.dumps({{"number": 9, "url": "https://github.invalid/mini/vault/pull/9", "state": "OPEN"}}))
        sys.exit(0)
    print("no pull requests found for branch " + args[2], file=sys.stderr)
    sys.exit(1)
if mode == "fail":
    print("HTTP 502: the fake GitHub is down", file=sys.stderr)
    sys.exit(1)
if mode == "nourl":
    sys.exit(0)
if args[:2] == ["pr", "create"]:
    print("https://github.invalid/mini/vault/pull/7")
elif args[:2] == ["pr", "list"]:
    print(json.dumps([{{"number": 5, "url": "https://github.invalid/mini/vault/pull/5"}}]))
elif args[:2] == ["pr", "comment"]:
    print("https://github.invalid/mini/vault/pull/5#issuecomment-1")
else:
    sys.exit(1)
"""

CHALLENGE_BRANCH = "session/2026-10-18-challenge-con-002"
ANSWER = "2026-10-20-answer-con-002"


def fake_gh(tmp_path, monkeypatch, mode="ok"):
    bin_dir, log = tmp_path / "bin", tmp_path / "gh-calls.jsonl"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH.format(python=sys.executable, log=str(log)), encoding="utf-8")
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")
    monkeypatch.setenv("FAKE_GH", mode)
    return log


def calls(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


def pushed(tmp_path, **kwargs):
    vault, bare = sent_session(tmp_path, **kwargs)
    assert push(vault)[0] == 3
    number = add_yes(vault)
    code, out = push(vault, "--consent", number)
    assert code == 0, out
    return vault, bare


def pr(vault, *flags):
    return run("close", "pr", "--vault", str(vault), "--today", TODAY, *flags)


def created(log):
    return [c for c in calls(log) if c["args"][:2] == ["pr", "create"]]


def reviewers_of(call):
    args = call["args"]
    return [args[i + 1] for i, a in enumerate(args) if a == "--reviewer"]


def test_reviewers_drop_own_handle_and_keep_teams(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = pushed(tmp_path, stock_owner="@lead @mini/stock-team")
    code, out = pr(vault)
    assert code == 0, out
    (call,) = created(log)
    assert sorted(reviewers_of(call)) == ["mini/shop-team", "mini/stock-team"]
    assert "--head" in call["args"] and call["args"][call["args"].index("--head") + 1] == BRANCH
    assert call["args"][call["args"].index("--title") + 1] == f"{TODAY} Decisions: stock"
    assert "https://github.invalid/mini/vault/pull/7" in out


def test_a_branch_with_an_open_pull_request_gets_the_session_added_not_a_second_one(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_GH_OPEN_PR", "1")
    vault, _ = pushed(tmp_path)
    code, out = pr(vault, "--for-lead")
    assert code == 0, out
    assert not created(log)
    (comment,) = [c for c in calls(log) if c["args"][:2] == ["pr", "comment"]]
    assert comment["args"][2] == "9" and "**What changed**" in comment["body"]
    assert "already has a review open" in out and "pull/9" in out
    code, out = pr(vault, "--json")
    assert json.loads(out)["added_to_open"] is True


def test_gh_failure_saves_body_and_says_one_sentence(tmp_path, monkeypatch):
    fake_gh(tmp_path, monkeypatch, mode="fail")
    vault, _ = pushed(tmp_path)
    code, out = pr(vault, "--for-lead")
    assert code == 1, out
    assert out.strip() == prbody.SAVED_SENTENCE and "I've kept its text" in out
    saved = (vault / ".vela" / "pr-body.md").read_text(encoding="utf-8")
    assert "**What changed**" in saved
    code, out = pr(vault)
    assert code == 1 and "502" in out and "gh pr create" in out  # the default mode names what failed


def test_no_pr_claimed_without_url(tmp_path, monkeypatch):
    fake_gh(tmp_path, monkeypatch, mode="nourl")
    vault, _ = pushed(tmp_path)
    code, out = pr(vault, "--json")
    assert code == 1, out
    data = json.loads(out)
    assert data["url"] is None and (vault / ".vela" / "pr-body.md").is_file()
    assert "github.invalid" not in out


def test_the_body_says_what_changed_in_plain_words_and_nothing_else(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = pushed(tmp_path)
    assert pr(vault)[0] == 0
    body = created(log)[0]["body"]
    assert "- Stock level: now decided" in body
    assert YES_WORDS not in body and '"Yes, send it."' not in body
    assert re.findall(r"^\*\*(.+?)\*\*$", body, re.M) == ["What changed"]
    for gone in ("Needs a look", "Decisions", "Check", "Stage", "Voice review", "In their words", "Overrides",
                 "Questions still open", "Sent with your yes", "[[", " c01", "Filled in by the reviewer",
                 "Structural fixes", "Prose edits", "Does customer data cross"):
        assert gone not in body, gone


def test_pending_pr_number_written(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("sim_run_for_pr", REPO / "tests" / "sim" / "run.py")
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    vault, bare = pushed(tmp_path, stock_meta='handed_off: "Stock senior, 2026-10-20"\nhanded_off_pr: pending')
    sim.write_gh_stub(tmp_path / "simbin", bare)
    monkeypatch.setenv("PATH", f"{tmp_path / 'simbin'}:{__import__('os').environ['PATH']}")
    code, out = pr(vault)
    assert code == 0, out
    page = (vault / "05-building-blocks" / "stock-building-blocks.md").read_text(encoding="utf-8")
    assert 'handed_off: "Stock senior, 2026-10-20"\nhanded_off_pr: 1\n' in page
    assert git(vault, "log", "-1", "--format=%s") == "Handoff PR number for APP-stock"
    assert git(bare, "rev-parse", BRANCH) == git(vault, "rev-parse", "HEAD")


def test_prose_file_goes_first(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = pushed(tmp_path)
    prose = tmp_path / "prose.md"
    prose.write_text("Stock level is now decided. The shop team should check the read API.\n", encoding="utf-8")
    assert pr(vault, "--prose", str(prose))[0] == 0
    body = created(log)[0]["body"]
    assert body.startswith("Stock level is now decided.")
    assert "- Stock level: now decided" in body


def test_pr_before_push_refused(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = sent_session(tmp_path)
    code, out = pr(vault, "--for-lead")
    assert code == 1 and "isn't sent yet" in out, out
    assert "Shall I send it for review?" in out and "I'll send" not in out  # asks; never promises a send
    assert not created(log)


def test_answer_session_pushes_challenge_branch_and_comments(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, bare = sent_session(tmp_path, record_id=ANSWER, modes="answer, grill", title="Answer: CON-002",
                               on_branch=CHALLENGE_BRANCH)
    before = git(bare, "rev-parse", CHALLENGE_BRANCH)
    code, out = push(vault)
    assert code == 3 and f"`{CHALLENGE_BRANCH}`" in out and "comment on the challenge's pull request" in out, out
    number = add_yes(vault)
    code, out = push(vault, "--consent", number)
    assert code == 0, out
    assert git(bare, "rev-parse", CHALLENGE_BRANCH) == git(vault, "rev-parse", "HEAD") != before
    assert not remote_has(bare, f"session/{ANSWER}")
    code, out = pr(vault)
    assert code == 0, out
    assert not created(log)
    (comment,) = [c for c in calls(log) if c["args"][:2] == ["pr", "comment"]]
    assert comment["args"][2] == "5"
    assert "**What changed**" in comment["body"]
    assert "https://github.invalid/mini/vault/pull/5#issuecomment-1" in out


# The pure body: the PR-BODY headings that now live in code.

def test_titles_use_plain_mode_names():
    assert prbody.title("2026-10-12", ["dump"], "Dump & Diverge: desks") == "2026-10-12 Brainstorm: desks"
    assert prbody.title("2026-10-12", ["grill"], "Grill: consent") == "2026-10-12 Decisions: consent"


def test_reviewer_handles():
    owners = ["@lead @mini/shop-team", "@priya", "@mini/shop-team"]
    assert prbody.reviewers(owners, "lead") == ["mini/shop-team", "priya"]
    assert prbody.reviewer_words(["mini/identity-team", "priya"]) == "Priya and the identity team"


def test_state_moves_in_plain_words():
    assert prbody.state_move("fact", "decided") == "now decided"
    assert prbody.state_move("decided", "assumption") == "set back to not decided yet"
    assert prbody.state_move("open", "resolved") == "answered"


def test_what_changed_has_no_record_link_or_capture_number():
    class Vault:
        def name_of(self, ident):
            return "Stock level"
    row = type("Row", (), {"item": "CON-002", "before": "fact", "after": "decided", "capture_number": "1"})()
    assert prbody.what_changed([row], Vault()) == ["- Stock level: now decided"]


def test_a_body_is_the_sentences_and_what_changed_only():
    text = prbody.body(prbody.Facts(summary="Done.", changed=["- Stock level: now decided"]))
    assert text == "Done.\n\n**What changed**\n\n- Stock level: now decided\n"
    assert "Needs a look" not in text


def test_lead_never_hears_a_code_in_the_failure_sentence():
    assert say.leak_in(prbody.SAVED_SENTENCE) is None
