"""The voice review at close: a fresh-context agent flags paragraphs, the drafter rewrites
each once, and voicecheck keeps every fact the draft carried."""
import os
import re
import shutil
import subprocess
import textwrap

import pytest
import yaml

from conftest import REPO
from planner import schema

PLUGIN = REPO / "plugin"
AGENT = PLUGIN / "agents" / "voice-reviewer.md"
CLOSE = PLUGIN / "skills" / "close" / "SKILL.md"


def close_text():
    return CLOSE.read_text(encoding="utf-8")


def test_the_agent_is_named_described_and_may_only_read():
    text = AGENT.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert meta["name"] == "voice-reviewer"
    assert isinstance(meta["description"], str) and len(meta["description"]) >= 40
    assert {t.strip() for t in meta["tools"].split(",")} == {"Read", "Grep", "Glob"}
    assert len(text.splitlines()) < 500


def test_the_agent_reads_active_examples_and_never_rewrites():
    body = AGENT.read_text(encoding="utf-8")
    assert "whose frontmatter says `state: active`, in file-name order. Skip `state: retired`." in body
    assert "Never read `voice/corpus/`." in body
    assert "not reviewed: fewer than two active <type> examples" in body
    assert "| # | Page | Verdict | What differs | Example |" in body
    assert "Never rewrite a paragraph or offer replacement text." in body
    assert "Never create, edit or delete a file." in body
    assert "Never flag a paragraph for its facts, IDs, numbers, dates or links." in body


def test_close_dispatches_a_fresh_reviewer_and_never_reviews_itself():
    close = close_text()
    assert "Dispatch the `planner:voice-reviewer` subagent with the Agent tool" in close
    assert "everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter" in close
    assert "Never review the drafts yourself in this conversation." in close
    assert '"**Voice review:** not run: <the reason>"' in close


def test_close_rewrites_once_and_keeps_the_draft_when_a_fact_moves():
    close = close_text()
    assert "Rewrite each paragraph the reviewer flags once" in close
    assert "Do not send the rewrite back for review." in close
    assert "Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`" in close
    assert "run `git restore -- <page>`" in close and "keeps its earlier draft whole" in close
    assert "Run it for no other file." in close
    assert "Never commit a rewrite voicecheck could not check." in close
    assert "**Voice review:** each paragraph the reviewer flagged" in close


def test_close_covers_the_empty_broken_and_meddling_reviewer():
    close = close_text()
    assert "you must not change any file, and you must report any file you changed" in close
    assert "If the output differs from step 1 of this part, the reviewer changed a file: stop and show the user." in close
    assert "returned anything but the table, treat the review as not run" in close
    assert "If it flagged no paragraph, skip steps 4 and 5 of this part" in close
    for kind in ("wikilink", "code span", "date", "ID", "number (with its units or currency)", "table cell",
                 "version", "frontmatter line", "negation"):
        assert kind in close


def test_the_agent_reads_both_folders_with_owner_examples_first():
    body = AGENT.read_text(encoding="utf-8")
    assert "`voice/local/<voice type>/`" in body and "`voice/examples/<voice type>/`" in body
    assert "Read local `owner` and `owner-edit` examples first" in body


def recipe_commands():
    """The fenced voicecheck block in close's text, with the planner path pointed at this repo."""
    found = re.search(r"^ *```\n( *tmp=\$\(mktemp\)\n.*?)^ *```", close_text(), re.S | re.M)
    block = textwrap.dedent(found.group(1))
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/planner" in block
    return block.replace("${CLAUDE_PLUGIN_ROOT}/scripts/planner", str(PLUGIN / "scripts" / "planner"))


def guard_command():
    found = re.search(r"^ *```\n( *git diff --quiet HEAD -- <page>.*?)^ *```", close_text(), re.S | re.M)
    return textwrap.dedent(found.group(1))


GIT_IDENTITY = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git_in(repo, *args):
    cmd = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args]
    return subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True, timeout=60).stdout


def close_voicecheck(repo, page):
    """Run close's block for one page, then close's exit-0 and exit-1 branches."""
    scratch = repo.parent / (repo.name + "-scratch")
    scratch.mkdir(exist_ok=True)
    # macOS mktemp ignores TMPDIR, so mktemp itself is pointed at the scratch folder
    script = f'mktemp() {{ command mktemp "{scratch}/t.XXXXXX"; }}\n' + recipe_commands().replace("<page>", page)
    env = {**os.environ, "TMPDIR": str(scratch)}
    code = subprocess.run(["bash", "-c", script], cwd=repo, capture_output=True, text=True, env=env, timeout=60).returncode
    assert list(scratch.iterdir()) == [], "the recipe left its temp file behind"
    if code == 0:
        git_in(repo, "add", page)
        git_in(repo, "commit", "-qm", "draft: voice rewrite for s")
    elif code in (1, 2):
        git_in(repo, "restore", "--", page)
    return code


DRAFT = "Booking holds a seat for 10 minutes while the customer pays on Tidepay's page.\n"


def draft_repo(tmp_path):
    git_in(tmp_path, "init", "-q")
    (tmp_path / "page.md").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "record.md").write_text("Changes\n", encoding="utf-8")
    git_in(tmp_path, "add", "page.md", "record.md")
    git_in(tmp_path, "commit", "-qm", "draft: prose for s")
    (tmp_path / "record.md").write_text("Changes\n| row | added by step 3 |\n", encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_rewrite_that_lost_a_number_is_restored_and_other_work_survives(tmp_path):
    draft_repo(tmp_path)
    (tmp_path / "page.md").write_text("Booking keeps the seat for ten minutes while the customer pays.\n", encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 1
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == DRAFT
    assert "added by step 3" in (tmp_path / "record.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_step_three_edit_on_a_rewritten_page_survives_the_restore(tmp_path):
    draft_repo(tmp_path)
    page = tmp_path / "page.md"
    page.write_text(DRAFT + "- capture mark from step 3\n", encoding="utf-8")
    (tmp_path / "record.md").write_text("Changes\n| staged by step 2 |\n", encoding="utf-8")
    git_in(tmp_path, "add", "record.md")
    guard = guard_command().replace("<page>", "page.md").replace("<id>", "s")
    subprocess.run(["bash", "-c", guard], cwd=tmp_path, check=True, env={**os.environ, **GIT_IDENTITY}, timeout=60)
    assert git_in(tmp_path, "log", "-1", "--format=%s").strip() == "Checkpoint s"
    assert git_in(tmp_path, "show", "--name-only", "--format=", "HEAD").split() == ["page.md"]
    assert git_in(tmp_path, "status", "--porcelain", "record.md").startswith("M")
    page.write_text("Booking keeps the seat for ten minutes while the customer pays.\n- capture mark from step 3\n", encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 1
    assert page.read_text(encoding="utf-8") == DRAFT + "- capture mark from step 3\n"


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_rewrite_voicecheck_could_not_read_is_restored(tmp_path):
    draft_repo(tmp_path)
    (tmp_path / "page.md").write_bytes(b"\xff\xfe not text\n")
    assert close_voicecheck(tmp_path, "page.md") == 2
    assert (tmp_path / "page.md").read_text(encoding="utf-8") == DRAFT
    assert "added by step 3" in (tmp_path / "record.md").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_clean_rewrite_is_committed_and_other_work_stays_uncommitted(tmp_path):
    draft_repo(tmp_path)
    rewrite = "Booking holds the seat for 10 minutes while the customer pays on Tidepay's page.\n"
    (tmp_path / "page.md").write_text(rewrite, encoding="utf-8")
    assert close_voicecheck(tmp_path, "page.md") == 0
    assert git_in(tmp_path, "log", "-1", "--format=%s").strip() == "draft: voice rewrite for s"
    assert git_in(tmp_path, "status", "--porcelain").strip() == "M record.md"


def test_the_plugin_validator_accepts_the_agents_folder():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


# Harvest: the owner's edits to merged drafts become examples, on the owner's yes only.

def test_harvest_is_owner_only():
    close = close_text()
    assert "Only the vault's owner harvests, and only their own edits." in close
    assert "The owner is the `author` of the `source: owner` examples" in close
    assert 'say "Harvest is owner-only."' in close
    assert "Did you write this change?" in close
    assert "The owner's answer is the check that the edit is theirs." in close


def test_harvest_finds_drafts_through_the_merged_prs():
    close = close_text()
    assert 'gh pr list --state merged --search "head:session/"' in close
    assert "git fetch origin pull/<number>/head" in close
    assert "--author @me" in close and "--limit 10" in close
    assert "gh pr view <number> --json commits" in close
    assert 'say "gh could not list merged PRs, so nothing was harvested."' in close


def test_harvest_saves_word_for_word_on_an_explicit_yes():
    close = close_text()
    assert "Save it only on an explicit yes." in close
    assert "Save the merged paragraph word for word" in close
    assert "source: owner-edit" in close and "harvested_from: '<full hash of the baseline draft commit>'" in close


def test_harvest_keeps_five_active_and_retires_the_seed_first():
    close = close_text()
    assert f"A type keeps at most {schema.VOICE_ACTIVE_MAX} active examples." in close
    assert "the oldest `public-seed` example first, then the oldest `owner-edit`, then the oldest `owner`" in close
    assert "never delete an example" in close
    assert "every example harvested or retired" in close and "**Voice examples:** each example harvested or retired." in close


# The two folders and the gh failure rule, added after the brief was written.

def harvest_text():
    return close_text().split("### Harvest the owner's edits", 1)[1].split("## 5.", 1)[0]


def test_harvest_asks_committed_or_local_and_recommends_local_for_employer_text():
    harvest = harvest_text()
    assert "`voice/examples/<type>/`" in harvest and "`voice/local/<type>/`" in harvest
    assert "If the owner's employer owns the text, or the owner is not sure, recommend local only." in harvest
    assert "May this text be committed to the vault?" in harvest
    assert "no step below stages it" in harvest
    assert "Never stage anything in `voice/local/`." in close_text()


def test_harvest_reads_both_folders_and_retires_seeds_only_within_a_folder():
    harvest = harvest_text()
    assert "`voice/examples/` and `voice/local/`" in harvest
    assert "in either folder" in harvest
    assert "A local example never retires a committed seed" in harvest
    assert "in a local-only save only local examples may retire" in harvest


def test_harvest_writes_the_paragraph_with_a_quoted_heredoc_and_a_cmp_check():
    harvest = harvest_text()
    assert "sed -n '<first>,<last>p'" in harvest
    assert "cat .planner/harvest/<pr>-<n>.txt >> <file>" in harvest
    assert "| cmp - .planner/harvest/<pr>-<n>.txt" in harvest
    assert "do not repair the file" in harvest


def test_every_gh_step_in_harvest_says_it_failed_and_never_reads_failure_as_no_edits():
    harvest = harvest_text()
    assert 'Never read a failure as "no edits found".' in harvest
    assert 'say "gh could not read your handle, so nothing was harvested."' in harvest
    assert 'say "gh could not list merged PRs, so nothing was harvested."' in harvest
    assert 'say "gh could not read the commits of PR <number>, so its edits were not checked."' in harvest
    assert 'say "git could not fetch PR <number>, so it was not checked."' in harvest
    assert 'Say "no edits found" only when every merged PR was checked.' in harvest
    for call in ("`gh api user", "`gh pr list", "`gh pr view", "`git fetch origin pull"):
        line = next(l for l in harvest.splitlines() if call in l)
        assert "fails" in line or "could not" in line, call


# Fix round 1: order, jump targets, the PR's own commits, the retire rule, the cap, quoting, the limit.

def test_the_rewrite_commit_sentence_ends_voice_review_before_harvest():
    close = close_text()
    sentence = "Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`"
    assert close.count(sentence) == 1
    assert close.index("### Voice review") < close.index(sentence) < close.index("### Harvest the owner's edits")
    assert close.index("### Harvest the owner's edits") < close.index("## 5. Read back decided wording")


def test_no_jump_says_a_bare_step_5_and_a_skipped_review_still_runs_harvest():
    close = close_text()
    assert "go on to step 5" not in close
    review = close.split("### Voice review", 1)[1].split("### Harvest the owner's edits", 1)[0]
    assert review.count('go on to the part "Harvest the owner\'s edits"') >= 3
    harvest = harvest_text()
    exits = re.findall(r"go on to ([^.]*)\.", harvest)
    assert exits and all(e == "section 5, Read back decided wording" for e in exits)
    assert "Harvest does not depend on the voice review: run it even when the review did not run." in harvest


def test_harvest_builds_on_the_prs_own_commits_and_reads_the_merged_text_from_its_head():
    harvest = harvest_text()
    assert harvest.count("origin/main") == 1 and "never from `origin/main`" in harvest
    view = harvest.index("gh pr view <number> --json commits")
    fetch = harvest.index("git fetch origin pull/<number>/head")
    merged = harvest.index("git show FETCH_HEAD:<page>")
    assert view < merged and fetch < merged
    assert "both `draft: prose for` and `draft: voice rewrite for`" in harvest
    assert "the baseline is the last draft commit in the PR's list that touched it" in harvest
    assert "Skip the PR if there are none." in harvest
    assert "`Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer" in harvest
    assert "the owner did not edit the page, so skip it" in harvest


def test_the_owner_is_asked_who_wrote_the_change_before_being_asked_to_save():
    harvest = harvest_text()
    assert harvest.index("Did you write this change?") < harvest.index("Save the merged paragraph as a <type> example?")
    assert "If it is no, or still unclear, record a decline" in harvest
    assert "and do not ask the save question" in harvest


def test_harvest_dedupes_per_paragraph_and_records_declines_in_the_session_record():
    harvest = harvest_text()
    assert "Skip a paragraph that is already saved or declined" in harvest
    assert "the same `page`, a `harvested_from` equal to the baseline's full hash, and a body equal to the merged paragraph" in harvest
    assert "`Harvest declined: PR <number> <page> <hash>`" in harvest
    assert "grep -rh '^Harvest declined: ' sessions/" in harvest


def test_two_owner_examples_in_a_folder_retire_that_folders_seed():
    harvest = harvest_text()
    assert "2 or more, retire that folder's active `public-seed` examples of the type" in harvest
    assert "as `/planner:voice-seed` does. A local save retires only local seeds." in harvest


def test_a_local_save_the_cap_blocks_stores_nothing_and_says_so():
    harvest = harvest_text()
    assert "If the cap blocks a local-only save, store nothing" in harvest
    assert "The cap blocks a local save: <type> holds 5 active examples" in harvest


def test_harvest_quotes_free_values_and_rechecks_the_frontmatter():
    harvest = harvest_text()
    assert "page: '<page path>'" in harvest
    assert "harvested_from: '<full hash of the baseline draft commit>'" in harvest
    assert harvest.index("| cmp - .planner/harvest/<pr>-<n>.txt") < harvest.index("confirm it parses as YAML")


def test_harvest_says_when_the_pr_limit_hid_older_prs():
    harvest = harvest_text()
    assert "If it returns 10 PRs, say" in harvest
    assert "--limit 20" not in harvest
    assert "older PRs were not checked." in harvest
    assert "say when the PR limit hid older PRs" in close_text()


# Fix round 2.

def run_git(repo, *args, stdin=None):
    return subprocess.run(["git", *args], cwd=repo, input=stdin, capture_output=True, text=True, check=True, timeout=60).stdout


def commit_page(repo, text, message):
    (repo / "page.md").write_text(text, encoding="utf-8")
    run_git(repo, "add", "page.md")
    run_git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "commit", "-qm", message)
    return run_git(repo, "rev-parse", "HEAD").strip()


def owner_edit_commits(repo, baseline, headlines_and_bodies):
    """The skill's step 4 filter, as written: PR commits after the baseline, minus its own."""
    shas = run_git(repo, "log", "--format=%H", f"{baseline}..HEAD", "--", "page.md").split()
    kept = []
    for sha in shas:
        headline, body = headlines_and_bodies[sha]
        if headline.startswith(("draft: ", "Checkpoint ", "Close session ")):
            continue
        if "Co-Authored-By: Claude" in body or "Claude-Session:" in body:
            continue
        kept.append(sha)
    return kept


@pytest.fixture
def pr_repo(tmp_path):
    run_git(tmp_path, "init", "-q")
    return tmp_path


def test_close_and_checkpoint_commits_are_never_offered_as_owner_edits(pr_repo):
    meta = {}
    base = commit_page(pr_repo, "Draft one.\n", "draft: prose for APP-1")
    meta[base] = ("draft: prose for APP-1", "")
    for headline in ("Checkpoint APP-1", "Close session 2026-10-03-x"):
        sha = commit_page(pr_repo, f"Draft one.\n\nAdded by {headline}.\n", headline)
        meta[sha] = (headline, "")
    assert owner_edit_commits(pr_repo, base, meta) == []
    sha = commit_page(pr_repo, "Draft one, tuned.\n\nAdded by Close session 2026-10-03-x.\n", "Tune the wording")
    meta[sha] = ("Tune the wording", "")
    assert owner_edit_commits(pr_repo, base, meta) == [sha]
    skipped = commit_page(pr_repo, "Draft one, tuned again.\n\nAdded by Close session 2026-10-03-x.\n", "Reword")
    meta[skipped] = ("Reword", "Claude-Session: https://claude.ai/code/session_x")
    assert owner_edit_commits(pr_repo, base, meta) == [sha]


def test_a_commit_is_diffed_against_its_parent_so_other_commits_do_not_bleed_in(pr_repo):
    base = commit_page(pr_repo, "Alpha.\n\nBeta.\n", "draft: prose for APP-1")
    commit_page(pr_repo, "Alpha.\n\nBeta.\n\nGamma from section 3.\n", "Close session x")
    edit = commit_page(pr_repo, "Alpha, edited.\n\nBeta.\n\nGamma from section 3.\n", "Tune")
    per_commit = run_git(pr_repo, "diff", "-U0", f"{edit}^", edit, "--", "page.md")
    assert "+Alpha, edited." in per_commit and "Gamma" not in per_commit
    baseline_to_tip = run_git(pr_repo, "diff", "-U0", base, edit, "--", "page.md")
    assert "Gamma" in baseline_to_tip


def test_the_skill_names_the_headline_and_body_fields_and_drops_authors():
    harvest = harvest_text()
    assert "`oid`, `messageHeadline` and `messageBody`" in harvest
    assert "`authors`" not in harvest
    assert "`messageHeadline` starts with `draft: `, `Checkpoint ` or `Close session `" in harvest
    assert "each one whose `messageBody` carries a `Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer" in harvest
    assert "git diff -U0 <oid>^ <oid> -- <page>" in harvest
    assert "Never compare the baseline with the tip" in harvest


@pytest.mark.skipif(shutil.which("shasum") is None, reason="shasum is not installed")
def test_the_decline_hash_command_is_reproducible(tmp_path):
    import hashlib
    paragraph = "Line one.\nLine two, with a tab\tand text.\n"
    harvest = harvest_text()
    assert "shasum < .planner/harvest/<pr>-<n>.txt | cut -c1-12" in harvest
    assert "rm -f .planner/harvest/<pr>-<n>.txt" in harvest
    (tmp_path / "p.txt").write_text(paragraph, encoding="utf-8")
    out = subprocess.run(["bash", "-c", "shasum < p.txt | cut -c1-12"], cwd=tmp_path, capture_output=True, text=True,
                         check=True, timeout=60).stdout.strip()
    assert out == hashlib.sha1(paragraph.encode()).hexdigest()[:12]


def test_a_decline_is_a_bare_line_under_captures_and_conventions_say_so():
    harvest = harvest_text()
    assert "insert one bare line `Harvest declined: PR <number> <page> <hash>` directly under `## Captures`" in harvest
    assert "It is never a bullet." in harvest
    sentence = "A harvest decline is one bare line, `Harvest declined: PR <n> <page> <hash>`, directly under `## Captures`, never a bullet."
    for path in ("template", "tests/stub-conventions", "examples/unified-booking"):
        assert sentence in (REPO / path / "CONVENTIONS.md").read_text(encoding="utf-8")


def test_the_full_hash_is_stored_and_a_no_asks_no_save_question():
    harvest = harvest_text()
    assert "harvested_from: '<full hash of the baseline draft commit>'" in harvest
    assert "short hash" not in harvest
    no = harvest.index("do not ask the save question")
    assert harvest.index("Did you write this change?") < no < harvest.index("Save the merged paragraph as a <type> example?")


def test_retirement_runs_only_after_the_cmp_check_confirms_the_save():
    harvest = harvest_text()
    assert "and change no example yet" in harvest
    assert harvest.index("| cmp - .planner/harvest/<pr>-<n>.txt") < harvest.index("Only now apply the retirements you planned in step 7")
    assert harvest.index("Plan the room before you save") < harvest.index("| cmp - .planner/harvest/<pr>-<n>.txt")


def test_step_references_name_their_section():
    close = close_text()
    assert "See section 3." in close and "See step 3." not in close
    assert "from sections 2 and 3," in close and "step 2 or 3" not in close
    assert "the work that section 7 stages" in close and "that step 7 stages" not in close
    assert "from section 6," in close


# I1: Claude Code's Bash keeps no shell variable between calls, so harvest's temp file has a
# fixed path every later call can name, and each block must run on its own in a fresh shell.

HARVEST_FILE = ".planner/harvest/<pr>-<n>.txt"


def harvest_block(first_line):
    found = re.search(r"^ *```\n( *" + re.escape(first_line) + r".*?)^ *```", harvest_text(), re.S | re.M)
    assert found, first_line
    return textwrap.dedent(found.group(1))


def fresh_shell(repo, block, **slots):
    for slot, value in slots.items():
        block = block.replace(f"<{slot}>", value)
    return subprocess.run(["bash", "-c", block], cwd=repo, capture_output=True, text=True, timeout=60)


def test_harvest_names_its_temp_file_and_keeps_no_shell_variable():
    harvest = harvest_text()
    assert "$tmp" not in harvest and "mktemp" not in harvest
    assert "mkdir -p .planner/harvest" in harvest
    assert "`<n>` is the paragraph's order" in harvest
    assert "rm -rf .planner/harvest" in harvest


def test_harvest_step_four_and_step_eight_each_run_in_a_fresh_shell(pr_repo):
    repo = pr_repo
    (repo / ".gitignore").write_text(".planner/\n", encoding="utf-8")  # as template/.gitignore does
    run_git(repo, "add", ".gitignore")
    page = "04-solution-strategy.md"
    (repo / page).write_text("# Strategy\n\nFirst line of the owner's paragraph.\nIt’s kept   word for word.\n\nTail.\n",
                             encoding="utf-8")
    run_git(repo, "add", page)
    run_git(repo, "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "merged")
    run_git(repo, "fetch", "-q", ".", "HEAD")
    slots = {"page": page, "first": "3", "last": "4", "pr": "42", "n": "1"}
    extracted = fresh_shell(repo, harvest_block("mkdir -p .planner/harvest"), **slots)
    assert extracted.returncode == 0, extracted.stderr
    stored = repo / ".planner" / "harvest" / "42-1.txt"
    assert stored.read_text(encoding="utf-8") == "First line of the owner's paragraph.\nIt’s kept   word for word.\n"
    assert re.fullmatch(r"[0-9a-f]{12}\n", extracted.stdout), extracted.stdout
    assert run_git(repo, "status", "--porcelain") == "", "the temp file must not dirty the working tree"

    example = repo / "voice" / "examples" / "decision" / "VX-decision-004.md"
    example.parent.mkdir(parents=True)
    example.write_text("---\nid: VX-decision-004\nstate: active\n---\n\n", encoding="utf-8")
    saved = fresh_shell(repo, harvest_block("cat .planner/harvest/<pr>-<n>.txt >> <file>"), file=str(example), **slots)
    assert saved.returncode == 0, saved.stderr
    assert example.read_text(encoding="utf-8").endswith("\n\nFirst line of the owner's paragraph.\nIt’s kept   word for word.\n")
    assert not stored.exists(), "step 8 removes the temp file on every exit"


def test_harvest_step_eight_fails_on_a_changed_body_and_still_removes_the_file(pr_repo):
    repo = pr_repo
    stored = repo / ".planner" / "harvest" / "7-2.txt"
    stored.parent.mkdir(parents=True)
    stored.write_text("The paragraph.\n", encoding="utf-8")
    example = repo / "VX-decision-001.md"
    example.write_text("---\nid: VX-decision-001\n---\n\nSomething already here.\n", encoding="utf-8")
    saved = fresh_shell(repo, harvest_block("cat .planner/harvest/<pr>-<n>.txt >> <file>"), file=str(example), pr="7", n="2")
    assert saved.returncode != 0
    assert not stored.exists()


def test_close_voicecheck_block_is_self_contained():
    block = recipe_commands()
    assert block.startswith("tmp=$(mktemp)\n") and 'rm -f "$tmp"; (exit $code)' in block
