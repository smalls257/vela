"""The focused reviewers and the review checkpoints in the session skills.

Each assertion pins a rule whose loss would be silent: a reviewer that writes, a persona that
creeps back, a sweep kept alongside the checkpoint that replaced it, a cap on questions, or an
area that failed and reads as clean."""
import re

import yaml

from conftest import REPO, skill_text
from planner import reviews

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def frontmatter(rel):
    return yaml.safe_load(text(rel).split("---\n", 2)[1])


# ------------------------------------------------------------------ the agent

def test_the_area_reviewer_reads_and_never_writes():
    meta = frontmatter("agents/area-reviewer.md")
    assert meta["name"] == "area-reviewer"
    assert meta["tools"] == "Read, Grep, Glob"
    assert len(meta["description"]) >= 40


def test_the_area_reviewer_returns_the_fields_the_merge_reads():
    body = text("agents/area-reviewer.md")
    for field in reviews.FIELDS:
        assert f'"{field}":' in body, field
    assert '{"area": "<your area code>", "findings": []}' in body
    assert '{"area": "<your area code>", "error": "<what stopped you>"}' in body
    assert "R-FIN-01" in body and "`pending` is `true`" in body
    assert "skip the `## Reviews` section" in body
    assert "never an empty findings list" in body


def test_the_area_reviewer_covers_the_five_areas_by_label_only():
    body = text("agents/area-reviewer.md")
    for code, label in (("FIN", "Finance and liabilities"), ("DAT", "Data and lawful basis"),
                        ("PTN", "Partners and contracts"), ("REG", "Regulation and liability"),
                        ("OPS", "Operations and people")):
        assert f"| `{code}` {label} |" in body
    lowered = body.lower()
    assert not re.search(r"\bpersonas?\b|\barchetypes?\b|\byou are an?\b", lowered)
    assert "Never read another reviewer's output" in body
    assert "There is no limit." in body


# ------------------------------------------------------------------ the checkpoint procedure

def test_review_dispatches_one_fresh_reviewer_per_area_with_a_fallback():
    review = text("references/REVIEW.md")
    assert "`planner:area-reviewer`" in review and "all five in one message" in review
    assert "general-purpose subagent" in review and "${CLAUDE_PLUGIN_ROOT}/agents/area-reviewer.md" in review
    assert "Give no conversation" in review
    assert 'If you changed a file, return `{"area": "<your area code>", "error": "changed <path>"}` instead.' in review
    assert "report any file you changed" not in review
    assert "Never review the pages yourself in this conversation." in review


def test_review_merges_in_code_and_never_reads_a_failure_as_clean():
    review = text("references/REVIEW.md")
    assert "planner findings merge .planner/findings/<session id>/<n>" in review
    assert '{"area": "<AREA>", "error": "<what happened>"}' in review
    assert "Never write an empty findings list for a reviewer that did not finish" in review
    assert "An area that did not run is never reported as clean." in review
    assert "- **Coverage:** <the merge's coverage line" in review


def test_review_tells_the_session_to_swap_inner_quotes_like_the_merge():
    review = text("references/REVIEW.md")
    assert "replace each inner straight `\"` with `”`" in review


def test_review_clears_stale_findings_and_numbers_from_the_record():
    review = text("references/REVIEW.md")
    assert "1 plus the number of `### ` headings under `## Reviews`" in review
    assert review.count("rm -rf .planner/findings/<session id>/<n>") == 2
    assert review.index("rm -rf .planner/findings/<session id>/<n> .planner/findings/<session id>/<n>-questions\nmkdir") < review.index("Save each reply")
    assert "no variables" in review


def test_review_defines_a_rerun_as_a_new_checkpoint_with_areas():
    assert "REVIEW-RERUN.md" in text("references/REVIEW.md")  # read only when an area is run again
    review = text("references/REVIEW-RERUN.md")
    assert "Re-run of checkpoint <n>: <areas>" in review
    assert "--areas FIN,REG" in review and "F<n+1>.1" in review
    assert "the ids of earlier checkpoints never change" in review


def test_review_covers_the_minor_gaps():
    review = text("references/REVIEW.md")
    assert "`areas:` block" in review and "`pending` field is `true`" in review
    assert "file name without .md" in review and "basename" not in review
    assert "baseline" in review and "compare it with the baseline" in review
    assert "skip the `## Reviews` section" in review.replace("Skip", "skip")
    assert "`Checkpoint <session id> <n>`" in review
    assert "merge failed: <error>" in review
    assert "R-` id" in review


def test_review_puts_no_cap_on_the_digest():
    review = text("references/REVIEW.md")
    assert "planner questions --open --digest" in review
    # S26: the lead is shown at most three questions, once; nothing is dropped from the ledger.
    assert "no question is dropped, only held back from the conversation" in review
    assert "At most three questions" in review and "Once per session" in review


def test_a_reviews_section_in_the_documented_form_passes_check(tmp_path):
    import shutil

    from conftest import check, findings
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    record = vault / "sessions" / "2026-11-19-owed-questions.md"
    text = record.read_text(encoding="utf-8").replace("## Changes", """## Reviews

### 1. after the read-back, 2026-11-19

- **Coverage:** FIN found 1; DAT checked, none; PTN checked, none; REG did not run (no findings file); OPS checked, none
- **Dropped:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | new | Who tells the loyalty scheme \\| and when? | "because points are earned at reservation" in [[04a-capability-delta]] |

## Changes""")
    record.write_text(text, encoding="utf-8")
    code, out = check(vault, "2026-11-20")
    assert code == 0 and findings(out) == [], out


# ------------------------------------------------------------------ the checkpoints replace the sweeps

def test_dump_runs_the_checkpoint_after_the_pre_mortem_and_the_sweep_is_gone():
    dump = text("skills/dump/SKILL.md")
    assert "references/REVIEW.md" in dump and '"after the pre-mortem"' in dump
    assert "concern sweep" not in dump
    assert "nobody has named yet" not in dump
    assert "to fetch:" in dump


def test_discover_runs_the_checkpoint_after_the_read_back_and_the_implications_list_is_gone():
    discover = text("skills/discover/SKILL.md")
    assert "references/REVIEW.md" in discover and '"after the read-back"' in discover
    assert "What these sources imply" not in discover
    assert "### PTY-nn <name>" in discover and "### SV-nn <name>" in discover
    assert "planner questions --subject <ID>" in discover


def test_modes_has_no_question_cap_and_no_sweep():
    modes = text("references/MODES.md")
    assert "at most two questions" not in modes and "concern sweep" not in modes
    assert "## Owed questions" in modes and "No question is dropped and none is owed a quota" in modes
    assert modes.count("question ledger rows") == 5  # dump, discover, shape, boundary and grill write them at close


def test_the_checks_every_area_makes_live_in_the_agent_and_not_in_the_skills():
    agent = text("agents/area-reviewer.md")
    assert "## Checks every area makes" in agent
    for line in ("service levels, hours or limits that differ", "dates, terms or numbers that disagree",
                 "a plan that a fact contradicts", "must follow a customer across systems",
                 "who gains and who loses under each reading of the ask"):
        assert line in agent
    for skill in ("skills/dump/SKILL.md", "skills/discover/SKILL.md"):
        body = text(skill)
        assert "Add to that focus" not in body and "who gains and who loses" not in body
        assert "service levels" not in body


def test_round_two_fixes_in_dump_discover_and_the_reviewer():
    dump, disc = text("skills/dump/SKILL.md"), text("skills/discover/SKILL.md")
    agent = text("agents/area-reviewer.md")
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --subject <ID>" in disc
    assert "is not a verdict on any idea" in dump
    assert "Never present the checkpoint's digest as a verdict" in dump
    assert "say aloud any pair of lines" in disc and "never two facts" in disc
    assert '"after the read-back" (the "Here\'s what I think exists" step' in disc
    assert 'type at close: PTY' in dump and 'type at close: SV' in dump
    assert "any contract or document the captures themselves name" in dump
    assert "A team that loses under one reading is a stakeholder, even if nobody named them" in agent


def test_shape_runs_the_checkpoint_before_options_with_what_must_be_true():
    shape = text("skills/shape/SKILL.md")
    assert "references/REVIEW.md" in shape and '"before options"' in shape
    assert shape.index("run the review checkpoint") < shape.index("Show the options.")
    assert '"what must be true" set' in shape and "`assumed` ledger row" in shape
    assert "planner check --gate shape" in shape


def test_grill_reads_the_blocking_questions_and_runs_the_checkpoint_on_the_agenda():
    grill = text("skills/grill/SKILL.md")
    assert "planner check --gate grill --item <ID>" in grill and "W807" in grill
    assert "references/REVIEW.md" in grill and '"on the agenda"' in grill
    assert grill.index("--gate grill") < grill.index("write the agenda into the session record")


def test_epics_reads_the_question_gate():
    assert "`E805`" in text("skills/epics/SKILL.md")


def test_shape_shows_the_top_conditions_and_sends_the_rest_through_the_digest():
    shape = text("skills/shape/SKILL.md")
    assert "only the top few conditions" in shape and "coverage line" in shape
    assert "through the one digest (REVIEW section 5)" in shape
    assert "quotes the option's capture" in shape and "counterparties" in shape
    assert "the shape gate will warn" not in shape and "tell the lead only that close will list what is still assumed" in shape


def test_grill_records_a_decision_over_an_open_blocking_question():
    grill = text("skills/grill/SKILL.md")
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner check --gate grill --item <ID>" in grill
    assert "Repeat `--item`" in grill and "exits 2" in grill and "can be stale" in grill
    assert "REVIEW section 5" in grill and "at most three questions" in grill
    assert "decided with <copy IDs> open (W807)" in grill and "`## Changes` row" in grill


def test_epics_offers_the_e805_override_with_its_exact_bullet():
    epics = text("skills/epics/SKILL.md")
    assert "- **Override:** E805 by @<handle> on <today>: <reason>" in epics
    assert "under the `## History` section at the end of `11-unknowns-and-risks.md`" in epics and "turns E805 into W805, which still prints" in epics
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner questions --open --digest" in epics
    assert "Defer it to whoever can answer" in epics and "--gate epics --app <APP-id>" in epics
    assert "Never call the epics complete past an E805 the user has neither taken nor overridden." in epics
    assert "the override is the only way to a clean `--gate epics`" in epics


# ------------------------------------------------------------------ close writes the ledger and proposes entries

def test_close_writes_a_ledger_row_for_every_copy_taken_and_every_finding():
    close = skill_text("close")
    assert "### The question ledger" in close
    assert "`R-<AREA>-nn`" in close and "Its state is `open` unless the lead took it." in close
    assert "Never write `answered` without an item link and a source" in close
    assert "<!-- generated:undisposed-questions sha=00000000: do not edit, run planner render -->" in close


def test_close_proposes_catalogue_entries_and_never_edits_the_catalogue():
    close = skill_text("close")
    assert "### Gaps the catalogue missed" in close
    assert "Never ask the lead whether a gap turned up late" in close  # S25: the answer was no, 11 times in 11
    assert "Never edit `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`" in close
    assert "planner questions --stats" in close and "Pruning is the maintainer's call." in close


def test_close_reports_questions_and_reviews_in_the_pr_body():
    close = skill_text("close")
    for label in ("**Questions:**", "**Reviews:**", "**Catalogue proposals:**"):
        assert label in close
    assert "Never write that the questions are complete." in close
    assert "planner check --gate shape" in close


def test_start_keeps_its_override_rule():
    start = text("references/START.md")
    assert "## The user may override any rule" in start and "Never refuse, and never ask twice." in start


def test_close_writes_answered_rows_in_the_grammar_check_reads():
    """An answered row needs answer: and a source check can verify. "The lead's own words in quotes"
    with no page is E802, so close must never be told to write one."""
    close = skill_text("close")
    assert "the lead's own words in double quotes" not in close
    assert "quote the words section 3 wrote" not in close
    assert "| SRC-nn | <name>'s first-hand account of <subject> | @<lead> | <today> | exists | said in session <id> |" in close
    assert "never words this close wrote. With no such source, the row is `assumed`." in close
    assert "E801, E802 or E803" in close and "Never delete a row to quiet the check" in close
    assert "Never delete a ledger row to quiet the check" in close
    assert "By is the handle of whoever recorded or decided the row" in close
    assert "`git show origin/main:11-unknowns-and-risks.md`" in close
    assert "`[[<id>#<n>. <checkpoint>, <date>]]`" in close


def test_close_types_the_subjects_dump_named_and_never_invents_a_fact():
    close = skill_text("close")
    assert "### Type the subjects Dump named" in close
    assert "`type at close: PTY`" in close and "`type at close: SV`" in close
    for label in ("**Relationship:**", "**Agreements:**", "**Holder:**", "**Owner:**"):
        assert label in close
    assert "Never fill a fact from general knowledge" in close
    assert "Only `**Owner:**` may say `not known yet`." in close and "`none known`" in close
    assert "`→ keep: [[11-unknowns-and-risks#<heading>|UNK-nnn]] (open)`" in close
    assert "A finding the lead did not take has no capture, so it gets no mark." in close


def test_conventions_lists_the_states_a_keep_mark_may_carry():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    line = next(l for l in conventions.splitlines() if l.startswith("- The `(<state>)` of a keep"))
    for state in ("inkling", "assumption", "fact", "decided", "open", "asked", "answered", "assumed",
                  "unknown", "not-applicable", "subject"):
        assert f"`{state}`" in line, state


def test_close_keeps_the_grill_record_of_a_decision_over_open_questions():
    close = skill_text("close")
    assert "decided with <copy IDs> open (W807)" in close
    assert "write no row for those copies" in close


def test_close_keeps_its_existing_guards():
    close = skill_text("close")
    for kept in ("### Voice review", "**Voicescore, optional.**", "### Harvest the owner's edits",
                 "git merge --no-edit origin/main", "Never stage anything in `voice/local/`",
                 "gh pr comment <number> --body-file <file>", "planner handoff <APP-id>",
                 "planner voicecheck"):
        assert kept in close, kept
    assert len(close.splitlines()) < 500


def test_the_ledger_grammar_close_describes_passes_check(tmp_path):
    """A realistic close outcome on a copy of the fixture: a Dump typed a stored value at close,
    and the lead answered one copy with a quote, assumed one, ruled one out, made one an unknown,
    and answered one for every stored value with a wildcard. A finding of copy `new` became a
    reviewer question. The rows, the typed subject and the new UNK must all pass check."""
    import shutil

    from conftest import check, edit, findings, run
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)

    edit(vault / "03-context-and-scope.md", "- **Owner:** Finance, through INI-004 Loyalty Revamp\n", """\
- **Owner:** Finance, through INI-004 Loyalty Revamp

### SV-02 Travel credit

- **Holder:** Booking, which keeps each credit against the booking reference it came from
- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-009 Who carries travel credit|UNK-009]]
""")
    unknowns = vault / "11-unknowns-and-risks.md"
    edit(unknowns, "## Risks\n", """\
### UNK-009 Who carries travel credit

- **Question:** Who carries travel credit as money owed to customers?
- **Owner:** @hl-solution-lead (solution lead)
- **Opened:** 2026-11-20 Dump
- **State:** open
- **Ask by:** 2026-12-18
- **Blocks:** nothing in INI-002

## Risks
""")
    rows = [
        "| Q-DAT-04@SV-02 | answered | item: [[03-context-and-scope#SV-02 Travel credit\\|SV-02]]; "
        "source: \"keeps each credit against the booking reference\" in [[03-context-and-scope]]; "
        "answer: Booking holds the credit against its booking reference | @hl-solution-lead | 2026-11-20 |",
        "| Q-FIN-05@SV-02 | assumed | belief: credit expires 12 months after the cancelled crossing; "
        "load-bearing: yes; signpost: a customer asking to use credit after a year | @hl-solution-lead | 2026-11-20 |",
        "| Q-FIN-06@SV-02 | not-applicable | reason: travel credit never converts into another scheme "
        "| @hl-solution-lead | 2026-11-20 |",
        "| Q-FIN-03@SV-02 | unknown | unknown: [[#UNK-009 Who carries travel credit\\|UNK-009]] "
        "| @hl-solution-lead | 2026-11-20 |",
        "| Q-FIN-04@SV-* | not-applicable | reason: INI-002 neither moves nor merges any value held for "
        "customers | @hl-solution-lead | 2026-11-20 |",
        "| R-FIN-02 | open | question: Does a refund to card cancel the credit, and who records it?; "
        "quote: \"keeps each credit against the booking reference\" in [[03-context-and-scope]]; "
        "severity: high | @hl-solution-lead | 2026-11-20 |",
    ]
    ledger = unknowns.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(rows) + "\n"
    unknowns.write_text(ledger, encoding="utf-8")

    (vault / "sessions" / "2026-11-20-credit-dump.md").write_text("""\
---
id: 2026-11-20-credit-dump
type: session
title: "Dump: travel credit"
date: 2026-11-20
modes: [dump]
status: closed
summary: Typed travel credit as stored value and recorded where its owed questions stand.
---

# 2026-11-20 Dump: travel credit

## Captures

- [thought] (solution lead) A cancelled crossing can be kept as travel credit, held by Booking. type at close: SV → keep: [[03-context-and-scope#SV-02 Travel credit|SV-02]] (subject) ^c01
- [thought] (solution lead) Q-FIN-05@SV-02: we believe credit expires after 12 months, and the plan rests on it → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-05@SV-02]] (assumed) ^c02
- [thought] (solution lead) Q-FIN-06@SV-02: credit never converts into another scheme → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-06@SV-02]] (not-applicable) ^c03
- [unknown] (solution lead) Q-FIN-03@SV-02: nobody here knows who carries the credit → keep: [[11-unknowns-and-risks#UNK-009 Who carries travel credit|UNK-009]] (open) ^c04
- [thought] (solution lead) Q-FIN-04@SV-*: nothing in INI-002 moves or merges held value → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-04@SV-*]] (not-applicable) ^c05

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-009 | - | open | [[2026-11-20-credit-dump#^c04]] |
| Q-DAT-04@SV-02 | - | answered | [[2026-11-20-credit-dump#^c01]] |
| Q-FIN-05@SV-02 | - | assumed | [[2026-11-20-credit-dump#^c02]] |
| Q-FIN-06@SV-02 | - | not-applicable | [[2026-11-20-credit-dump#^c03]] |
| Q-FIN-03@SV-02 | - | unknown | [[2026-11-20-credit-dump#^c04]] |
| Q-FIN-04@SV-* | - | not-applicable | [[2026-11-20-credit-dump#^c05]] |
| R-FIN-02 | - | open | [[2026-11-20-credit-dump#^c01]] |
""", encoding="utf-8")

    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    code, out = check(vault, "2026-11-20")
    assert code == 0 and findings(out) == [], out

    code, out = run("questions", "--subject", "SV-02", "--vault", str(vault))
    assert code == 0, out
    for copy, state in (("Q-DAT-04@SV-02", "answered"), ("Q-FIN-05@SV-02", "assumed"),
                        ("Q-FIN-06@SV-02", "not-applicable"), ("Q-FIN-03@SV-02", "unknown"),
                        ("Q-FIN-04@SV-02", "not-applicable via Q-FIN-04@SV-*")):
        line = next((l for l in out.splitlines() if l.startswith(copy + " ")), "")
        assert f"| {state} |" in line, (copy, out)

    code, out = run("check", "--gate", "shape", "--vault", str(vault), "--today", "2026-11-20")
    assert any(" W806 " in l and "Q-FIN-05@SV-02" in l for l in out.splitlines()), out


def test_an_answered_row_quoting_only_the_lead_is_refused(tmp_path):
    """Why close quotes a page or cites an SRC-nn: words in quotes with no page fake a source."""
    import shutil

    from conftest import check, findings
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    unknowns = vault / "11-unknowns-and-risks.md"
    row = ("| Q-FIN-02@INI-002 | answered | item: [[concern-ownership\\|Ownership]]; "
           "source: \"Platform pays for it from next year\"; answer: Platform pays | @hl-solution-lead | 2026-11-20 |")
    text = unknowns.read_text(encoding="utf-8")
    old = next(l for l in text.splitlines() if l.startswith("| Q-FIN-02@INI-002 | asked | capture:"))
    unknowns.write_text(text.replace(old, row), encoding="utf-8")
    code, out = check(vault, "2026-11-20")
    assert ("E802", "11-unknowns-and-risks.md") in findings(out), out


# ------------------------------------------------------------------ a close, run by its rules, on real records
# The helpers below apply close's rules to session records as a session leaves them, unmarked. What
# the lead says at close (facts, states, beliefs) is the only other input. Each row, mark, subject and
# unknown is derived from those, never written by hand, so the test fails if the rules produce rows
# that check refuses.

LEAD = "@hl-solution-lead"
TODAY = "2026-11-20"
CAPTURE = re.compile(r"^- \[(?P<tag>\w+)\] \((?P<origin>[^)]*)\) (?P<words>.*?) \^(?P<cid>c\d+)$")
TAKES = re.compile(r"^(?P<id>Q-[A-Z]{3}-\d{2}@[A-Za-z0-9*-]+|F\d+\.\d+): ")
TYPES = re.compile(r"type at close: (?P<kind>PTY|SV)\b")
REVIEW_ROW = re.compile(r"^\| (?P<f>F\d+\.\d+) \| (?P<area>[A-Z]{3}) \| (?P<sev>\w+) \| (?P<copy>\S+) \| "
                        r"(?P<question>.*?) \| (?P<quote>.*) \|$")


def _next_id(vault, prefix, width):
    """The next free ID of a kind: one more than the highest anywhere in the vault."""
    pattern = re.compile(re.escape(prefix) + r"(\d{%d})\b" % width)
    used = [int(n) for page in vault.rglob("*.md") for n in pattern.findall(page.read_text(encoding="utf-8"))]
    return f"{prefix}{max(used, default=0) + 1:0{width}d}"


def _insert_before(page, anchor, block):
    from conftest import edit
    edit(page, anchor, block + anchor)


def _write_unknown(vault, opened, said):
    """An unknown with an owner and an ask-by date, before ## Risks. Returns its heading and ID."""
    unk = _next_id(vault, "UNK-", 3)
    heading = f"{unk} {said['name']}"
    _insert_before(vault / "11-unknowns-and-risks.md", "## Risks\n", f"""### {heading}

- **Question:** {said['question']}
- **Owner:** {LEAD} (solution lead)
- **Opened:** {TODAY} {opened}
- **State:** open
- **Ask by:** {said['ask_by']}
- **Blocks:** nothing in INI-002

""")
    return heading, unk


def _type_subject(vault, kind, said, opened):
    """Close's typing rule. Returns the mark for the capture, the Changes rows, and what the existence
    copy's row needs: ("answered", a link to the subject) or ("unknown", the UNK that asks)."""
    scope = vault / "03-context-and-scope.md"
    facts = dict(said["facts"])
    if kind == "PTY" and facts["Relationship"] is None or kind == "SV" and facts["Holder"] is None:
        heading, unk = _write_unknown(vault, opened, said["unknown"])
        return f"keep: [[11-unknowns-and-risks#{heading}|{unk}]] (open)", [(unk, "open")], ("unknown", unk)
    changes = []
    if kind == "SV" and facts["Owner"] is None:
        heading, unk = _write_unknown(vault, opened, said["unknown"])
        facts["Owner"] = f"not known yet, see [[11-unknowns-and-risks#{heading}|{unk}]]"
        changes.append((unk, "open"))
    subject = _next_id(vault, f"{kind}-", 2)
    bullets = "".join(f"- **{label}:** {value}\n" for label, value in facts.items())
    section = "## Out of scope\n" if kind == "SV" else "## Value held for customers\n"
    _insert_before(scope, section, f"### {subject} {said['name']}\n\n{bullets}\n")
    link = f"[[03-context-and-scope#{subject} {said['name']}\\|{subject}]]"
    return f"keep: [[03-context-and-scope#{subject} {said['name']}|{subject}]] (subject)", changes, ("answered", link)


def _has_row(vault, copy):
    ledger = (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    return any(l.startswith(f"| {copy} | ") for l in ledger.split("<!-- /generated:undisposed-questions -->")[-1].splitlines())


def _evidence(vault, copy, said, session):
    """The evidence for a row, in the state table's grammar, with close's source rule."""
    state = said["state"]
    if state == "answered":
        source = said.get("source")
        if source is None:  # the lead's word is the only source: a first-hand row
            source = _next_id(vault, "SRC-", 2)
            sources = vault / "sources.md"
            last = [l for l in sources.read_text(encoding="utf-8").splitlines() if l.startswith("| SRC-")][-1]
            from conftest import edit
            edit(sources, last + "\n", last + f"\n| {source} | Solution lead's first-hand account of {said['about']} "
                                              f"| {LEAD} | {TODAY} | exists | said in session {session} |\n")
        return f"item: {said['item']}; source: {source}; answer: {said['answer']}"
    if state == "assumed":
        return f"belief: {said['belief']}; load-bearing: {said['load_bearing']}; signpost: {said['signpost']}"
    if state == "unknown":
        unk = said["unknown"]
        heading = next(l[4:] for l in (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8").splitlines()
                       if l.startswith(f"### {unk} "))
        return f"unknown: [[#{heading}\\|{unk}]]"
    assert state == "not-applicable", state
    return f"reason: {said['reason']}"


def _close(vault, record_name, said):
    """Mark every capture, type subjects, write the ledger rows, then close the record."""
    record = vault / "sessions" / f"{record_name}.md"
    lines = record.read_text(encoding="utf-8").splitlines()
    findings_ = {m["f"]: m for m in map(REVIEW_ROW.match, lines) if m}
    checkpoint = next((l[4:] for l in lines if re.match(r"^### \d+\. ", l)), None)
    ledger_rows, changes, taken = [], [], set()
    for i, line in enumerate(lines):
        capture = CAPTURE.match(line)
        if not capture or "→" in line:
            continue
        cid, words = capture["cid"], capture["words"]
        typed, take = TYPES.search(words), TAKES.match(words)
        if typed:
            # One mark, to the subject (or to the unknown when it stays untyped). The existence copy the
            # capture starts with gets its row here, and its Changes row cites the capture.
            mark, more, (state, what) = _type_subject(vault, typed["kind"], said[cid], record_name.split("-", 3)[3])
            changes += [(item, s, f"[[{record_name}#^{cid}]]") for item, s in more]
            if take and not _has_row(vault, take["id"]):
                row_said = dict(said[cid]["yes"], state=state)
                row_said["item" if state == "answered" else "unknown"] = what
                ledger_rows.append(f"| {take['id']} | {state} | {_evidence(vault, take['id'], row_said, record_name)} "
                                   f"| {LEAD} | {TODAY} |")
                changes.append((take["id"], state, f"[[{record_name}#^{cid}]]"))
        elif take:
            copy = take["id"]
            if copy.startswith("F"):
                taken.add(copy)
                copy = findings_[copy]["copy"]
            row_said = said[cid]
            ledger_rows.append(f"| {copy} | {row_said['state']} | {_evidence(vault, copy, row_said, record_name)} "
                               f"| {LEAD} | {TODAY} |")
            changes.append((copy, row_said["state"], f"[[{record_name}#^{cid}]]"))
            mark = f"keep: [[11-unknowns-and-risks#Question ledger|{copy}]] ({row_said['state']})"
        else:
            mark = said.get(cid, "park")
        lines[i] = line.replace(f" ^{cid}", f" → {mark} ^{cid}")
    for fid, finding in findings_.items():
        if fid in taken or finding["copy"] != "new":
            continue  # a finding about an owed copy the lead did not take adds no row
        r_id = _next_id(vault, f"R-{finding['area']}-", 2)
        ledger_rows.append(f"| {r_id} | open | question: {finding['question']}; quote: {finding['quote']}; "
                           f"severity: {finding['sev']} | {LEAD} | {TODAY} |")
        changes.append((r_id, "open", f"[[{record_name}#{checkpoint}]]"))
    unknowns = vault / "11-unknowns-and-risks.md"
    unknowns.write_text(unknowns.read_text(encoding="utf-8").rstrip("\n") + "\n"
                        + "".join(row + "\n" for row in ledger_rows), encoding="utf-8")
    text = "\n".join(lines) + "\n"
    text = text.replace("status: open", "status: closed")
    text = text.rstrip("\n") + "\n" + "".join(f"| {i} | - | {s} | {src} |\n" for i, s, src in changes)
    record.write_text(text, encoding="utf-8")


DUMP_RECORD = """\
---
id: 2026-11-20-credit-dump
type: session
title: "Dump: travel credit"
date: 2026-11-20
modes: [dump]
status: open
summary: Travel credit for cancelled crossings.
---

# 2026-11-20 Dump: travel credit

## Captures

- [thought] (solution lead) Q-FIN-01@INI-002: yes, customers who cancel can keep the fare as travel credit, held in Booking. type at close: SV ^c01
- [thought] (solution lead) Q-DAT-01@INI-002: yes, a travel insurer may sell cover with each crossing and would see the booking, and nobody here knows how we would deal with them. type at close: PTY ^c02
- [wild] (claude) Credit could be given away as a gift to another customer. ^c03

## Changes

| ID | From | To | Source |
|---|---|---|---|
"""

SHAPE_RECORD = """\
---
id: 2026-11-20-credit-expiry
type: session
title: "Shape: when travel credit expires"
date: 2026-11-20
modes: [shape]
status: open
summary: Options for when travel credit expires.
---

# 2026-11-20 Shape: when travel credit expires

## Captures

- [thought] (claude) Option A: credit expires 12 months after the cancelled crossing, and Booking removes it then. ^c01
- [thought] (claude) Option B: credit never expires, and finance carries it until it is used. ^c02
- [thought] (solution lead) Neither option fits until we know who carries the credit, so both are rejected for now. ^c03
- [thought] (solution lead) F1.1: we believe credit lasts 12 months, and the plan rests on it ^c04
- [thought] (solution lead) Q-DAT-04@SV-02: Booking is the one record of each customer's credit balance ^c05
- [unknown] (solution lead) Q-FIN-03@SV-02: nobody here knows who carries the credit ^c06
- [thought] (solution lead) Q-FIN-04@SV-*: nothing in INI-002 moves value between schemes ^c07

## Reviews

### 1. before options, 2026-11-20

- **Coverage:** FIN found 3; DAT checked, none; PTN checked, none; REG checked, none; OPS checked, none
- **Dropped:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-05@SV-02 | What happens to the credit at expiry? | "credit expires 12 months after the cancelled crossing" in [[2026-11-20-credit-expiry]] |
| F1.2 | FIN | normal | Q-FIN-06@SV-02 | Who sets the rate if credit converts? | "finance carries it until it is used" in [[2026-11-20-credit-expiry]] |
| F1.3 | FIN | high | new | Does a refund to card cancel the credit, and who records it? | "keep the fare as travel credit" in [[2026-11-20-credit-dump]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
"""

DUMP_SAID = {
    "c01": {"name": "Travel credit",
            "facts": {"Holder": "Booking, which keeps each credit against its booking reference", "Owner": None},
            "unknown": {"name": "Who carries travel credit", "ask_by": "2026-12-18",
                        "question": "Who carries travel credit as money owed to customers?"},
            "yes": {"about": "travel credit", "answer": "yes, Booking holds travel credit for customers who cancel"}},
    "c02": {"name": "Travel insurer", "facts": {"Relationship": None, "Agreements": "none known"},
            "unknown": {"name": "How we deal with a travel insurer", "ask_by": "2026-12-18",
                        "question": "Would a travel insurer be our partner or our supplier?"},
            "yes": {}},
}

SHAPE_SAID = {
    "c04": {"state": "assumed", "belief": "credit lasts 12 months after the cancelled crossing",
            "load_bearing": "yes", "signpost": "a customer asking to use credit after a year"},
    "c05": {"state": "answered", "item": "[[03-context-and-scope#SV-02 Travel credit\\|SV-02]]",
            "about": "travel credit", "answer": "Booking is the one record of each customer's credit balance"},
    "c06": {"state": "unknown", "unknown": "UNK-009"},
    "c07": {"state": "not-applicable", "reason": "nothing in INI-002 moves value between schemes"},
}


def _states(vault, subject):
    from conftest import run
    code, out = run("questions", "--subject", subject, "--vault", str(vault))
    assert code == 0, out
    return {l.split(" | ")[0]: l.split(" | ")[3] for l in out.splitlines()[1:] if " | " in l}


def test_a_close_run_by_its_rules_on_a_dump_then_a_shape_passes_check(tmp_path):
    import shutil

    from conftest import check, findings, run
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    # A vault where nobody has asked the two existence questions yet, so the gate holds both.
    ledger = vault / "11-unknowns-and-risks.md"
    ledger.write_text("".join(l for l in ledger.read_text(encoding="utf-8").splitlines(keepends=True)
                              if not l.startswith(("| Q-FIN-01@INI-002 |", "| Q-DAT-01@INI-002 |"))), encoding="utf-8")
    gate = run("check", "--gate", "epics", "--vault", str(vault), "--today", TODAY)[1]
    assert any(" E805 Q-FIN-01@INI-002 " in l for l in gate.splitlines()), gate
    (vault / "sessions" / "2026-11-20-credit-dump.md").write_text(DUMP_RECORD, encoding="utf-8")

    _close(vault, "2026-11-20-credit-dump", DUMP_SAID)
    run("render", "--vault", str(vault))
    code, out = check(vault, TODAY)
    assert code == 0 and findings(out) == [], out
    scope = (vault / "03-context-and-scope.md").read_text(encoding="utf-8")
    assert "### SV-02 Travel credit" in scope and "PTY-03" not in scope
    dump = (vault / "sessions" / "2026-11-20-credit-dump.md").read_text(encoding="utf-8")
    assert "→ keep: [[11-unknowns-and-risks#UNK-010 How we deal with a travel insurer|UNK-010]] (open) ^c02" in dump
    assert "→ park ^c03" in dump
    assert "travel credit, held in Booking. type at close: SV → keep: [[03-context-and-scope#SV-02 Travel credit|SV-02]] (subject) ^c01" in dump
    assert dump.count("→") == 3, dump  # one mark per capture, never a second one for the ledger row
    rows = (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    assert ("| Q-FIN-01@INI-002 | answered | item: [[03-context-and-scope#SV-02 Travel credit\\|SV-02]]; source: SRC-11; "
            "answer: yes, Booking holds travel credit for customers who cancel |") in rows
    assert "| Q-DAT-01@INI-002 | unknown | unknown: [[#UNK-010 How we deal with a travel insurer\\|UNK-010]] |" in rows
    assert "| Q-FIN-01@INI-002 | - | answered | [[2026-11-20-credit-dump#^c01]] |" in dump
    owed = _states(vault, "SV-02")
    assert sorted(owed) == ["Q-DAT-04@SV-02", "Q-FIN-03@SV-02", "Q-FIN-04@SV-02", "Q-FIN-05@SV-02", "Q-FIN-06@SV-02"]
    assert set(owed.values()) == {"no row"}, owed

    (vault / "sessions" / "2026-11-20-credit-expiry.md").write_text(SHAPE_RECORD, encoding="utf-8")
    _close(vault, "2026-11-20-credit-expiry", SHAPE_SAID)
    run("render", "--vault", str(vault))
    code, out = check(vault, TODAY)
    assert code == 0 and findings(out) == [], out

    assert _states(vault, "SV-02") == {
        "Q-DAT-04@SV-02": "answered",
        "Q-FIN-03@SV-02": "unknown",
        "Q-FIN-04@SV-02": "not-applicable via Q-FIN-04@SV-*",
        "Q-FIN-05@SV-02": "assumed",
        "Q-FIN-06@SV-02": "no row",
    }
    ledger = (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    assert "| R-FIN-02 | open | question: Does a refund to card cancel the credit" in ledger
    assert "Q-FIN-06@SV-02 |" not in ledger.split("<!-- /generated:undisposed-questions -->")[1]
    assert "| SRC-11 | Solution lead's first-hand account of travel credit |" in (vault / "sources.md").read_text(encoding="utf-8")
    shape = (vault / "sessions" / "2026-11-20-credit-expiry.md").read_text(encoding="utf-8")
    assert "| R-FIN-02 | - | open | [[2026-11-20-credit-expiry#1. before options, 2026-11-20]] |" in shape

    code, out = run("check", "--gate", "shape", "--vault", str(vault), "--today", TODAY)
    assert any(" W806 " in l and "Q-FIN-05@SV-02" in l for l in out.splitlines()), out
    gate = run("check", "--gate", "epics", "--vault", str(vault), "--today", TODAY)[1]
    assert not any(" E805 Q-FIN-01@" in l or " E805 Q-DAT-01@" in l for l in gate.splitlines()), gate

    # The rule the untyped party's mark exists for: a keep to the heading it never got is E202.
    record = vault / "sessions" / "2026-11-20-credit-dump.md"
    record.write_text(record.read_text(encoding="utf-8").replace(
        "[[11-unknowns-and-risks#UNK-010 How we deal with a travel insurer|UNK-010]] (open)",
        "[[03-context-and-scope#PTY-03 Travel insurer|PTY-03]] (subject)"), encoding="utf-8")
    assert ("E202", "sessions/2026-11-20-credit-dump.md") in findings(check(vault, TODAY)[1])


def test_review_hands_each_reviewer_a_real_questions_file_and_the_reviewer_refuses_a_placeholder():
    review, agent = text("references/REVIEW.md"), text("agents/area-reviewer.md")
    assert "--json > .planner/findings/<session id>/<n>-questions/<AREA>.json" in review
    assert "`Questions file: .planner/findings/<session id>/<n>-questions/<AREA>.json`" in review
    assert "Never send a placeholder" in review
    assert review.index("-questions/<AREA>.json`. They sit") < review.index("Dispatch the `planner:area-reviewer`")
    assert "a placeholder" in agent and "no questions file" in agent


def test_a_review_digest_puts_at_most_five_questions_to_the_lead_in_a_turn_and_never_pastes_findings():
    """S12: the heron run's turn 38 put 89 question marks to the lead, with the reviewers' raw JSON."""
    review = text("references/REVIEW.md")
    assert "At most three questions" in review and "A turn of 50 questions is a dump" in review
    assert "Never paste a reviewer's reply, or the findings JSON, into the conversation" in review
    assert "no question is dropped" in review


def test_modes_asks_once_what_the_lead_might_not_know_they_need():
    modes = text("references/MODES.md")
    assert "**Ask what they might not know they need.**" in modes
    assert "In Discover, Shape and Grill" in modes and "who has to agree or be consulted" in modes
