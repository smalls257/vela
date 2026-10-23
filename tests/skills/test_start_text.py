"""What the start reference says, pinned in one place (overhaul plan Task 3; rewritten by Task 22j).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Task 22j moved START steps 1 to 5 into `vela session start` and `vela session brief`, the handle into `vela whoami`,
capture numbering into `vela record add` and the override grammar into `vela apply`. Each moved rule has a
rule-deletion assert here, so the old recipe can't creep back beside the command that now does it.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


START = text("references/START.md")
ANSWER = text("references/ANSWER-A-CHALLENGE.md")


def section(heading):
    """The text under a `## heading` up to the next `## `."""
    return START.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


START_RULE = ("The user may override any rule in these skills. Say once, in one plain sentence and without the rule's "
              "code, what the rule protects. Then do what they asked, ask the reason once, and record it with "
              "`vela apply`")


# --- where vela runs from: one line here, the ladder is `vela where`'s and pluginroot's


def test_where_vela_runs_from_is_one_line_that_points_at_where():
    """The six-step ladder moved out of the instruction path: `pluginroot` holds the order and its why, `/vela:where`
    prints it. START keeps the path, the unexpanded-variable tell and the pointer."""
    from vela import pluginroot
    line = section("Where vela runs from")
    assert "`sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela`" in line and "`/vela:where`" in line
    assert "literal `${`" in line and len(line.split()) < 60
    for gone in ("${CLAUDE_SKILL_DIR}", "synced/", "Cowork", "vela_path", "vela() {", "zsh", "$P"):
        assert gone not in line, gone
    assert START.count("## Where vela runs from") == 1
    assert [c.source for c in pluginroot.candidates("/p", "/s", "/v", "")][:2] == ["${CLAUDE_SKILL_DIR}", "${CLAUDE_PLUGIN_ROOT}"]
    assert "zsh, which doesn't split `$P` into words" in " ".join(pluginroot.__doc__.split())  # the why moved to the module, not the void


# --- step 0: the voice comes before any command output reaches the lead (voice audit S1)


def test_start_reads_the_voice_before_anything_reaches_the_lead():
    step = section("0. Read how to talk")
    assert "Before you say anything to the lead" in step
    assert step.index("voice/VOICE.md") < step.index("/CONVERSATION-VOICE")  # a mention, not a pin of that file's text
    assert "Each mode skill says this again in one line" not in START  # rule deletion: the skills say it, START needn't
    assert "--for-lead" in step and "git's or gh's own error text" in step
    assert START.index("## 0. Read how to talk") < START.index("## Where vela runs from")


def test_start_never_passes_raw_tool_text_to_the_lead():
    """Voice audit S2, S3: "in its own words" read as the tool's words, and "show its message" pasted git errors."""
    for old in ("in its own words", "show its message", "show the error", "Show the error"):
        assert old not in START, old
    assert "tell the lead in one plain sentence what you couldn't do, and go on" in START


# --- steps 1 to 5 are commands now


def test_start_opens_the_session_with_session_start_and_briefs_with_session_brief():
    one = section("1. Start the session")
    assert "`vela session start --mode grill --topic" in one and "--for-lead" in one
    assert "`vela session brief --for-lead`" in one
    assert "On exit 3 it changes nothing: ask what it asks, one at a time, and run it again." in one


def test_start_steps_one_to_five_no_longer_carry_the_recipes():
    """Rule deletion: the commands do these now, so the hand-run versions are gone."""
    for recipe in ("git status --short --branch", "git switch main", "git pull --ff-only", "git branch -r --list",
                   "git branch --list 'session/*'", "git grep -l '^status: open'", "git switch -c session/<id>",
                   "gh pr list --state merged", "pulls/<number>/reviews", "add `-2`, then `-3`",
                   "status: open\nsummary: In progress.", "Commit it with the message `Open session <id>`",
                   "commit it with the message `Name the initiative`", "W705", "W718",
                   "`findings/`, `owed/`, `close/`"):
        assert recipe not in START, recipe


def test_the_choices_session_start_prints_are_not_copied_into_start():
    """Rule deletion (the October 22 trim): `session start` exit 3 prints each choice, every time it applies."""
    for copy in ("`--resume <id>`", "`--new`", "No plan here yet", "Which plan", "Find open sessions",
                 "vela new --title", "vela plans --here", "`--title \"<their words>\"`", "git init", "--handle",
                 "Never set a plan up by hand", "Never guess, and never pick the first"):
        assert copy not in START, copy
    from vela.commands import plans, session
    plan = session.no_plan_yet()
    assert "vela new --title" in plan.needs_lead[0]["answer_with"] and "git init" in plan.lines[0].text
    which = plans.which_plan([{"folder": "a", "title": "A", "said": "A", "path": "a"},
                              {"folder": "b", "title": "B", "said": "B", "path": "b"}])
    assert "--vault <folder>" in which.lines[0].text and "never guess" in which.lines[0].text
    assert session.NAMING_QUESTION if hasattr(session, "NAMING_QUESTION") else True
    from vela import sessions
    assert "What short name should this initiative go by?" in sessions.NAMING_QUESTION


def test_start_keeps_bringing_main_in_and_freshness():
    one = section("1. Start the session")
    assert "never call the plan up to date when the shared copy was out of reach" in one
    assert "doesn't switch branches or pull `main`" in one and "`vela close sync-main`" in one
    assert "`vela freshness --for-lead`" in section("Owner or reader")


def test_start_never_mentions_a_probe_skill_because_next_says_what_to_do():
    assert "probe" not in START.lower()
    assert "ask whether the lead knows the answer now" in section("1. Start the session")


def test_start_never_drafts_an_ask():
    assert "never draft an ask for the user to send" in START


def test_start_offers_the_next_step_as_a_suggestion():
    assert "as a suggestion, never a decision" in section("1. Start the session")


def test_the_first_session_asks_for_the_name_once():
    assert "The initiative's name is asked once" not in START  # rule deletion: the command asks, and `--unnamed` is its own
    assert "`--unnamed`" not in START


def test_start_no_longer_lists_the_mode_display_names():
    """Rule deletion: the names are MODES.md's table and `sessions.MODE_NAMES`; START said them a third time."""
    assert "Epics, Challenge or Answer." not in START and "display name" not in START


def test_start_says_where_a_resumed_grill_carries_on():
    assert "## Agenda" in section("1. Start the session")
    assert "Never close a session the user hasn't asked to close" in START


# --- owner or reader: three lines, every command knows its role


def test_start_says_a_reader_runs_no_git_in_a_few_lines():
    reader = section("Owner or reader")
    assert "This is a read copy, so I will not use git" in reader
    assert len(reader.split()) < 110
    assert "- **Pending approval:** @<their handle>, <today>" not in START  # decide writes it in a reader copy


def test_the_handle_comes_from_whoami():
    assert "`vela whoami`" in START
    assert "gh api user -q .login" not in START and ".vela/handle" not in START  # rule deletion: whoami does it
    assert ".vela/*" in (REPO / "plugin" / "template" / ".gitignore").read_text(encoding="utf-8")


# --- plain names, one definition


def test_start_forbids_codes_in_conversation_and_names_what_counts():
    plain = section("Plain names and a page a person can hold")
    for kind in ("capture number", "check code", "gate name", "rule name"):
        assert kind in plain, kind
    assert "The lead reads names, never codes." in plain
    assert '"/vela:grill Desktop agent"' in plain  # a command the lead types names the thing, not its ID
    assert "If the lead asks for an ID, give it." in plain
    assert "copy and finding IDs" not in plain  # rule deletion: the kind-by-kind list is CONVERSATION-VOICE rule 5's


def test_start_says_states_and_spelling_in_words():
    plain = section("Plain names and a page a person can hold")
    for word in ("Say states in words", "American spelling", '"Organizer"', "spell out an abbreviation"):
        assert word in plain, word
    for gone in ("`vela terms <word>`", "the team lead", '"the plan"', "just an idea"):  # `vela terms` and the style check own these
        assert gone not in plain, gone
    assert not re.search(r"\bGrill\b(?! \(`| part)", plain)


def test_start_holds_conversation_rule_seven():
    plain = section("Plain names and a page a person can hold")
    assert "Answer first, then about four things at most" in plain and '"there are six more; want them?"' in plain


def test_the_group_yes_is_defined_once_here():
    assert "A yes that covers a group you read out" in START and "groups of about five" in START


def test_start_states_the_reading_load():
    assert "## Plain names and a page a person can hold" in START


# --- shell, override, hard stops


def test_no_skill_or_reference_tells_the_session_to_edit_in_place_with_sed():
    """S10: a session ran GNU-only sed on macOS. The only `sed -i` allowed in the plugin's text is one that forbids it."""
    texts = [*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("references/*.md"), *PLUGIN.glob("agents/*.md")]
    assert texts
    for path in texts:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "sed -i" in line:
                assert "Never" in line or "no `sed -i`" in line, f"{path}:{number} suggests sed -i"
    assert "Edit tool" in START and "no `sed -i`" in START


def test_start_holds_the_shared_override_rule_and_its_hard_stops():
    assert START_RULE in START and "Never refuse, and never ask twice." in START
    assert "Hard stops are not process rules" in START
    for stop in ("`~/.claude`", "company material", "unless the tool printed it"):
        assert stop in START


def test_the_override_grammar_is_the_clis():
    override = section("The user may override any rule")
    assert "`vela apply --schema override`" in override
    assert "- **Override:** <rule> by @" not in START and "`GATE-1` to `GATE-5`" not in START  # rule deletion


def test_every_never_list_is_a_default_the_user_can_override_because_start_says_so_once():
    assert 'every "never" and "must not" in the skills' in START
    for doc in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        body = doc.read_text(encoding="utf-8")
        assert "These are the defaults" not in body, doc.parent.name
        if "\n## Never\n" in body:
            rest = body.split("\n## Never\n", 1)[1]
            assert not re.search(r"cannot be overridden|may not be overridden|no override", rest, re.I), doc.parent.name


# --- closing and captures


def test_start_never_starts_close_and_close_waits_for_a_yes_before_sending():
    closing = section("Closing a session")
    assert "Never start close" in closing and "close says what will be sent and waits for a yes" in closing
    assert "CAP-005" not in closing and "`/vela:requirements booking changes`" in closing
    # The confirm run's diagnosis: START said typing /vela:close or saying "push" was consent to send, which close
    # never accepts (its section 7 sends only on a yes captured after the notice). One route, said once.
    assert "unless the lead typed" not in closing and "in so many words" not in closing
    assert "That yes, given after close says what goes, is the only one that sends." in closing


def test_captures_are_numbered_by_record_add_and_keep_their_origins():
    captures = section("Captures during the session")
    assert "`vela record add --origin <who> --tag <tag>" in captures
    assert "^c01" not in captures and "never reused" not in captures  # rule deletion: record add numbers them
    assert "claude, from <name>" in captures and "promoted on a nod" in captures
    assert "`vela close stage --checkpoint`" in captures
    assert "never `git add -A`" in captures and "by exact path" not in captures  # hook-only rule stays; the how is the command's


def test_start_names_every_mode_that_marks_at_once():
    marks = START.split("Leave the mark off until close")[1].split("\n")[0]
    for name in ("grill", "Discover", "Boundary", "Requirements", "Allocate", "Releases"):
        assert name in marks, name
    assert "(decided)" in marks and "(fact)" in marks and "(assumption)" in marks


# --- answer a challenge


def test_start_answers_a_challenge_on_its_own_branch():
    assert "ANSWER-A-CHALLENGE.md" in section("Answer a challenge")
    assert "`vela session start --mode answer --answer <PR number or the challenged ID> --for-lead`" in ANSWER
    assert "never starts on a guessed branch" in ANSWER
    assert "never opening a new one" in ANSWER and "adds `grill` to the session's modes" in ANSWER


def test_answer_a_challenge_lost_its_recipe_to_session_start():
    for recipe in ("gh pr list --search", "git switch <headRefName>", "Do not run `git switch -c`",
                   "`<date>-answer-<id-lowercased>`", "E316", "senior", "Grill"):
        assert recipe not in ANSWER, recipe
    assert len(ANSWER.split()) < 240  # the stub/notes split and the read-back words rule add two sentences


def test_relaying_a_command_says_more_and_what_to_do_on_my_side():
    """A `--for-lead` line that says "Something went wrong on my side" is say.MY_SIDE: a refusal only the model can fix.
    START says once how to read it (the same command with --json), and how to get the rest of a long list (--more)."""
    from vela import say
    relay = section("Relaying a command")
    assert say.MY_SIDE.split(";")[0] in relay
    assert "with `--json` in place of `--for-lead`" in relay and "`plain` and `fix` fields" in relay
    assert "never say that line or the command's own text" in relay
    assert "run the same command again with `--more` added" in relay
    assert '"Relaying a command" below' in section("0. Read how to talk")


# --- Drafting as each item settles: the house voice is written when the item is filed, and close only fills what is
# missing or went stale. The rule is written once here; each mode skill's own test file pins its one line.

def test_start_says_once_to_draft_the_paragraph_when_the_item_is_filed():
    rule = section("Draft the paragraph when the item is filed")
    assert "in the same turn" in rule and "skills/house-voice/SKILL.md" in rule
    assert "from the record as it stands" in rule and "with the filed line" in rule
    assert "change only the fact that changed" in rule and "What is never voiced" in rule
    assert "close lists only what is missing or went stale" in rule
    assert START.count("Draft the paragraph when the item is filed") == 1
