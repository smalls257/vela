"""OPS-02 is read back from the consumer's runtime page; the case table never answers it."""
import shutil

from conftest import REPO
from vela import cli, questions, say
from vela.commands.questions import lead_digest

FIXTURE = REPO / "tests" / "fixtures" / "small-two-apps"
RUNTIME = "06-runtime/apps/jobs-api-runtime.md"  # the template's folder, so the explorer groups it
FAILURE = ("---\nid: RUN-jobs-api\ntype: app-runtime\ntitle: Jobs API runtime\nstate: assumption\nowner: \"@mo\"\n"
           "authored: authored\n---\n\n# Jobs API runtime\n\n## On failure\n\nWhen [[scheduler-building-blocks#CON-001 "
           "Job due|Job due]] doesn't arrive by the time a job was due, the Jobs API marks it missed and tells the caller.\n")


def ops02(vault):
    return next(d for d in questions.dispositions(vault) if d.copy.id == "Q-OPS-02@CON-001")


def test_a_case_table_alone_answers_nothing():
    vault = cli.load_vault(FIXTURE)
    assert questions.failure_answers(vault, ops02(vault).copy) == ()


def test_a_runtime_answer_is_read_back_not_filed(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(FIXTURE, root)
    (root / RUNTIME).parent.mkdir(exist_ok=True)
    (root / RUNTIME).write_text(FAILURE, encoding="utf-8")
    vault = cli.load_vault(root)
    assert questions.failure_answers(vault, ops02(vault).copy) == ("jobs-api-runtime#On failure",)
    assert ops02(vault).pending, "the lead still says yes; vela files nothing"
    group = next(g for g in questions.digest(vault)["groups"] if g["entry"] == "Q-OPS-02")
    assert group["on_page"] == ["jobs-api-runtime#On failure"]


def test_the_lead_hears_a_read_back(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(FIXTURE, root)
    (root / RUNTIME).parent.mkdir(exist_ok=True)
    both = FAILURE + ("\nWhen [[jobs-api-building-blocks#CON-002 Event bus|Event bus]] is down, the Jobs API keeps the "
                      "finished jobs and sends them when the bus is back.\n")
    (root / RUNTIME).write_text(both, encoding="utf-8")
    vault = cli.load_vault(root)
    groups = [g for g in questions.digest(vault)["groups"] if g["entry"] == "Q-OPS-02"]
    result = lead_digest({"groups": groups, "held": 0, "shown": []}, dict(vault.catalog.areas))
    text = say.render(result, "for-lead", say.Resolver(vault), more=True)
    line = next(l for l in text.splitlines() if "runtime pages already say" in l)
    assert line.endswith("Is that the answer?") and "Job due" in line and "Event bus" in line
    assert "CON-" not in line
