"""A GitHub login may hold an underscore: an Enterprise Managed User's login is `name_shortcode`. Vela once had six
handle patterns, and none allowed it, so `vela whoami --set jane_acme` refused and a page owned by @jane_acme read
as owned by @jane. Every pattern is now built from schema.HANDLE_NAME; these tests hold each user of it to that."""
import re

from vela import onboardpath, override, prbody, schema
from vela.decisions import add_epic
from vela.explorer import asks_data

EMU = "jane_acme"


def test_a_managed_user_login_is_a_handle_everywhere():
    assert onboardpath.HANDLE.match(EMU)
    assert re.fullmatch(schema.HANDLE, "@" + EMU) and schema.OWNER_RE.match(f"@{EMU} @sam")
    assert override.DECIDED_BY_RE.match(f"@{EMU}").group("by") == "@" + EMU
    assert add_epic.HANDLE_IN.findall(f"owned by @{EMU}.") == ["@" + EMU]
    assert asks_data.HANDLE.findall(f"ask @{EMU} first") == ["@" + EMU]
    assert prbody._HANDLE.findall(f"@{EMU}") == ["@" + EMU]


def test_what_is_not_a_login_stays_out():
    for bad in ("_jane", "-jane", "jane/../x", "sam\n", "x" * 40, ""):
        assert not onboardpath.HANDLE.match(bad), bad
