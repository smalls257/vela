"""The six existence questions: one read-back, numbered, a no recommended only on evidence."""
import json

from conftest import REPO, run
from sizing_vault import from_template
from vela import cli, questions

SIX = ["Q-FIN-01", "Q-DAT-01", "Q-DAT-05", "Q-PTN-01", "Q-REG-01", "Q-REG-02"]


def test_a_new_plan_has_six_lines_in_catalog_order(tmp_path):
    lines = questions.existence_lines(cli.load_vault(from_template(tmp_path)))
    assert [l.copy.split("@")[0] for l in lines] == SIX


def test_no_is_recommended_only_where_the_plan_has_evidence():
    vault = cli.load_vault(REPO / "tests" / "fixtures" / "small-two-apps")
    recommended = {l.copy.split("@")[0]: l.recommend for l in questions.existence_lines(vault)}
    # the bus is an outside provider, so nothing that creates a party gets a recommended no
    assert recommended == {"Q-FIN-01": "no", "Q-DAT-01": "", "Q-DAT-05": "", "Q-PTN-01": "",
                           "Q-REG-01": "", "Q-REG-02": ""}


def test_for_lead_says_all_six_in_one_turn(tmp_path):
    root = from_template(tmp_path)
    code, out = run("questions", "--existence", "--for-lead", "--vault", str(root))
    assert code == 0 and all(f"{n}." in out for n in range(1, 7)) and "more; want them?" not in out


def test_json_lists_each_copy_with_its_recommendation(tmp_path):
    data = json.loads(run("questions", "--existence", "--json", "--vault", str(from_template(tmp_path)))[1])
    assert [d["copy"].split("@")[0] for d in data["lines"]] == SIX


def test_each_recommended_no_gives_its_own_reason(tmp_path):
    # FIN-01's evidence is a stored value; DAT-01's is a party. One shared reason would misstate one of them.
    out = run("questions", "--existence", "--for-lead", "--vault", str(from_template(tmp_path)))[1]
    assert f"{questions.NO_STORED_VALUE}; and to" in out and questions.NO_PARTY in out, out
    assert out.count(questions.NO_STORED_VALUE) == 1 and out.count(questions.NO_PARTY) == 1


def test_one_shared_reason_is_said_once():
    from vela.commands import questions as command
    same = [questions.ExistenceLine("Q-FIN-01@INI-001", "?", "no", "r"), questions.ExistenceLine("Q-DAT-01@INI-001", "?", "no", "r")]
    assert command.recommended_noes(same) == " I'd say no to 1 and 2: r."
    assert command.recommended_noes([questions.ExistenceLine("Q-FIN-01@INI-001", "?", "", "")]) == ""
