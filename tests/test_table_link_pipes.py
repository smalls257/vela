"""A [[link|label]] in a table row: its pipe is the link's, never a column break, and W329 asks for \\|."""
import sys
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugin" / "lib"))

from vela import rules  # noqa: E402
from vela.cli import load_vault  # noqa: E402
from vela.explorer.pages_data import cells  # noqa: E402
from vela.parse import split_row  # noqa: E402

# The shape a sim session wrote on a constraints page: one link escaped, one bare, in the same cell.
ROW = "| CST-1 | Demo in January | The board, as [[a#^c05\\|it reports]]; [[sources#SRC-09|the later note]] says | Fixes it |"


def test_a_bare_link_pipe_stays_in_its_cell_for_the_checker():
    assert split_row(ROW) == ("CST-1", "Demo in January", "The board, as [[a#^c05|it reports]]; [[sources#SRC-09|the later note]] says",
                              "Fixes it")


def test_a_bare_link_pipe_stays_in_its_cell_for_the_explorer():
    assert cells(ROW) == ["CST-1", "Demo in January", "The board, as [[a#^c05|it reports]]; [[sources#SRC-09|the later note]] says",
                          "Fixes it"]


def test_w329_names_each_bare_link_pipe_in_a_real_vault_and_no_escaped_one():
    # after-capture-boundary was written by real sessions: its constraints table mixes \| and bare | in one cell
    vault = load_vault(REPO / "tests" / "sim" / "snapshots" / "trading-coach" / "after-capture-boundary")
    found = [f for f in rules.link_pipe_rules(vault, None) if f.path.endswith("02-constraints.md")]
    assert found and all(f.code == "W329" for f in found)
    assert any("[[sources#SRC-09|the CEO's later note]]" in f.message for f in found)
    assert not any("\\|" in f.message.split(" in a table row")[0] for f in found)
