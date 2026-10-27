"""closefinish: the sentences close finish and close dashboard say. A no-session dashboard asks nothing and makes no
branch, so its one line says only that it goes in with the next session."""
from vela import closefinish


def test_the_no_session_dashboard_line_names_no_branch():
    assert closefinish.NO_SESSION_DASHBOARD == "I've updated the dashboard; it goes in with your next session."
    assert "branch" not in closefinish.DASHBOARD_DONE


def test_there_is_no_put_back_sentence():
    assert not hasattr(closefinish, "DASHBOARD_PUT_BACK")
