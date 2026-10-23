"""`vela voice examples / plan / save / harvest list / harvest decline` (overhaul Task 18).

The rules come from close/HARVEST.md, voice-seed (SKILL.md and WRITE.md) and house-voice; each test names the rule it
holds. Harvest runs against a real git repo with a bare origin carrying `refs/pull/<n>/head`, and a fake `gh` on PATH
that answers from files, so a `gh` failure can be made to happen on purpose.
"""
import hashlib
import json
import subprocess
import sys
import textwrap

import pytest

from conftest import run
from vela import voiceplan
import session_files

SESSION = "2026-10-14-voice-test"
RECORD = f"""---
id: {SESSION}
type: session
date: 2026-10-14
modes: [grill]
status: open
---

# 2026-10-14 Grill: voice test

## Captures

- [instruction] (@owner) "Yes, I wrote it myself." → drop: consent to store ^c01
- [instruction] (@owner) "Yes, it may be committed." → drop: consent to commit ^c02
- [instruction] (claude) "Yes." → drop: my own summary ^c03
- [instruction] (@owner) "Yes, retire that one." → drop: consent to retire ^c04
"""
PASSAGE = ("The calendar read waits on the CISO, and nobody has said when.\n\n"
           "Second paragraph: trailing spaces stay   \n\ttabs stay, and so does the missing final newline")


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], capture_output=True,
                          text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def example(root, place, voice_type, number, source="public-seed", state="active", added="2026-10-03",
            author='"Chris Davis"', body="A passage.\n"):
    folder = root / ("voice/examples" if place == "committed" else "voice/local") / voice_type
    folder.mkdir(parents=True, exist_ok=True)
    ident = f"VX-{voice_type}-{number:03d}"
    path = folder / f"{ident}.md"
    path.write_text(f"---\nid: {ident}\nvoice_type: {voice_type}\nsource: {source}\nauthor: {author}\n"
                    f"state: {state}\nadded: {added}\n---\n\n{body}", encoding="utf-8")
    return path


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    (root / "sessions").mkdir(parents=True)
    session_files.write_record(root, SESSION, RECORD)
    git(root, "init", "-q", "-b", "main")
    return root


def voice(root, *args):
    return run("voice", *args, "--vault", str(root))


def state_of(path):
    return next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("state:"))


# --- voice examples: house-voice's fixed reading order ---------------------------------------------------------------

def test_examples_order_is_fixed(vault):
    """Local owner and owner-edit examples first, then voice/examples/, then any other local example, each in file-name
    order, retired ones skipped: two drafts of one page start from the same context."""
    example(vault, "committed", "decision", 2)
    example(vault, "committed", "decision", 1)
    example(vault, "committed", "decision", 3, state="retired")
    example(vault, "local", "decision", 5, source="public-seed")
    example(vault, "local", "decision", 7, source="owner-edit", author='"@owner"')
    example(vault, "local", "decision", 4, source="owner", author='"@owner"')
    code, out = voice(vault, "examples", "--type", "decision")
    assert code == 0, out
    assert out.split() == ["voice/local/decision/VX-decision-004.md", "voice/local/decision/VX-decision-007.md",
                           "voice/examples/decision/VX-decision-001.md", "voice/examples/decision/VX-decision-002.md",
                           "voice/local/decision/VX-decision-005.md"]


def test_examples_resolve_a_page_by_id_then_type(vault):
    example(vault, "committed", "diagnosis", 1)
    example(vault, "committed", "diagnosis", 2)
    example(vault, "committed", "how-it-works", 1)
    (vault / "01-goals.md").write_text("---\nid: goals\ntype: initiative-section\ntitle: Goals\n---\n", encoding="utf-8")
    (vault / "flow.md").write_text("---\nid: FLO-001\ntype: flow\ntitle: A flow\n---\n", encoding="utf-8")
    code, out = voice(vault, "examples", "--page", "01-goals.md", "--json")
    data = json.loads(out)
    assert (code, data["voice_type"]) == (0, "diagnosis")
    code, out = voice(vault, "examples", "--page", "flow.md", "--json")
    data = json.loads(out)
    assert (data["voice_type"], data["examples"]) == ("how-it-works", ["voice/examples/how-it-works/VX-how-it-works-001.md"])
    assert any("fewer than 2" in line for line in data["lines"])


def test_examples_structured_page_has_no_voice(vault):
    (vault / "glossary.md").write_text("---\nid: glossary\ntype: glossary\ntitle: Glossary\n---\n", encoding="utf-8")
    code, out = voice(vault, "examples", "--page", "glossary.md", "--json")
    assert (code, json.loads(out)["examples"]) == (0, [])


def test_examples_unknown_page_type_is_refused(vault):
    (vault / "odd.md").write_text("---\nid: odd\ntype: memo\ntitle: Odd\n---\n", encoding="utf-8")
    code, out = voice(vault, "examples", "--page", "odd.md")
    assert code == 1 and "memo" in out


# --- voice plan: the retirement rules ----------------------------------------------------------------------------------

def test_local_never_retires_committed_seed(vault):
    """A local example never retires a committed seed, or every teammate's house voice drops below 2 of the type."""
    for n in (1, 2, 3):
        example(vault, "committed", "diagnosis", n)
    example(vault, "local", "diagnosis", 4, source="owner", author='"@owner"')
    plan = voiceplan.plan(voiceplan_examples(vault), "diagnosis", "local", source="owner")
    assert plan.seed_retires == [] and plan.cap_retires == [] and not plan.blocked
    code, out = voice(vault, "plan", "--type", "diagnosis", "--place", "local", "--json")
    assert code == 0, out
    assert json.loads(out)["retires"] == []


def test_committed_owner_examples_retire_their_own_folders_seed(vault):
    for n in (1, 2, 3):
        example(vault, "committed", "diagnosis", n)
    example(vault, "committed", "diagnosis", 4, source="owner", author='"@owner"')
    plan = voiceplan.plan(voiceplan_examples(vault), "diagnosis", "committed", source="owner")
    assert [e.id for e in plan.seed_retires] == ["VX-diagnosis-001", "VX-diagnosis-002", "VX-diagnosis-003"]
    assert plan.cap_retires == []


def test_cap_of_five_across_folders(vault):
    """At most 5 active, both folders counted together; the surplus retires public-seed first, then owner-edit, then
    owner, oldest `added` first and then file name. The owner must say yes to a cap retirement: exit 3."""
    example(vault, "committed", "decision", 1, source="owner", author='"@owner"', added="2026-01-01")
    example(vault, "committed", "decision", 2, source="owner-edit", author='"@owner"', added="2026-03-01")
    example(vault, "committed", "decision", 3, source="owner-edit", author='"@owner"', added="2026-02-01")
    example(vault, "local", "decision", 4, source="owner", author='"@owner"', added="2025-01-01")
    example(vault, "local", "decision", 5, source="owner", author='"@owner"', added="2025-02-01")
    code, out = voice(vault, "plan", "--type", "decision", "--place", "committed", "--json")
    assert code == 3, out
    data = json.loads(out)
    assert [r["id"] for r in data["retires"]] == ["VX-decision-003"] and data["needs_lead"]
    code, out = voice(vault, "plan", "--type", "decision", "--place", "local", "--json")
    assert code == 3, out
    assert [r["id"] for r in json.loads(out)["retires"]] == ["VX-decision-004"]  # only local may retire


def test_cap_blocks_a_local_save_when_no_local_example_may_retire(vault):
    for n in range(1, 6):
        example(vault, "committed", "decision", n, source="owner", author='"@owner"')
    code, out = voice(vault, "plan", "--type", "decision", "--place", "local")
    assert code == 1
    assert "The cap blocks a local save: decision holds 5 active examples and none in voice/local/ may retire." in out


def voiceplan_examples(root):
    from vela.edge import voicegit
    return voicegit.examples(root)


# --- voice save: verbatim, with its two yeses ---------------------------------------------------------------------------

def passage_file(tmp_path, text=PASSAGE, name="passage.txt"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return path


def test_save_is_byte_for_byte(vault, tmp_path):
    source = passage_file(tmp_path)
    code, out = voice(vault, "save", "--from", str(source), "--type", "diagnosis", "--place", "local",
                      "--consent", "^c01", "--author", "owner", "--where", "design review, the 'payments' move",
                      "--today", "2026-10-14", "--json")
    assert code == 0, out
    stored = vault / "voice/local/diagnosis/VX-diagnosis-001.md"
    raw = stored.read_bytes()
    head = ("---\nid: VX-diagnosis-001\nvoice_type: diagnosis\nsource: owner\nauthor: \"@owner\"\n"
            "from: 'design review, the ''payments'' move'\nstate: active\nadded: 2026-10-14\n---\n\n")
    assert raw == head.encode("utf-8") + source.read_bytes()
    assert voiceplan.stored_body(raw.decode("utf-8")) == PASSAGE
    data = json.loads(out)
    assert data["wrote"] == ["voice/local/diagnosis/VX-diagnosis-001.md"]
    assert any("no final newline" in line for line in data["lines"])


def test_save_numbers_past_retired_files_in_both_folders(vault, tmp_path):
    example(vault, "committed", "diagnosis", 4, state="retired")
    example(vault, "local", "diagnosis", 2, source="owner", author='"@owner"')
    code, out = voice(vault, "save", "--from", str(passage_file(tmp_path)), "--type", "diagnosis", "--place", "local",
                      "--consent", "^c01", "--author", "@owner", "--where", "a memo", "--json")
    assert code == 0, out
    assert json.loads(out)["wrote"] == ["voice/local/diagnosis/VX-diagnosis-005.md"]


def test_committed_save_needs_both_yeses(vault, tmp_path):
    """Committed text is read by everyone with access to the repository: "I wrote it" and "it may be committed" are two
    separate yeses from a person, and the second is never the first one reused."""
    source = passage_file(tmp_path)
    common = ("save", "--from", str(source), "--type", "decision", "--place", "committed", "--author", "owner",
              "--where", "a memo")
    code, out = voice(vault, *common, "--consent", "^c01")
    assert code == 1 and "commit" in out
    code, out = voice(vault, *common, "--consent", "^c01", "--commit-consent", "^c01")
    assert code == 1
    code, out = voice(vault, *common, "--consent", "^c01", "--commit-consent", "^c03")
    assert code == 1 and "was mine, not yours" in out  # ^c03 is Claude's, not the owner's
    code, out = voice(vault, *common, "--consent", "^c09", "--commit-consent", "^c02")
    assert code == 1
    assert not (vault / "voice/examples/decision").exists()
    code, out = voice(vault, *common, "--consent", "^c01", "--commit-consent", "^c02")
    assert code == 0, out
    assert (vault / "voice/examples/decision/VX-decision-001.md").is_file()


def test_save_reports_boundary_lines_and_word_count(vault, tmp_path):
    text = "Short.\n---\n<!-- generated:x sha=0: do not edit -->\n"
    code, out = voice(vault, "save", "--from", str(passage_file(tmp_path, text)), "--type", "diagnosis", "--place",
                      "local", "--consent", "^c01", "--author", "owner", "--where", "x", "--json")
    assert code == 0, out
    lines = json.loads(out)["lines"]
    assert any("line 2" in line and "---" in line for line in lines)
    assert any("line 3" in line and "generated" in line for line in lines)
    assert any("under 80" in line for line in lines)


def test_save_applies_seed_retirement_and_asks_for_cap_retirement(vault, tmp_path):
    seeds = [example(vault, "committed", "how-it-works", n) for n in (1, 2, 3)]
    before = seeds[0].read_text(encoding="utf-8")
    example(vault, "committed", "how-it-works", 4, source="owner", author='"@owner"')
    example(vault, "committed", "how-it-works", 5, source="owner", author='"@owner"')
    common = ("save", "--from", str(passage_file(tmp_path)), "--type", "how-it-works", "--place", "committed",
              "--consent", "^c01", "--commit-consent", "^c02", "--author", "owner", "--where", "x")
    code, out = voice(vault, *common, "--json")
    # 2 owner examples already: the three seeds retire by the folder rule, no cap retirement, no question.
    assert code == 0, out
    assert [state_of(vault / f"voice/examples/how-it-works/VX-how-it-works-00{n}.md") for n in (1, 2, 3)] \
        == ["state: retired"] * 3
    assert seeds[0].read_text(encoding="utf-8") == before.replace("state: active", "state: retired")


def test_save_with_cap_retirement_exits_3_until_the_owner_says_yes(vault, tmp_path):
    for n in range(1, 6):
        example(vault, "committed", "decision", n, source="owner", author='"@owner"', added=f"2026-01-0{n}")
    common = ("save", "--from", str(passage_file(tmp_path)), "--type", "decision", "--place", "committed",
              "--consent", "^c01", "--commit-consent", "^c02", "--author", "owner", "--where", "x")
    code, out = voice(vault, *common, "--json")
    assert code == 3, out
    assert not (vault / "voice/examples/decision/VX-decision-006.md").exists()
    code, out = voice(vault, *common, "--retire-consent", "^c04", "--json")
    assert code == 0, out
    assert state_of(vault / "voice/examples/decision/VX-decision-001.md") == "state: retired"
    assert (vault / "voice/examples/decision/VX-decision-006.md").is_file()


def test_reader_copy_saves_only_locally(tmp_path):
    root = tmp_path / "reader"
    (root / ".vela").mkdir(parents=True)
    (root / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")
    (root / "sessions").mkdir()
    session_files.write_record(root, SESSION, RECORD)
    code, out = voice(root, "save", "--from", str(passage_file(tmp_path)), "--type", "decision", "--place",
                      "committed", "--consent", "^c01", "--commit-consent", "^c02", "--author", "owner", "--where", "x")
    assert code == 1 and "local" in out


# --- harvest ----------------------------------------------------------------------------------------------------------

FAKE_GH = '''#!{python}
import json, os, pathlib, sys
here = pathlib.Path(os.environ["FAKE_GH_DIR"])
args = sys.argv[1:]
key = {{("api", "user"): "user", ("pr", "list"): "list"}}.get(tuple(args[:2]))
if key is None and args[:2] == ["pr", "view"]:
    key = "view-" + args[2]
fail = here / (key + ".fail")
if fail.exists():
    sys.stderr.write(fail.read_text())
    sys.exit(1)
sys.stdout.write((here / key).read_text())
'''

PAGE = "05-solution-strategy.md"
DRAFT = """---
id: solution-strategy
type: initiative-section
title: Solution strategy
---

# Solution strategy

Heron reads the calendar first. The folder read waits.

The call tools come last, after Legal.
"""


@pytest.fixture
def harvest(tmp_path, monkeypatch):
    """A vault whose session PR 7 holds a draft commit, the owner's edit, and an edit made by Claude."""
    root, origin, ghdir = tmp_path / "vault", tmp_path / "origin.git", tmp_path / "gh"
    root.mkdir()
    ghdir.mkdir()
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Owner")
    git(root, "config", "user.email", "owner@example.invalid")
    git(root, "remote", "add", "origin", str(origin))
    example(root, "committed", "decision", 1, source="owner", author='"@owner"')
    (root / "sessions").mkdir()
    session_files.write_record(root, SESSION, RECORD)
    (root / ".gitignore").write_text(".vela/\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    git(root, "push", "-q", "origin", "main")
    git(root, "switch", "-q", "-c", "session/2026-10-14-x")
    (root / PAGE).write_text(DRAFT, encoding="utf-8")
    git(root, "add", PAGE)
    git(root, "commit", "-q", "-m", "draft: prose for 2026-10-14-x")
    draft = git(root, "rev-parse", "HEAD")
    commits = [draft]
    edited = DRAFT.replace("Heron reads the calendar first.", "Heron reads the calendar before anything else.")
    (root / PAGE).write_text(edited, encoding="utf-8")
    git(root, "commit", "-q", "-am", "Tighten the opening")
    commits.append(git(root, "rev-parse", "HEAD"))
    claude = edited.replace("after Legal.", "once Legal has signed off.")
    (root / PAGE).write_text(claude, encoding="utf-8")
    git(root, "commit", "-q", "-am", "Reword the call tools line\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>")
    commits.append(git(root, "rev-parse", "HEAD"))
    git(root, "push", "-q", "origin", "HEAD:refs/pull/7/head")
    git(root, "switch", "-q", "main")
    bodies = {draft: "", commits[1]: "", commits[2]: "Co-Authored-By: Claude Opus <noreply@anthropic.com>"}
    heads = {draft: "draft: prose for 2026-10-14-x", commits[1]: "Tighten the opening",
             commits[2]: "Reword the call tools line"}
    (ghdir / "user").write_text("owner\n")
    (ghdir / "list").write_text(json.dumps([{"number": 7, "headRefName": "session/2026-10-14-x"}]))
    (ghdir / "view-7").write_text(json.dumps({"commits": [
        {"oid": c, "messageHeadline": heads[c], "messageBody": bodies[c]} for c in commits]}))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "gh").write_text(FAKE_GH.format(python=sys.executable))
    (bindir / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:{__import__('os').environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_DIR", str(ghdir))
    return root, ghdir, draft


def harvest_list(root, *flags):
    code, out = voice(root, "harvest", "list", "--json", *flags)
    return code, json.loads(out)


def test_harvest_drops_claude_trailer_commits(harvest):
    root, _, draft = harvest
    code, data = harvest_list(root)
    assert code == 0, data
    assert [(c["pr"], c["page"], c["baseline"]) for c in data["candidates"]] == [(7, PAGE, draft)]
    candidate = data["candidates"][0]
    assert candidate["draft"] == "Heron reads the calendar first. The folder read waits.\n"
    assert candidate["merged"] == "Heron reads the calendar before anything else. The folder read waits.\n"
    assert candidate["hash"] == hashlib.sha1(candidate["merged"].encode()).hexdigest()[:12]
    assert candidate["voice_type"] == "decision"  # the page id solution-strategy is in the table
    assert (root / candidate["file"]).read_text() == candidate["merged"]


def test_gh_failure_is_never_no_edits_found(harvest):
    root, ghdir, _ = harvest
    (ghdir / "list.fail").write_text("HTTP 502: Bad Gateway")
    code, out = voice(root, "harvest", "list")
    assert code == 2
    assert "502" in out and "no edits found" not in out.lower()
    (ghdir / "list.fail").unlink()
    (ghdir / "view-7.fail").write_text("could not resolve PR")
    code, out = voice(root, "harvest", "list")
    assert code == 2 and "PR 7" in out and "no edits found" not in out.lower()


def test_gh_user_failure_is_exit_2(harvest):
    root, ghdir, _ = harvest
    (ghdir / "user.fail").write_text("not logged in")
    code, out = voice(root, "harvest", "list")
    assert code == 2 and "not logged in" in out


def test_harvest_is_owner_only(harvest):
    root, ghdir, _ = harvest
    (ghdir / "user").write_text("someone-else\n")
    code, out = voice(root, "harvest", "list")
    assert code == 1 and "Harvest is owner-only." in out


def test_declined_line_written_and_skipped_next_time(harvest):
    root, _, _ = harvest
    _, data = harvest_list(root)
    candidate = data["candidates"][0]
    code, out = voice(root, "harvest", "decline", "7", candidate["page"], candidate["hash"])
    assert code == 0, out
    record = session_files.record_text(root, SESSION)
    line = f"Harvest declined: PR 7 {PAGE} {candidate['hash']}"
    assert f"## Captures\n{line}\n" in record
    code, out = voice(root, "harvest", "decline", "7", candidate["page"], candidate["hash"])
    assert code == 0 and record == session_files.record_text(root, SESSION)
    code, data = harvest_list(root)
    assert (code, data["candidates"]) == (0, [])
    assert any("no edits found" in line.lower() for line in data["lines"])


def test_saved_paragraph_is_not_offered_again(harvest):
    root, _, draft = harvest
    _, data = harvest_list(root)
    candidate = data["candidates"][0]
    code, out = voice(root, "save", "--from", str(root / candidate["file"]), "--type", "how-it-works",
                      "--place", "local", "--consent", "^c01", "--author", "owner", "--page", PAGE,
                      "--harvested-from", draft, "--json")
    assert code == 0, out
    assert "source: owner-edit" in (root / json.loads(out)["wrote"][0]).read_text()
    _, data = harvest_list(root)
    assert data["candidates"] == []


def test_ten_prs_says_older_not_checked(harvest):
    root, ghdir, _ = harvest
    prs = [{"number": 7, "headRefName": "session/2026-10-14-x"}]
    prs += [{"number": n, "headRefName": f"session/s{n}"} for n in range(20, 29)]
    (ghdir / "list").write_text(json.dumps(prs))
    for n in range(20, 29):
        (ghdir / f"view-{n}").write_text(json.dumps({"commits": []}))
    code, out = voice(root, "harvest", "list")
    assert "10 merged PRs came back, so older PRs were not checked." in out


def test_no_owner_examples_means_nothing_to_harvest(harvest):
    root, _, _ = harvest
    for path in (root / "voice").rglob("*.md"):
        path.unlink()
    code, out = voice(root, "harvest", "list")
    assert code == 0 and "No owner examples yet" in out


# --- pure helpers -----------------------------------------------------------------------------------------------------

def test_tool_commits_are_recognized():
    assert voiceplan.is_tool_commit("draft: voice rewrite for x", "")
    assert voiceplan.is_tool_commit("Checkpoint 2026-10-14-x", "")
    assert voiceplan.is_tool_commit("Close session x", "")
    assert voiceplan.is_tool_commit("Fix a typo", "Body\n\nClaude-Session: https://claude.ai/code/x")
    assert voiceplan.is_tool_commit("Fix a typo", "co-authored-by: Claude <noreply@anthropic.com>")
    assert not voiceplan.is_tool_commit("Fix a typo", "Co-Authored-By: Sam <sam@example.com>")


def test_retire_changes_only_the_state_line():
    text = textwrap.dedent("""\
        ---
        id: VX-decision-001
        state: active
        added: 2026-10-03
        ---

        state: active is in the body too.
        """)
    assert voiceplan.retired(text) == text.replace("state: active\nadded", "state: retired\nadded", 1)


def test_for_lead_lines_hold_no_code_or_id(harvest, tmp_path):
    """Every step's `--for-lead` output goes through say's checker, which fails loudly (exit 2) on a leak."""
    root, ghdir, draft = harvest
    code, out = voice(root, "harvest", "list", "--for-lead")
    assert code == 0 and "solution-strategy" in out, out
    _, data = harvest_list(root)
    candidate = data["candidates"][0]
    code, out = voice(root, "save", "--from", str(root / candidate["file"]), "--type", "decision", "--place",
                      "committed", "--consent", "^c01", "--commit-consent", "^c03", "--author", "owner", "--page", PAGE,
                      "--harvested-from", draft, "--for-lead")
    assert code == 1 and "^c" not in out, out
    code, out = voice(root, "examples", "--type", "decision", "--for-lead")
    assert code == 0, out
    code, out = voice(root, "harvest", "decline", "7", PAGE, candidate["hash"], "--for-lead")
    assert code == 0 and "won't come up again" in out
    (ghdir / "list.fail").write_text("HTTP 502")
    code, out = voice(root, "harvest", "list", "--for-lead")
    assert code == 2 and out.strip() == "I couldn't reach GitHub, so I haven't looked for your edits."
