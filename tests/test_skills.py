"""The plugin's skills: frontmatter, size, the files they point at, the plugin validator, and the
rules each skill exists to hold."""
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO, run, skill_text

PLUGIN = REPO / "plugin"
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY = {"ask", "find"}  # every other skill writes to the vault
# Close is the one writing skill the model may start, on the lead's word (S24). Without the platform flag its safety is
# written into the skill: see test_close_starts_only_on_the_leads_word_and_confirms_before_it_pushes.
MODEL_MAY_START = {"close"}
# Files a reference may name that live outside references/: vault files, and files of the user's grill skills.
OTHER_FILES = {"CONVENTIONS.md", "CLAUDE.md", "SKILL.md", "CONTEXT.md", "NEG-AUDIT.md", "PREREQ-CHECK.md", "GRILL-LOOP.md",
               "REQUIREMENTS-FORMAT.md", "TECH-DESIGN-FORMAT.md", "REVIEW-CHECKPOINT.md"}
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
    elif skill.name in MODEL_MAY_START:
        assert "disable-model-invocation" not in meta
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
    assert "Never start from an old `main` without saying so." in start
    assert "add `-2`" in start
    assert "Never close a session the user has not asked to close" in start
    assert "Review comments were not checked" in start or "review comments were not checked" in start
    assert "claude, from <name>" in start


def test_dump_writes_captures_only():
    dump = text("skills/dump/SKILL.md")
    assert "Never edit a page outside `sessions/` during a dump." in dump
    assert "pre-mortem" in dump
    assert "Do not run close yourself." not in dump


def test_close_marks_honestly_and_never_claims_a_pr():
    close = skill_text("close")
    assert "Never propose `fact`." in close
    assert "A `(claude)` line is parked unless the user picks it." in close
    assert "It is never parked." in close
    assert "Promoted on a nod" in close
    assert "May still say the old value" in close
    assert "passed as `org/team`" in close and "Drop the user's own handle." in close
    assert "Never say a PR exists unless `gh` printed its URL." in close
    assert "Do not open a PR for a branch that is not pushed." in close


def test_open_sessions_are_found_on_their_branches_and_ids_do_not_collide():
    start, close = text("references/START.md"), skill_text("close")
    assert "git branch --list 'session/*'" in start and "git branch -r --list 'origin/session/*'" in start
    assert "add `-2`, then `-3`" in start
    assert "git branch -r --list 'origin/session/*'" in close and "git switch <branch>" in close and "it is `session/<id>`" in close
    assert "If there is none yet, skip the merged-PR search" in start
    assert "pulls/<number>/reviews" in start
    assert "<Mode name>" in start and "Dump & Diverge" in start


def test_close_parks_every_claude_origin_and_never_decides_its_unknowns():
    close = skill_text("close")
    assert "including `(claude, from <name>)`" in close
    assert "kept as an UNK with an owner and an ask-by date, or dropped with a reason" in close
    assert "Claude never decides it alone" in close and "This rule wins over the park default" in close
    assert "A person's `wild` line is parked, never dropped." in close
    assert "every item kept or promoted from a capture whose origin starts with `claude`" in close
    assert "planner next-id <its prefix>" in close


def test_close_pr_body_reviewers_and_staging():
    close = skill_text("close")
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
                           skill_text("close"))
    assert 'Silence, "ok", "next", "sure" with nothing else, or a change of subject do not count as acceptance.' in grill
    assert "read the final wording back and get a yes" in grill
    assert "says yes in person" in grill and "explicit yes" in grill
    assert "record where the provider stands as well as each consumer" in grill
    assert "(decided)" in grill and "the one exception to leaving marks off until close" in grill
    assert "(decided)" in start and "## Agenda" in start
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
    assert "nothing under `.inbox/` is staged" in skill_text("close")  # close owns the staging check


def test_shape_offers_two_or_three_and_never_decides():
    shape = text("skills/shape/SKILL.md")
    assert "never one and never more than three" in shape
    assert "that's decided, grill to confirm" in shape
    assert "Shape never decides" in shape


def test_there_is_no_probe_skill():
    assert not (PLUGIN / "skills" / "probe").exists()
    assert "probe" not in text("references/MODES.md").lower()


def test_discover_fix_round_guesses_never_become_facts():
    d = text("skills/discover/SKILL.md")
    assert "Propose a `Kind` for each source" in d and "confirmed `Kind`" in d
    assert 'A line about the future ("will", "planned", "by Q4", "ready in") is an `assumption`, whatever its source\'s `Kind`.' in d
    assert "Label every line with its source" in d and "that source's `Kind`" in d and "what runs today or a plan" in d
    assert "the lines the lead said yes to" in d and "ask once more in different words" in d
    assert "`first-hand` is not a registered `Kind`" in d and "`Kind: exists`" in d
    assert "an owner handle and an ask-by date" in d
    assert "capture line and a `## Changes` row" in d


def test_shape_and_close_fix_round():
    shape, close = text("skills/shape/SKILL.md"), skill_text("close")
    assert "`claude, from <name>`" in shape
    assert "After close, run `/planner:grill <ID>`" in shape
    assert "never an `inkling`" in close and "`**Options considered:**` bullet" in close
    assert "grill to confirm" in close and "GATE-2" in close
    assert "Discover already wrote its facts" in close


def test_discover_marks_its_fact_captures_and_close_leaves_them():
    d, start, close = (text("skills/discover/SKILL.md"), text("references/START.md"),
                       skill_text("close"))
    assert "→ keep: [[<page>#<heading>|<ID>]] (fact)" in d
    assert "(fact)" in start and "a Discover, which marks" in start
    assert "a Discover already marked `(fact)`, or a Boundary, Requirements, Allocate or Releases session already marked `(assumption)`, keeps its mark" in close


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
    assert "Never search or Read a file under `voice/` or `.inbox/`." in ask  # said once
    assert "Cite nothing you did not open in this answer." in ask
    assert "`Not recorded:`" in ask and "`Not decided:`" in ask
    assert "Never create, edit or delete a file." in ask
    assert "Sources:" in ask


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_ask_header_works_with_no_origin_and_no_claude_md(tmp_path):
    import os
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    git = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    subprocess.run(git + ["init", "-q", "-b", "main"], cwd=tmp_path, check=True, timeout=60)
    (tmp_path / "x.md").write_text("x\n", encoding="utf-8")
    subprocess.run(git + ["add", "x.md"], cwd=tmp_path, check=True, timeout=60)
    subprocess.run(git + ["commit", "-q", "-m", "x"], cwd=tmp_path, check=True, timeout=60)
    (fresh,) = run_injected(tmp_path, env)
    assert re.match(r"HEAD is [0-9a-f]+, committed \d{4}-\d{2}-\d{2}\.\n", fresh)
    assert "Behind origin/main by an unknown number of commits, as of the last fetch on no recorded date." in fresh
    assert len(run_injected(tmp_path, env)) == 1


def test_ask_fix_round_bash_read_only_and_every_claim_sourced():
    ask = text("skills/ask/SKILL.md")
    assert "Never redirect output (`>`, `>>`)." in ask
    for banned in ("`tee`", "`sed -i`", "`git commit`", "`git checkout`", "`git log --output`", "`planner render`"):
        assert banned in ask
    assert "writes a file or changes git state" in ask
    assert "Every claim rests on a page in the `Sources:` list or is labeled `Not from the vault:`. There is no third choice." in ask
    assert "Name each thing in the sentence by its plain name, not its ID." in ask  # the lead reads names; IDs sit in Sources
    assert "Assert nothing you did not open and read. A Grep snippet alone does not count." in ask
    assert "Search and Read `sessions/` only if the question asks about a session or what was said." in ask
    assert "only when the clone is behind origin/main" in ask  # a lead who asks a question does not read a commit hash first


# house voice (V1-09): close now drafts prose through it, and only through it.

def test_close_drafts_prose_through_house_voice():
    close = skill_text("close")
    assert "Read `${CLAUDE_PLUGIN_ROOT}/skills/house-voice/SKILL.md` and follow it" in close
    assert "draft: prose for <id>" in close
    assert "Prose to draft" not in close


def test_house_voice_rules():
    voice = text("skills/house-voice/SKILL.md")
    assert "in file-name order" in voice
    assert "Never read `voice/corpus/`." in voice
    assert "Replaces the paragraph above" not in voice and "## Replaced prose" in voice  # a page never carries two openings
    assert "more than about 20 prose paragraphs" in voice
    assert "acceptance criteria, and the `- Trace:` line under each;" in voice and "`**Decision:**` and `**Dissent:**` lines;" in voice


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
    assert "4 to 7 criteria" in epics and "## Done when" in epics
    assert "`[testing]`" in epics
    assert "offer `/planner:requirements` on that `CAP-nnn`, then `/planner:allocate`" in epics and "Never write the requirement into the epic." in epics
    assert "Set an epic to `decided` only when the solution lead confirms" in epics
    assert "in groups of about five" in epics and "while any criterion lacks a yes (its own or its group's)" in epics
    assert "every criterion has a yes, its own or its group's" in epics
    assert "It does not mean they are decided" in epics and "check --gate epics --app <APP-id>" in epics
    assert "list each epic still at `draft`" in epics
    assert "Its `- Trace:` line holds at least one contract (`CON-`) or flow (`FLO-`) ID" in epics and "Redis or Kafka" in epics
    assert "- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC3  ·  [testing]" in epics and "More than 7 means the epic should be split" in epics
    assert "`modes: [epics, shape, grill]` and the title `Epics: <team>`" in epics
    assert "check --gate epics" in epics
    assert "Never say an app's epics are complete while one remains." in epics


def test_modes_and_close_know_epics():
    assert "| Epics (`epics`)" in text("references/MODES.md") and "| `epics` | `draft` epic pages" in text("references/MODES.md")
    assert "owes its summary" in skill_text("close")


def test_epics_skill_frontmatter_instruction_names_the_epics_mode():
    epics = text("skills/epics/SKILL.md")
    assert "`modes: [epics, shape, grill]`" in epics and "`modes: [shape, grill]`" not in epics
    assert "Still add the `## Changes` rows for every epic" in skill_text("close")


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
    b, modes, close = text("skills/boundary/SKILL.md"), text("references/MODES.md"), skill_text("close")
    assert "Offer 2 or 3 ways to cut the direction into apps, never one and never more than three" in b
    assert "write a line only after the yes `START.md` defines" in b and "a yes to a group counts for the lines in it" in b
    assert "read the sheet back in two groups" in b.lower()
    assert "Every page this session writes is an `assumption`, never `decided`" in b and "never `addressed`" in b
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
    review, agent, close = text("references/REVIEW.md"), text("agents/area-reviewer.md"), skill_text("close")
    assert "--changed <paths>" in review and "`Changed: <paths>`" in review
    assert "it quotes a `Changed:` page" in agent
    assert "waits on UNK-050: Q-DAT-02@APP-account-link-service, R-OPS-12, F2.4" in review
    assert "A capture `waits on UNK-nnn: <IDs>` makes each ID's row `unknown`" in close and "changed in place" in close


def test_explore_opens_a_page_only_after_a_build_that_succeeded_and_writes_nothing_but_the_page_and_pins():
    explore = text("skills/explore/SKILL.md")
    assert "If the command exits 2, show its message in full, say no page was built, and stop." in explore
    assert "Never say the page is open unless the command succeeded." in explore
    assert "Nothing is written into the plugin folder." in skill_text("explore")  # product notes, in ABOUT.md, read on request
    meta = frontmatter(PLUGIN / "skills/explore/SKILL.md")
    assert "Write" not in meta["allowed-tools"].split() and "Edit" not in meta["allowed-tools"].split()


def test_every_flag_the_explore_skill_names_is_one_the_command_accepts():
    from planner import cli
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.dest == "command").choices["explore"]
    accepted = {flag for action in sub._actions for flag in action.option_strings}
    named = set(re.findall(r"`(--[a-z]+)[ `]", text("skills/explore/SKILL.md"))) | {"-o"}
    assert named and named <= accepted, named - accepted


EXPLORER_LINE = "The dashboard is up to date: dashboard.html — open it, or run /planner:explore to ask Claude from it"


def test_close_ends_by_rebuilding_the_static_explorer_and_a_failed_build_never_blocks_it():
    close = skill_text("close")
    last = close.split("\n## ")[-1]
    assert last.startswith("9. Rebuild the explorer")
    assert "scripts/planner explore` from the vault root, without `--serve`" in last
    assert EXPLORER_LINE in last
    assert "A failed build never undoes or blocks the close" in last
    assert "never say the dashboard is up to date unless the command exited 0" in last
    assert "Run it even when section 8 stopped" in last
    assert "go straight to section 9, which has its own path for a close with no session" in close
    assert "With no session" in last and "do not commit to `main` and do not push" in last
    assert "never pipe it" in last and "Read the exit status before you say anything" in last


def test_open_and_import_also_say_where_the_explorer_is_and_never_stop_on_a_failed_build():
    assert EXPLORER_LINE in text("skills/open/SKILL.md")
    imported = text("skills/import/SKILL.md")
    assert EXPLORER_LINE in imported and "a failed build never ends the import" in imported


def test_explore_and_the_vault_reference_say_designs_and_plans_live_in_the_vault_docs_folder():
    explore, ref = skill_text("explore"), text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "`docs/tech-design/<slug>.md` (with `docs/adr/`" in explore and "team_repos" not in explore
    assert "write their own `docs/` files in the vault and never edit a planner page" in explore
    assert 'says "never edit the vault"' not in explore  # an outside skill's words go stale; say what is true here
    assert "in the vault" in ref and "team_repos" not in ref


def test_the_static_build_close_runs_writes_the_page_and_names_it_on_its_last_line(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(REPO / "tests/sim/snapshots/trading-coach/after-80b", vault)
    code, said = run("explore", str(vault), "--today", "2026-10-10")
    assert code == 0, said
    assert (vault / "dashboard.html").is_file()
    assert said.strip().splitlines()[-1].startswith("planner explore: wrote ") and "serving" not in said


def test_a_build_that_fails_exits_2_says_why_and_leaves_no_new_page(tmp_path):
    code, said = run("explore", str(tmp_path / "not-a-vault"))
    assert code == 2 and said.strip(), said
    assert not (tmp_path / "not-a-vault" / "dashboard.html").exists()


def test_no_skill_or_reference_tells_the_session_to_edit_in_place_with_sed():
    """S10: a session ran GNU-only sed on macOS. The only `sed -i` allowed in the plugin's text is one that forbids it."""
    texts = [*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("references/*.md"), *PLUGIN.glob("agents/*.md")]
    assert texts
    for path in texts:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "sed -i" in line:
                assert "Never" in line or "no `sed -i`" in line, f"{path}:{number} suggests sed -i"
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert "Edit tool" in start and "no `sed -i`" in start


def test_epics_skill_disposes_of_e805_by_answer_defer_or_override_and_never_leaves_it_unplaced():
    """S11: the heron run offered "leave the gate failing", the lead took it, and the question had no owner."""
    epics = text("skills/epics/SKILL.md")
    assert "Defer it to whoever can answer" in epics and "planner next-id UNK" in epics
    assert "- Leave the gate failing." not in epics
    assert "is not a route" in epics and "do not loop" in epics


def test_boundary_asks_which_capability_each_flow_serves_and_leaves_it_out_without_capabilities():
    boundary = skill_text("boundary")
    assert "`capabilities`" in boundary and "which capability the journey serves" in boundary
    assert "leave the field out and do not invent one" in boundary


def test_house_voice_carries_the_plain_spoken_rules():
    """Design session 17: the writer persona, natural negatives, the true state once, about four things at once,
    no narrating the record, who said what kept, and the unknowns opening as the list-page example."""
    voice = text("skills/house-voice/SKILL.md")
    assert "senior technical writer explaining the system to a colleague" in voice
    assert "don't twist them into positives" in voice
    assert "Never make it sound more certain than the record" in voice
    assert "hold about four new things at once" in voice
    assert "not about the record" in voice and "## History" in voice
    assert "Who said what, and every state word" in voice
    assert "One open call holds up most of this page" in voice


def test_house_voice_protects_quoted_sentences_and_writes_capabilities_as_planned():
    """S51: the Heron rewrite broke 8 evidence quotes (E802). And capability prose said "the business can have" or
    "reads" for something not built; the user picked "will read"."""
    voice = text("skills/house-voice/SKILL.md")
    assert "a sentence another page quotes as evidence" in voice and "change the quote in the same edit" in voice and "E802" in voice
    assert "what the system will do" in voice and '"The Desktop agent will read' in voice and '"the business can have"' in voice
