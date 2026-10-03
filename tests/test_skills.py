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
READ_ONLY = {"ask"}  # every other skill writes to the vault
# Files a reference may name that live outside references/: vault files, and files of the user's grill skills.
OTHER_FILES = {"CONVENTIONS.md", "CLAUDE.md", "SKILL.md", "CONTEXT.md", "NEG-AUDIT.md", "PREREQ-CHECK.md", "GRILL-LOOP.md",
               "REQUIREMENTS-FORMAT.md", "TECH-DESIGN-FORMAT.md"}
INSTALLED = re.compile(r"\.claude/skills/planner/([A-Za-z0-9_./-]+)")
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
    assert "git branch -r --list 'origin/session/*'" in close and "git switch session/<id>" in close
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
    assert "**Prose to draft:**" in close and "**Decided wording not yet read back:**" in close
    assert "gh api user -q .login" in close and "Strip the leading `@`" in close
    assert "If nobody remains, leave out `--reviewer`." in close
    assert "Never use `git add -A`." in close


# grill (V1-10)

def test_grill_holds_the_gate_and_writes_each_decision_at_once():
    grill = text("skills/grill/SKILL.md")
    for gate in ("GATE-1", "GATE-2", "GATE-3", "GATE-4", "GATE-5"):
        assert f"| {gate} |" in grill
    assert "If no item passes, do not start the grill: make no change to any page" in grill
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
    assert "never an `inkling`" in close and "`Options considered` list" in close
    assert "grill to confirm" in close and "GATE-2" in close
    assert "Discover already wrote its facts" in close


def test_discover_marks_its_fact_captures_and_close_leaves_them():
    d, start, close = (text("skills/discover/SKILL.md"), text("references/START.md"),
                       text("skills/close/SKILL.md"))
    assert "→ keep: [[<page>#<heading>|<ID>]] (fact)" in d
    assert "(fact)" in start and "second is a Discover" in start
    assert "or a Discover already marked `(fact)`, keeps its mark" in close
