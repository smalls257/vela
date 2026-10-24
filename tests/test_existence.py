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
