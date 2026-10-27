"""closefinish: the sentences close finish and close dashboard say. A no-session dashboard asks nothing, so there is no
sentence offering its branch."""
from vela import closefinish


def test_the_no_session_dashboard_offers_no_branch():
    assert not hasattr(closefinish, "NO_SESSION_DASHBOARD")
    assert "branch" not in closefinish.DASHBOARD_DONE


def test_putting_the_dashboard_back_is_still_said_plainly():
    assert closefinish.DASHBOARD_PUT_BACK.startswith("I've left the dashboard as it was")
