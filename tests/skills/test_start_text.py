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


# --- where vela runs from


def test_start_tries_skill_dir_first():
    """`${CLAUDE_SKILL_DIR}` is the variable both apps document expanding in skill text, so START and `vela where`
    try it before `${CLAUDE_PLUGIN_ROOT}`, and in the same order."""
    from vela import pluginroot
    order = START.split("## Where vela runs from")[1].split("\n## ")[0]
    assert order.index("1. `${CLAUDE_SKILL_DIR}/../../scripts/vela`") < order.index("2. `${CLAUDE_PLUGIN_ROOT}/scripts/vela`")
    assert [c.source for c in pluginroot.candidates("/p", "/s", "/v", "")][:2] == ["${CLAUDE_SKILL_DIR}", "${CLAUDE_PLUGIN_ROOT}"]


def test_the_resolution_order_is_stated_once_in_start():
    assert START.count("## Where vela runs from") == 1
    order = section("Where vela runs from")
    positions = [order.index(m) for m in ("1. `${CLAUDE_SKILL_DIR}/../../scripts/vela`", "2. `${CLAUDE_PLUGIN_ROOT}/scripts/vela`",
                                          "3. An installed copy in the plugins folder", "/synced/*/vela/scripts/vela",
                                          "/cache/*/vela/*/scripts/vela", "4. `.claude/skills/vela/scripts/vela`",
                                          "vela_path")]
    assert positions == sorted(positions)
    assert "Cowork" in order and "marketplace install" in order  # why synced/ and cache/ are both listed
    assert "I cannot find the vela program. Run `/vela:where` and send me what it prints." in order


def test_start_calls_vela_through_a_function_zsh_can_run():
    """Diagnosis 6C: `P="python3 ..."; $P check` exits 127 in zsh, which doesn't word-split; 44 retries in two runs."""
    order = section("Where vela runs from")
    assert 'vela() { python3 <the path> "$@"; }' in order
    assert "zsh doesn't split `$P` into words" in order


# --- step 0: the voice comes before any command output reaches the lead (voice audit S1)


def test_start_reads_the_voice_before_anything_reaches_the_lead():
    step = section("0. Read how to talk")
    assert "Before you say anything to the lead" in step
    assert step.index("voice/VOICE.md") < step.index("/CONVERSATION-VOICE")  # a mention, not a pin of that file's text
    assert "Each mode skill says this again in one line" in step  # START and the skills agree
    assert "no skill repeats it" not in START
    assert "--for-lead" in step and "git's or gh's own error text" in step
    assert START.index("## 0. Read how to talk") < START.index("## Where vela runs from")


def test_start_never_passes_raw_tool_text_to_the_lead():
    """Voice audit S2, S3: "in its own words" read as the tool's words, and "show its message" pasted git errors."""
    for old in ("in its own words", "show its message", "show the error", "Show the error"):
        assert old not in START, old
    assert "say in one plain sentence that you couldn't check, and go on" in START


# --- steps 1 to 5 are commands now


def test_start_opens_the_session_with_session_start_and_briefs_with_session_brief():
    assert "`vela session start --mode grill --topic" in section("1. Show the state of the clone")
    assert "--for-lead" in section("1. Show the state of the clone")
    assert "`vela session brief --for-lead`" in section("3. Bring in review comments")
    assert "exits 3 with the choices" in section("2. Find open sessions")
    for choice in ("`--resume <id>`", "`/vela:close`", "`--new`"):
        assert choice in section("2. Find open sessions"), choice


def test_start_steps_one_to_five_no_longer_carry_the_recipes():
    """Rule deletion: the commands do these now, so the hand-run versions are gone."""
    for recipe in ("git status --short --branch", "git switch main", "git pull --ff-only", "git branch -r --list",
                   "git branch --list 'session/*'", "git grep -l '^status: open'", "git switch -c session/<id>",
                   "gh pr list --state merged", "pulls/<number>/reviews", "add `-2`, then `-3`",
                   "status: open\nsummary: In progress.", "Commit it with the message `Open session <id>`",
                   "commit it with the message `Name the initiative`", "W705", "W718",
                   "`findings/`, `owed/`, `close/`"):
        assert recipe not in START, recipe


def test_start_keeps_bringing_main_in_and_freshness():
    one = section("1. Show the state of the clone")
    assert "brings `main` up to the shared copy" in one and "never call the plan up to date" in one
    assert "`vela freshness`" in one


def test_start_never_mentions_a_probe_skill_because_next_says_what_to_do():
    four = START.split("## 4.", 1)[1].split("## 5.", 1)[0]
    assert "probe" not in START.lower()
    assert "ask the user whether they know the answer now" in four


def test_start_never_drafts_an_ask():
    assert "Never draft an ask for the user to send, and never offer to." in START


def test_start_offers_the_next_step_as_a_suggestion():
    assert "as a suggestion, never a decision" in section("4. Offer the overdue unknowns and the next step")


def test_the_first_session_asks_for_the_name_once():
    paragraph = START.split("**Name the initiative, once.**", 1)[1].split("\n", 1)[0]
    assert "What short name should this initiative go by?" in paragraph
    assert '`--title "<their words>"`' in paragraph and "never ask again" in paragraph and "`--unnamed`" in paragraph
    assert "Reader copy" in paragraph


def test_start_lists_every_mode_display_name():
    assert "Epics, Challenge or Answer." in START


def test_start_says_where_a_resumed_grill_carries_on():
    assert "## Agenda" in section("2. Find open sessions")
    assert "Never close a session the user hasn't asked to close" in START


# --- owner or reader: three lines, every command knows its role


def test_start_says_a_reader_runs_no_git_in_a_few_lines():
    reader = section("Owner or reader")
    assert "This is a read copy, so I will not use git" in reader
    assert len(reader.split()) < 130
    assert "- **Pending approval:** @<their handle>, <today>" not in START  # decide writes it in a reader copy
    assert "**Reader copy:**" in section("1. Show the state of the clone")


def test_the_handle_comes_from_whoami():
    assert "`vela whoami`" in START
    assert "gh api user -q .login" not in START and ".vela/handle" not in START  # rule deletion: whoami does it
    assert ".vela/*" in (REPO / "template" / ".gitignore").read_text(encoding="utf-8")


# --- plain names, one definition


def test_start_forbids_codes_in_conversation_and_names_what_counts():
    plain = section("Plain names and a page a person can hold")
    for kind in ("check codes", "gate names", "capture numbers", "copy and finding IDs", "unknowns", "capabilities",
                 "contracts", "flows", "epics", "apps", "parties", "runs"):
        assert kind in plain, kind
    assert "The lead reads names, never codes." in plain
    assert '"/vela:grill Desktop agent"' in plain  # a command the lead types names the thing, not its ID
    assert "the data protection officer" in plain


def test_start_says_states_terms_and_spelling_in_words():
    plain = section("Plain names and a page a person can hold")
    for word in ("just an idea", "not decided yet", "proposed", "decided", "confirmed", '"the plan"', "the team lead",
                 "`vela terms <word>`", "American spelling", '"Summarizer"'):
        assert word in plain, word
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


def test_captures_are_numbered_by_record_add_and_keep_their_origins():
    captures = section("Captures during the session")
    assert "`vela record add --origin <who> --tag <tag>" in captures
    assert "^c01" not in captures and "never reused" not in captures  # rule deletion: record add numbers them
    assert "claude, from <name>" in captures and "promoted on a nod" in captures
    assert "`vela close stage --checkpoint`" in captures and "by exact path, never `git add -A`" in captures


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
    assert "never opening a new one" in ANSWER and "adds `grill` to the record's modes" in ANSWER


def test_answer_a_challenge_lost_its_recipe_to_session_start():
    for recipe in ("gh pr list --search", "git switch <headRefName>", "Do not run `git switch -c`",
                   "`<date>-answer-<id-lowercased>`", "E316", "senior", "Grill"):
        assert recipe not in ANSWER, recipe
    assert len(ANSWER.split()) < 200


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
