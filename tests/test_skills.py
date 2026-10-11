"""The plugin's skills: frontmatter, size, the files they point at, the plugin validator, and the
rules each skill exists to hold."""
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY = {"ask", "find"}  # every other skill writes to the vault
# Files a reference may name that live outside references/: vault files, and files of the user's grill skills.
OTHER_FILES = {"CONVENTIONS.md", "CLAUDE.md", "SKILL.md", "CONTEXT.md", "NEG-AUDIT.md", "PREREQ-CHECK.md", "GRILL-LOOP.md",
               "REQUIREMENTS-FORMAT.md", "TECH-DESIGN-FORMAT.md"}
INSTALLED = re.compile(r"(?:\.claude/skills/planner|\$\{CLAUDE_PLUGIN_ROOT\})/([A-Za-z0-9_./-]+)")
SIBLING = re.compile(r"`([A-Z][A-Z0-9-]*\.md)`")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    return yaml.safe_load(text.split("---\n", 2)[1])


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def ids(paths):
    return [p.name for p in paths]


@pytest.mark.parametrize("skill", SKILLS, ids=ids(SKILLS))
def test_frontmatter(skill):
    meta = frontmatter(skill / "SKILL.md")
    assert meta["name"] == skill.name
    assert isinstance(meta.get("description"), str) and len(meta["description"]) >= 40
    if skill.name in READ_ONLY:
        assert "disable-model-invocation" not in meta
        assert meta["disallowed-tools"] == "Write Edit NotebookEdit"
    else:
        assert meta.get("disable-model-invocation") is True, f"{skill.name} writes, so only the user may invoke it"


@pytest.mark.parametrize("skill", SKILLS, ids=ids(SKILLS))
def test_under_500_lines(skill):
    assert len((skill / "SKILL.md").read_text(encoding="utf-8").splitlines()) < 500


DOCS = SKILLS + [PLUGIN / "references"]


@pytest.mark.parametrize("folder", DOCS, ids=ids(DOCS))
def test_every_file_a_skill_or_reference_names_exists(folder):
    files = [folder / "SKILL.md"] if (folder / "SKILL.md").exists() else sorted(folder.glob("*.md"))
    for path in files:
        body = path.read_text(encoding="utf-8")
        for rel in INSTALLED.findall(body):
            rel = rel.rstrip(".")
            assert (PLUGIN / rel).exists(), f"{path.name} names .claude/skills/planner/{rel}, which the plugin lacks"
        if folder.name == "references":
            for name in SIBLING.findall(body):
                assert name in OTHER_FILES or (folder / name).exists(), f"{path.name} names {name}, which is not in references/"


def test_references_hold_no_skill_frontmatter():
    for path in (PLUGIN / "references").glob("*.md"):
        assert not path.read_text(encoding="utf-8").startswith("---"), f"{path.name} is a reference, not a skill"


def test_claude_plugin_validate():
    if shutil.which("claude") is None:
        pytest.skip("the claude command is not installed here")
    result = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.

def test_start_stops_on_a_dirty_clone_and_says_when_main_is_old():
    start = text("references/START.md")
    assert "If any file is changed or untracked, stop and ask" in start
    assert "Never start from an old `main` without saying so." in start
    assert "add `-2`" in start
    assert "Never close a session for the user." in start
    assert "Review comments were not checked" in start or "review comments were not checked" in start
    assert "claude, from <name>" in start


def test_dump_writes_captures_only():
    dump = text("skills/dump/SKILL.md")
    assert "Never edit a page outside `sessions/` during a dump." in dump
    assert "pre-mortem" in dump
    assert "Do not run close yourself." in dump


def test_close_marks_honestly_and_never_claims_a_pr():
    close = text("skills/close/SKILL.md")
    assert "Never propose `fact`." in close
    assert "A `(claude)` line is parked unless the user picks it." in close
    assert "It is never parked." in close
    assert "Promoted on a nod" in close
    assert "May still say the old value" in close
    assert "passed as `org/team`" in close and "Drop the user's own handle." in close
    assert "Never say a PR exists unless `gh` printed its URL." in close
    assert "Do not open a PR for a branch that is not pushed." in close


def test_open_sessions_are_found_on_their_branches_and_ids_do_not_collide():
    start, close = text("references/START.md"), text("skills/close/SKILL.md")
    assert "git branch --list 'session/*'" in start and "git branch -r --list 'origin/session/*'" in start
    assert "add `-2`, then `-3`" in start
    assert "git branch -r --list 'origin/session/*'" in close and "git switch <branch>" in close and "it is `session/<id>`" in close
    assert "If there is none yet, skip the merged-PR search" in start
    assert "pulls/<number>/reviews" in start
    assert "<Mode name>" in start and "Dump & Diverge" in start


def test_close_parks_every_claude_origin_and_never_decides_its_unknowns():
    close = text("skills/close/SKILL.md")
    assert "including `(claude, from <name>)`" in close
    assert "kept as an UNK with an owner and an ask-by date, or dropped with a reason" in close
    assert "Claude never decides it alone" in close and "This rule wins over the park default" in close
    assert "A person's `wild` line is parked, never dropped." in close
    assert "every item kept or promoted from a capture whose origin starts with `claude`" in close
    assert "next free ID of their kind" in close


def test_close_pr_body_reviewers_and_staging():
    close = text("skills/close/SKILL.md")
    assert "**Prose drafted:**" in close and "**Decided wording not yet read back:**" in close
    assert "gh api user -q .login" in close and "Strip the leading `@`" in close
    assert "If nobody remains, leave out `--reviewer`." in close
    assert "Never use `git add -A`." in close


# grill (V1-10)

def test_grill_holds_the_gate_and_writes_each_decision_at_once():
    grill = text("skills/grill/SKILL.md")
    for gate in ("GATE-1", "GATE-2", "GATE-3", "GATE-4", "GATE-5"):
        assert f"| {gate} |" in grill
    assert "If no item passes and the user overrides none, do not start the grill: make no change to any page" in grill
    assert "- **Decision:** [[<session id>]]" in grill
    assert "- **Dissent:** <name>, <date>: <reason>" in grill
    assert "claude, from <name>" in grill
    assert "Keep your recommendation when the user pushes back without a reason." in grill
    assert "Never answer your own question." in grill
    assert "Never batch decisions to the end." in grill


def test_grill_defines_acceptance_agenda_and_the_mark_exception():
    grill, start, close = (text("skills/grill/SKILL.md"), text("references/START.md"),
                           text("skills/close/SKILL.md"))
    assert 'Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance.' in grill
    assert "read the final wording back and get a yes" in grill
    assert "says yes in person" in grill and "explicit yes" in grill
    assert "record where the provider stands as well as each consumer" in grill
    assert "(decided)" in grill and "the one exception to leaving marks off until close" in grill
    assert "exception is a Grill" in start and "(decided)" in start and "## Agenda" in start
    assert "keeps its mark" in close and "Promoted on a nod" in close
    assert "## Agenda" in grill and "GATE-3 confirmed yes|no" in grill
    assert "blocks every item on that page" in grill
    assert "re-run GATE-4 for every other agenda item" in grill and "E316" in grill
    assert "Stage the session record and the changed pages, by exact path." in grill
    assert "already `decided`, say so" in grill and "change of mind in the Changes table" in grill


# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.

def test_discover_cites_sources_and_never_promotes_a_plan_to_fact():
    discover = text("skills/discover/SKILL.md")
    assert "A line from an `intends` source is an `assumption`" in discover
    assert "Never copy document text into the vault." in discover
    assert "Claude's general knowledge is never a source." in discover
    assert "`Kind: repo`" in discover and "<url>@<sha>" in discover
    assert "nothing under `.inbox/` is staged" in discover


def test_shape_offers_two_or_three_and_never_decides():
    shape = text("skills/shape/SKILL.md")
    assert "never one and never more than three" in shape
    assert "that's decided, grill to confirm" in shape
    assert "Shape never decides" in shape


def test_there_is_no_probe_skill():
    assert not (PLUGIN / "skills" / "probe").exists()
    assert "There is no separate Probe skill." in text("references/MODES.md")


def test_discover_fix_round_guesses_never_become_facts():
    d = text("skills/discover/SKILL.md")
    assert "Propose a `Kind` for each source" in d and "confirmed `Kind`" in d
    assert 'A line about the future ("will", "planned", "by Q4", "ready in") is an `assumption`, whatever its source\'s `Kind`.' in d
    assert "Label every line with its source `SRC-nn` and that source's `Kind`." in d
    assert "explicit yes for that line" in d and "ask again" in d
    assert "`first-hand` is not a registered `Kind`" in d and "`Kind: exists`" in d
    assert "an owner handle and an ask-by date" in d
    assert "capture line and a `## Changes` row" in d


def test_shape_and_close_fix_round():
    shape, close = text("skills/shape/SKILL.md"), text("skills/close/SKILL.md")
    assert "`claude, from <name>`" in shape
    assert "After close, run `/planner:grill <ID>`" in shape
    assert "never an `inkling`" in close and "`**Options considered:**` bullet" in close
    assert "grill to confirm" in close and "GATE-2" in close
    assert "Discover already wrote its facts" in close


def test_discover_marks_its_fact_captures_and_close_leaves_them():
    d, start, close = (text("skills/discover/SKILL.md"), text("references/START.md"),
                       text("skills/close/SKILL.md"))
    assert "→ keep: [[<page>#<heading>|<ID>]] (fact)" in d
    assert "(fact)" in start and "second is a Discover" in start
    assert "a Discover already marked `(fact)`, or a Boundary, Requirements or Allocate session already marked `(assumption)`, keeps its mark" in close


# /ask (V1-15)

ASK_INJECT = re.compile(r"^!`(.+)`$", re.M)


def run_injected(cwd, env):
    out = []
    for command in ASK_INJECT.findall(text("skills/ask/SKILL.md")):
        result = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (command, result.stderr)
        out.append(result.stdout)
    return out


def test_ask_answers_from_opened_sections_and_marks_what_is_missing():
    ask = text("skills/ask/SKILL.md")
    assert "Never search `voice/`." in ask
    assert "Cite nothing you did not open in this answer." in ask
    assert "`Not recorded:`" in ask and "`Not decided:`" in ask
    assert "Never create, edit or delete a file." in ask
    assert "Sources:" in ask


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_ask_header_works_with_no_origin_and_no_claude_md(tmp_path):
    import os
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    git = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid"]
    subprocess.run(git + ["init", "-q", "-b", "main"], cwd=tmp_path, check=True, timeout=60)
    (tmp_path / "x.md").write_text("x\n", encoding="utf-8")
    subprocess.run(git + ["add", "x.md"], cwd=tmp_path, check=True, timeout=60)
    subprocess.run(git + ["commit", "-q", "-m", "x"], cwd=tmp_path, check=True, timeout=60)
    rules, fresh = run_injected(tmp_path, env)
    assert rules.startswith("NO CLAUDE.md")
    assert re.match(r"HEAD is [0-9a-f]+, committed \d{4}-\d{2}-\d{2}\.\n", fresh)
    assert "Behind origin/main by an unknown number of commits, as of the last fetch on no recorded date." in fresh
    (tmp_path / "CLAUDE.md").write_text((REPO / "template" / "CLAUDE.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert run_injected(tmp_path, env)[0].startswith("TEMPLATE: a person must rewrite this file.")


def test_ask_fix_round_bash_read_only_and_every_claim_sourced():
    ask = text("skills/ask/SKILL.md")
    assert "Never redirect output (`>`, `>>`)." in ask
    for banned in ("`tee`", "`sed -i`", "`git commit`", "`git checkout`", "`git log --output`", "`planner render`"):
        assert banned in ask
    assert "writes a file or changes git state" in ask
    assert "Every claim is followed by its ID or labelled `Not from the vault:`. There is no third choice." in ask
    assert "Assert nothing you did not open and read. A Grep snippet alone does not count." in ask
    assert "Never Read a file under `voice/` or `.inbox/`. Read `sessions/` only if the user asks." in ask


# house voice (V1-09): close now drafts prose through it, and only through it.

def test_close_drafts_prose_through_house_voice():
    close = text("skills/close/SKILL.md")
    assert "Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it" in close
    assert "draft: prose for <id>" in close
    assert "Prose to draft" not in close


def test_house_voice_rules():
    voice = text("skills/house-voice/SKILL.md")
    assert "in file-name order" in voice
    assert "Never read `voice/corpus/`." in voice
    assert "> Replaces the paragraph above after <session id>; delete one." in voice
    assert "more than about 20 prose paragraphs" in voice
    assert "acceptance criteria;" in voice and "`**Decision:**` and `**Dissent:**` lines;" in voice


# requirements-grill vault mode (V1-12): the vault rules live in the planner, not in the user's skill.

def test_requirements_in_vault_caps_certainty_and_moves_the_output():
    ref = text("references/REQUIREMENTS-IN-VAULT.md")
    assert "It writes at most `assumption`." in ref
    assert "It never writes `fact`." in ref
    assert "there is no `docs/requirements/<slug>.md`" in ref
    assert "### CAP-NNN.FRn <short name>" in ref
    assert "Offer `/planner:grill CAP-NNN.FRn`." in ref
    assert "E316" in ref
    assert "/planner:close" in ref


# epics (V1-17): the check finds the frontier, only the lead's confirmation decides, the gate closes.

def test_epics_skill_reads_the_gaps_and_runs_the_gate():
    epics = text("skills/epics/SKILL.md")
    assert "`traceability` block" in epics
    assert "2 or 3 ways to cut" in epics and "exactly one owning team" in epics
    assert "4 to 7 numbered criteria" in epics
    assert "`[testing]`" in epics
    assert "offer `/planner:requirements` on that `CAP-nnn`, then `/planner:allocate`" in epics and "Never write the requirement into the epic." in epics
    assert "Set an epic to `decided` only when the solution lead confirms" in epics
    assert "an explicit yes to each criterion on its own" in epics and "while any criterion lacks its own explicit yes" in epics
    assert "It does not mean they are decided." in epics and "Report those separately" in epics
    assert "list each epic still at `draft`" in epics
    assert "It cites at least one contract (`CON-`) or flow (`FLO-`) ID." in epics and "Redis or Kafka" in epics
    assert "`modes: [epics, shape, grill]` and the title `Epics: <team>`" in epics
    assert "check --gate epics" in epics
    assert "Never say an app's epics are complete while one remains." in epics


def test_modes_and_close_know_epics():
    assert "| Epics (`epics`)" in text("references/MODES.md") and "| `epics` | `draft` epic pages" in text("references/MODES.md")
    assert "owes a description paragraph" in text("skills/close/SKILL.md")


def test_epics_skill_frontmatter_instruction_names_the_epics_mode():
    epics = text("skills/epics/SKILL.md")
    assert "`modes: [epics, shape, grill]`" in epics and "`modes: [shape, grill]`" not in epics
    assert "Still add the `## Changes` rows for every epic" in text("skills/close/SKILL.md")


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.

def test_tech_design_from_vault_reads_the_slice_and_links_back():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "`handed_off:`" in ref
    for source in ("`contracts-consumed` block", "`epics-for-app` block", "`delivers` list", "**Blocks:**"):
        assert source in ref
    assert "Never copy vault text into the design doc." in ref
    assert "`challenges: <vault ID>`" in ref
    assert "The design never edits the vault." in ref


def test_boundary_turns_a_decided_direction_into_apps_and_decides_nothing():
    b, modes, close = text("skills/boundary/SKILL.md"), text("references/MODES.md"), text("skills/close/SKILL.md")
    assert "Offer 2 or 3 ways to cut the direction into apps, never one and never more than three" in b
    assert "Write nothing until the user has given an explicit yes to that line" in b
    assert "every page it writes is an `assumption` until a Grill" in b and "Never `addressed`" in b
    assert "→ keep: [[<page>#<heading>|<ID>]] (assumption)" in b
    assert 'the checkpoint "after the pages are written"' in b and "questions --subject <ID>" in b
    assert "/planner:grill <APP-id>" in b
    assert "| Boundary (`boundary`) |" in modes and "| `boundary` |" in modes
    assert "Boundary already wrote its app, contract and runtime pages" in close


def test_claude_asks_the_lead_first_never_drafts_an_ask_and_ends_a_blocked_session():
    modes, start, grill = text("references/MODES.md"), text("references/START.md"), text("skills/grill/SKILL.md")
    assert "**Ask the lead first.**" in modes and "**A blocked session ends.**" in modes
    assert "Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to." in modes
    assert "Never fill a blocked session with other work." in modes
    assert "Never draft an ask for the user to send, and never offer to." in start
    assert "Never draft an ask, an email or a chase for the user to send." in grill
    for path in (PLUGIN / "skills").glob("*/SKILL.md"):
        body = path.read_text(encoding="utf-8")
        for phrase in ("draft a short ask", "an ask instead", "offer an ask", "an ask to the"):
            assert phrase not in body, (path, phrase)


def test_a_review_is_about_what_this_session_changed_and_a_group_can_wait_on_one_unknown():
    review, agent, close = text("references/REVIEW.md"), text("agents/area-reviewer.md"), text("skills/close/SKILL.md")
    assert "--changed <paths>" in review and "`Changed: <paths>`" in review
    assert "it quotes a `Changed:` page" in agent
    assert "waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4" in review
    assert "A capture `waits on UNK-nnn: <IDs>` makes each ID's row `unknown`" in close and "changed in place" in close


def test_explore_opens_a_page_only_after_a_build_that_succeeded_and_writes_nothing_but_the_page_and_pins():
    explore = text("skills/explore/SKILL.md")
    assert "If the command exits 2, show its message in full, say no page was built, and stop." in explore
    assert "Never say the page is open unless the command succeeded." in explore
    assert "Nothing is written into the plugin folder." in explore
    meta = frontmatter(PLUGIN / "skills/explore/SKILL.md")
    assert "Write" not in meta["allowed-tools"].split() and "Edit" not in meta["allowed-tools"].split()


def test_every_flag_the_explore_skill_names_is_one_the_command_accepts():
    from planner import cli
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.dest == "command").choices["explore"]
    accepted = {flag for action in sub._actions for flag in action.option_strings}
    named = set(re.findall(r"`(--[a-z]+)[ `]", text("skills/explore/SKILL.md"))) | {"-o"}
    assert named and named <= accepted, named - accepted
