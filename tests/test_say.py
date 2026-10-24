"""The output layer every new command relays through (overhaul Task 2): `--for-lead` resolves IDs to names and raises
on a leak, so a line meant for the lead can't carry a code or an ID (Leaky Narrative, fixed at the interface)."""
import argparse
import io
import re

import pytest

from conftest import REPO, run
from vela import cli, commands, model, say

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"


def test_for_lead_never_prints_a_code_or_id():
    code, out = run("check", "--vault", str(HERON), "--today", "2026-10-14", "--for-lead", "--more")
    assert code in (0, 1), out
    assert "vela bug" not in out
    for kind, pattern in say.LEAD_PATTERNS.items():
        assert not pattern.search(out), (kind, pattern.search(out).group(0))
    assert not re.search(r"\b[EWT]\d{3}\b|\bUNK-\d|\bCON-\d|\bFLO-\d|Fix:", out)
    assert "Calendar entries doesn't list what it returns when a call fails" in out  # the name, not "(CON-001)"


def test_for_lead_formatter_raises_on_a_leak(monkeypatch):
    """A leak is a vela bug: exit 2, naming the command, never a quiet code in front of the lead."""
    monkeypatch.setattr(cli, "check_lead_header", lambda *a: "E316 is open; see sessions/2026-10-14-consent.md")
    code, out = run("check", "--vault", str(HERON), "--today", "2026-10-14", "--for-lead")
    assert code == 2
    assert "vela bug: a line meant for the lead held an ID" in out and "`vela check --for-lead`" in out


def test_emit_raises_on_an_explicit_plain_line_that_leaks():
    result = say.Result("demo", lines=[say.Line("UNK-001 open", plain="Edit 01-goals.md to close it")])
    with pytest.raises(say.LeadLeak) as caught:
        commands.emit(result, argparse.Namespace(for_lead=True, json=False), io.StringIO())
    assert caught.value.command == "demo" and caught.value.kind == "file path"


def test_finding_id_prints_area_and_question():
    from vela.catalog import Catalog
    vault = model.Vault(config={}, pages=[], catalog=Catalog(1, (("DAT", "Data and lawful basis"),), ()))
    resolver = say.Resolver(vault, findings={"F1.4": ("DAT", "how long consent records are kept")})
    assert resolver.plain("F1.4 is still open") == "the data reviewer asked how long consent records are kept is still open"
    assert "F2.1" not in resolver.plain("F2.1 waits") and "reviewer" in resolver.plain("F2.1 waits")


def test_ids_with_no_name_are_said_by_their_kind_and_captures_by_what_they_are():
    resolver = say.Resolver()
    said = resolver.plain("UNK-009 blocks CON-004, from ^c12; copy Q-FIN-03@SV-01; row R-DAT-10; GATE-4 overridden")
    assert say.leak_in(said) is None, said
    assert "an open question" in said and "a contract" in said and "a note in the session record" in said
    assert "the open-question check" in said


def test_refusal_carries_plain_fix_and_override_and_for_lead_prints_only_plain():
    refusal = say.Refusal("GATE-4", "Nobody has said who owns the consent records yet.", "Ask the lead.",
                          "vela apply ... (rule GATE-4)")
    result = say.Result("demo", exit=say.REFUSED, refusals=[refusal])
    assert refusal.as_json() == {"refused": True, "rule": "GATE-4", "plain": refusal.plain, "fix": "Ask the lead.",
                                 "override": "vela apply ... (rule GATE-4)", "audience": say.LEAD, "recommend": ""}
    assert say.render(result, "for-lead") == "Nobody has said who owns the consent records yet.\n" + say.WAIVE_ONE
    assert "Override: vela apply" in say.render(result, "default")


def test_exit_3_means_nothing_changed():
    """Exit 3 promises the lead that nothing changed and that the choices are listed; `render` holds both promises."""
    asked = say.Result("demo", exit=say.NEEDS_LEAD, needs_lead=[{"choose": "which session"}])
    assert '"needs_lead"' in say.render(asked, "json")
    with pytest.raises(ValueError, match="nothing changed"):
        say.render(say.Result("demo", exit=say.NEEDS_LEAD, needs_lead=[{"x": 1}], wrote=["sessions/a.md"]), "json")
    with pytest.raises(ValueError, match="without saying what the lead must choose"):
        say.render(say.Result("demo", exit=say.NEEDS_LEAD), "default")


def test_the_leak_check_catches_the_plumbing_the_voice_audit_found():
    """Each line passed the old check (codes and IDs only) and reached a lead in the October 14 runs."""
    leaks = {
        "session slug": "Calling this one 2026-10-14-calendar-entries.",
        "git error": "GitHub's command line failed (none of the git remotes configured for this repository point to "
                     "a known GitHub host; run gh auth login)",
        "command": "Run `vela session start` to bring it in.",
        "file path": "The text is in `.vela/pr-body.md`.",
        "branch": "Your branch session/x is 3 commits behind the shared plan (origin/main).",
        "flag": "Build it with --for-lead first.",
        "ISO date": "I've set it to be asked by 2027-02-02.",
        "handle": "@agent-lead owns no app pages.",
        "commit hash": "Your copy is the latest published (a1b2c3d, October 14).",
    }
    for kind, line in leaks.items():
        assert say.leak_in(line) is not None and say.leak_in(line)[0] in (kind, "session slug", "git error"), (kind, line)
    for fine in ("vela needs 3.9 or later.", "Open dashboard.html in this folder.", "Ask by October 14, read/write.",
                 "/vela:explore opens it.", "Vela's own words are grill, slice and tracer."):
        assert say.leak_in(fine) is None, fine


def test_the_command_pattern_knows_every_subcommand():
    import argparse as ap
    parser = cli.build_parser()
    names = next(a for a in parser._actions if isinstance(a, ap._SubParsersAction)).choices
    for name in names:
        assert say.LEAD_PATTERNS["command"].search(f"run vela {name} now"), name


def test_the_resolver_says_dates_handles_and_page_files_in_words():
    import datetime
    resolver = say.Resolver(today=datetime.date(2026, 10, 14))
    assert resolver.plain("due 2026-11-03, with @solution-lead") == "due November 3, with solution lead"
    assert resolver.plain("due 2027-02-02") == "due February 2, 2027"
    assert resolver.plain("start it with /vela:design --app APP-x.") == "start it with /vela:design."
    assert resolver.plain("in the lead's own words") == "in your own words"


def test_the_lead_hears_the_answer_then_about_four_then_how_many_more():
    lines = [say.Line(f"item {n}", plain=f"Thing {n} needs you.") for n in range(1, 8)]
    result = say.Result("demo", exit=say.REFUSED, lines=lines + [lines[0]], answer="Seven things hold it up.")
    said = say.render(result, "for-lead").splitlines()
    assert said[0] == "Seven things hold it up." and said[1:5] == [f"Thing {n} needs you." for n in range(1, 5)]
    assert said[5] == "Three more; want them?" and len(said) == 6  # the repeated line is said once
    assert say.render(result, "for-lead", more=True).splitlines()[-1] == "Thing 7 needs you."
    assert say.render(result, "default").count("item 1") == 2  # the default keeps every line as given
    one_more = say.Result("demo", lines=lines[:5])
    assert "more; want them" not in say.render(one_more, "for-lead")  # "one more" costs as much as reading it


def test_refusals_by_audience_and_the_way_out_said_once():
    model = say.Refusal("decide-by", "I need your handle.", "run vela whoami", "none: a decision names who",
                        audience=say.MODEL)
    lead = [say.Refusal("GATE-4", f"Question {n} is open.", "Ask.", "an override", recommend="I'd ask the owner.")
            for n in (1, 2)]
    said = say.render(say.Result("demo", exit=say.REFUSED, refusals=[model, *lead]), "for-lead")
    assert "handle" not in said  # the model's slip never reaches the lead
    assert "Question 1 is open. I'd ask the owner." in said  # each of the lead's carries my recommendation
    assert said.count("set aside") == 1 and said.splitlines()[-1] == say.WAIVE_MANY
    alone = say.render(say.Result("demo", exit=say.REFUSED, refusals=[model]), "for-lead")
    assert alone == say.MY_SIDE  # an exit 1 is never silent, and never the slip itself
    assert "I need your handle" in say.render(say.Result("demo", exit=say.REFUSED, refusals=[model]), "default")
    hidden = say.Line("hooks note", plain="Hooks did not run.", audience=say.MODEL)
    assert say.render(say.Result("demo", lines=[hidden]), "for-lead") == ""


def test_main_says_what_each_exit_code_means():
    doc = cli.main.__doc__
    for line in ("0  done.", "1  refused", "2  the tool failed", "3  needs the lead: nothing changed"):
        assert line in doc


def test_date_words_put_the_month_first_and_the_year_only_when_it_is_not_this_one():
    import datetime
    today = datetime.date(2026, 10, 14)
    assert say.date_words("2026-10-14", today) == "October 14"
    assert say.date_words("2027-02-02", today) == "February 2, 2027"
    assert say.date_words("2026-10-14") == "October 14, 2026"
    assert say.date_words("not a date", today) == "not a date"


def test_date_words_with_a_weekday_keeps_the_same_order():
    import datetime
    today = datetime.date(2026, 10, 14)
    assert say.date_words_with_weekday("2027-02-02", today) == "Tuesday, February 2, 2027"
    assert say.date_words_with_weekday("2026-10-14", today) == "Wednesday, October 14"
    assert say.date_words_with_weekday("soon", today) == "soon"


def test_the_session_date_helper_and_the_override_question_use_the_same_order():
    import datetime
    from vela import sessions
    from vela.decisions import override
    assert sessions.date_in_words("2026-10-14", datetime.date(2026, 1, 1)) == "October 14"
    assert sessions.date_in_words("2027-02-02", datetime.date(2026, 1, 1)) == "February 2, 2027"
    assert override._said("2026-12-01") == "December 1"


# --- a refusal names its fix (the October 22 trim): the skills dropped their per-command exit-code ladders because
# every refusal carries a `fix`, so a refusal built with no fix, an empty one or a one-word one would leave the model
# with neither the skill's recovery path nor the command's.

def _refusal_fixes():
    """(file, line, fix expression) for every `Refusal(...)` in the program whose fix is written out in place."""
    import ast
    found = []
    for path in sorted((REPO / "plugin" / "lib" / "vela").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name != "Refusal":
                continue
            fix = node.args[2] if len(node.args) >= 3 else next((k.value for k in node.keywords if k.arg == "fix"), None)
            found.append((path.name, node.lineno, fix))
    return found


def test_every_refusal_is_built_with_a_fix_that_says_what_to_do():
    import ast
    refusals = _refusal_fixes()
    assert len(refusals) >= 40, len(refusals)
    for name, line, fix in refusals:
        assert fix is not None, f"{name}:{line} has no fix"
        if isinstance(fix, ast.Constant):  # a literal: a variable or an f-string is built from a reason the test can't see
            assert isinstance(fix.value, str) and len(fix.value.split()) >= 3, f"{name}:{line} fix is {fix.value!r}"


def test_no_session_open_says_how_to_start_one(tmp_path):
    """The gap the trim found: `vela decide` (via apply's record lookup) said there was nothing to file into and
    stopped, so the skill's "start a session" sentence was the only place that said what to run."""
    from vela.commands import apply
    import shutil
    vault = tmp_path / "ub"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    _, result = apply.find_record(vault)
    assert result is not None and "vela session start" in result.lines[0].text
