"""The complexity waiver file: its format, the delete-only rule and expiry. Pure; no git, no lizard."""
import datetime
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import quality_waivers

HEAD = "# seeded 2026-10-27 at 4dfa3eb0 by smalls257: pre-gate debt\n"
LINE = "plugin/lib/vela/reading.py::style_problems\tccn=59 nloc=80\tsmalls257\t2027-04-27\tover the cap when the gate arrived\n"


def test_round_trip_keeps_every_field():
    found = quality_waivers.parse_waivers(HEAD + LINE)
    w = found["plugin/lib/vela/reading.py::style_problems"]
    assert w.limits == {"ccn": 59, "nloc": 80} and w.owner == "smalls257" and w.expires == datetime.date(2027, 4, 27)
    assert quality_waivers.format_waivers(found.values(), HEAD.strip()).endswith(LINE)


@pytest.mark.parametrize("bad", ["x\tccn=1\tsmalls257\t2027-04-27\n", "x\tccn=1\t\t2027-04-27\twhy\n",
                                 "x\tccn=1\tsmalls257\t27-04-2027\twhy\n", "x\tfoo=1\tsmalls257\t2027-04-27\twhy\n",
                                 "x\tccn=z\tsmalls257\t2027-04-27\twhy\n", LINE + LINE])
def test_malformed_lines_name_their_line(bad):
    with pytest.raises(quality_waivers.WaiverFileError, match=r"line \d"):
        quality_waivers.parse_waivers(HEAD + bad)


def test_blank_and_crlf_lines_are_tolerated():
    assert len(quality_waivers.parse_waivers(HEAD + "\n" + LINE.replace("\n", "\r\n"))) == 1


def test_an_added_or_raised_line_is_caught_but_a_reseed_is_not():
    raised = LINE.replace("ccn=59", "ccn=61")
    assert quality_waivers.added_entries(HEAD + LINE, HEAD + raised) == [raised.strip()]
    assert quality_waivers.added_entries(HEAD + LINE, HEAD) == []  # deleting is fine
    reseed = "# seeded 2026-11-03 at 1234abcd by smalls257: re-seed after easy-settle merged\n"
    assert quality_waivers.added_entries(HEAD + LINE, reseed + raised) == []


def test_expired_waivers_and_todos():
    w = quality_waivers.parse_waivers(HEAD + LINE)
    assert quality_waivers.expired(w.values(), datetime.date(2027, 4, 27)) == []
    assert len(quality_waivers.expired(w.values(), datetime.date(2027, 4, 28))) == 1
    marker = "TO" + "DO"  # built at run time so a repo-wide grep for dated markers does not find this test
    found = quality_waivers.expired_todos([f"tools/x.py:3:# {marker}(smalls257, 2026-10-01): drop the old flag"],
                                          datetime.date(2026, 10, 27))
    assert found[0].path == "tools/x.py" and found[0].line == 3 and "expired on 2026-10-01" in found[0].message
