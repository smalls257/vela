"""What the lead hears about a participant's words: whose they are, when they are not confirmed as theirs yet, and how
many sentences wait at the read-back. The pull request's "In their words" names who said a quote that is not the lead's."""
import json

from conftest import run
from vela import closegate, say
import session_files
import test_close_readback as rb
from test_close_readback import RECORD, closing_vault, readback

ANA_YES = '- [quote-yes] (@cto-ana) "Yes, you can quote me." ^c10'
UNCONFIRMED = '- [thought] (@cto-ana, unverified) "Ship it on Friday." → park ^c11'


def with_ana(tmp_path, yes=True):
    vault = closing_vault(tmp_path)
    notes = session_files.record_text(vault, RECORD)
    extra = ([ANA_YES] if yes else []) + [UNCONFIRMED]
    session_files.write_private(vault, RECORD, notes.replace("\n## Changes", "\n" + "\n".join(extra) + "\n\n## Changes", 1))
    return vault


def test_picking_a_participants_confirmed_words_says_whose_they_are(tmp_path):
    vault = with_ana(tmp_path)
    code, out = readback(vault, "--pick", "^c08", "--for-lead")
    assert code == 0, out
    assert "Picked. It goes in the pull request in their words." in out and "your words" not in out
    assert say.leak_in(out) is None
    code, out = readback(vault, "--pick", "^c02", "--for-lead")
    assert code == 0 and "in your words" in out


def test_a_pick_on_unconfirmed_words_says_so_not_that_they_gave_no_yes(tmp_path):
    vault = with_ana(tmp_path)
    code, out = readback(vault, "--pick", "^c11", "--for-lead")
    assert code == 1, out
    assert "aren't confirmed as theirs yet" in out and "only with their own yes" not in out
    assert say.leak_in(out) is None
    code, detail = readback(vault, "--pick", "^c11")
    assert "vela record confirm" in detail
    no_yes = with_ana(tmp_path / "again", yes=False)
    code, out = readback(no_yes, "--pick", "^c11", "--for-lead")
    assert code == 1 and "only with their own yes" in out


def test_records_show_on_unconfirmed_words_says_so(tmp_path):
    vault = with_ana(tmp_path)
    code, out = run("records", "show", RECORD, "c11", "--vault", str(vault), "--for-lead")
    assert code == 1 and "aren't confirmed as theirs yet" in out and say.leak_in(out) is None


def test_unsorted_lines_are_never_called_the_leads():
    """One participant's lines alone are still not the lead's, so the gate never says "you said" about them."""
    mixed = ['- [thought] (@priya) "One." ^c01', '- [thought] (@cto-ana) "Two." ^c02']
    problem = closegate.unmarked_problem("## Captures\n\n" + "\n".join(mixed) + "\n")[0]
    assert problem.plain.startswith("Two things said in the session aren't sorted yet")
    alone = closegate.unmarked_problem("## Captures\n\n" + "\n".join(
        ['- [thought] (@priya) "One." ^c01', '- [thought] (@priya) "Two." ^c02']) + "\n")[0]
    assert alone.plain.startswith("Two things said in the session aren't sorted yet")


def test_the_read_back_header_is_plain_for_the_lead(tmp_path):
    vault = closing_vault(tmp_path)
    assert readback(vault, "--pick", "^c02")[0] == 0
    code, out = readback(vault, "--for-lead")
    assert out.splitlines()[0] == "One sentence to read back." and "sentence(s)" not in out
    assert "sentence(s)" in readback(vault)[1]


def test_records_show_refusal_says_it_pastes_only_the_leads_own_lines():
    """A participant who said yes is still refused by `records show`, so the refusal must not blame a missing yes."""
    from vela.commands import private_records
    assert "only with their own yes" not in private_records.NOT_THEIRS
    assert "only your own" in private_records.NOT_THEIRS and "read-back" in private_records.NOT_THEIRS
