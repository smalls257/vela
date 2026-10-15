"""`vela boundary cover --cut FILE` (overhaul Task 21g): per cut, the requirements one app carries whole, the ones
split across apps (so a contract is needed), and the ones no app carries. The vault is the Heron plan fixture, read
only; its nine requirements sit under five capabilities (CAP-001 to CAP-005)."""
import json

from conftest import REPO, run
from vela import boundarycover, say

HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron-plan"

ONE_AGENT = {"name": "One desktop agent", "apps": [
    {"name": "Desktop agent", "change": "new", "carries": ["CAP-001", "CAP-002", "CAP-003", "CAP-004.FR1"]},
    {"app": "APP-consent-and-identity", "change": "integrated", "carries": ["CAP-005.FR1"]},
]}
WITH_SUMMARIZER = {"name": "Agent and a cloud summarizer", "apps": [
    {"name": "Desktop agent", "change": "new", "carries": ["CAP-001", "CAP-002", "CAP-003.FR1", "CAP-005"]},
    {"name": "Summarizer", "change": "new", "carries": ["CAP-003", "CAP-004"]},
    {"app": "APP-consent-and-identity", "change": "integrated", "carries": ["CAP-005"]},
]}


def cut_file(tmp_path, *cuts, version=1):
    path = tmp_path / "cuts.json"
    path.write_text(json.dumps({"version": version, "cuts": list(cuts)}), encoding="utf-8")
    return str(path)


def cover(tmp_path, *cuts, mode=()):
    return run("boundary", "cover", "--cut", cut_file(tmp_path, *cuts), "--vault", str(HERON), *mode)


def test_cover_whole_split_uncarried(tmp_path):
    code, out = cover(tmp_path, ONE_AGENT, mode=("--json",))
    assert code == 0, out
    (only,) = json.loads(out)["cuts"]
    whole = {row["requirement"]: row["app"] for row in only["whole"]}
    assert whole["CAP-001.FR1"] == "Desktop agent"  # a capability named on an app carries each of its requirements
    assert whole["CAP-004.FR1"] == "Desktop agent"
    assert whole["CAP-005.FR1"] == "Consent and identity"  # an existing app is said by its page's title
    assert only["split"] == []
    assert only["uncarried"] == ["CAP-005.FR2"]

    code, out = cover(tmp_path, WITH_SUMMARIZER, mode=("--json",))
    (cut,) = json.loads(out)["cuts"]
    split = {row["requirement"]: row["apps"] for row in cut["split"]}
    assert split["CAP-003.FR1"] == ["Desktop agent", "Summarizer"]
    assert split["CAP-005.FR2"] == ["Desktop agent", "Consent and identity"]
    assert "CAP-003.FR2" in {row["requirement"] for row in cut["whole"]}
    assert cut["uncarried"] == []

    code, out = cover(tmp_path, ONE_AGENT)  # default mode keeps the IDs, for files and the PR body
    assert code == 0
    assert "CAP-005.FR2" in out and "carried by no app" in out


def test_bad_cut_file_refused_plainly(tmp_path):
    def refused(text, said):
        path = tmp_path / "bad.json"
        path.write_text(text, encoding="utf-8")
        code, out = run("boundary", "cover", "--cut", str(path), "--vault", str(HERON))
        assert code == 1, out
        assert said in out, out
        assert "Traceback" not in out

    refused("{not json", "is not JSON")
    refused(json.dumps({"version": 2, "cuts": [ONE_AGENT]}), "version 1")
    refused(json.dumps({"version": 1, "cuts": []}), "at least one cut")
    unknown = {"name": "Typo", "apps": [{"name": "Agent", "carries": ["CAP-009.FR1"]}]}
    refused(json.dumps({"version": 1, "cuts": [unknown]}), "CAP-009.FR1")
    no_app = {"name": "Ghost", "apps": [{"app": "APP-nowhere", "carries": []}]}
    refused(json.dumps({"version": 1, "cuts": [no_app]}), "APP-nowhere")
    twice = {"name": "Twice", "apps": [{"name": "Agent", "carries": []}, {"name": "agent", "carries": []}]}
    refused(json.dumps({"version": 1, "cuts": [twice]}), "twice")
    coded = {"name": "Cut with CAP-001 in its name", "apps": [{"name": "Agent", "carries": []}]}
    refused(json.dumps({"version": 1, "cuts": [coded]}), "in words")
    code, out = run("boundary", "cover", "--cut", str(tmp_path / "missing.json"), "--vault", str(HERON))
    assert code == 1 and "no file" in out.lower()


def test_two_cuts_compared(tmp_path):
    code, out = cover(tmp_path, ONE_AGENT, WITH_SUMMARIZER, mode=("--json",))
    assert code == 0
    first, second = json.loads(out)["cuts"]
    assert (first["name"], second["name"]) == (ONE_AGENT["name"], WITH_SUMMARIZER["name"])
    assert (len(first["whole"]), len(first["split"]), len(first["uncarried"])) == (8, 0, 1)
    assert (len(second["whole"]), len(second["split"]), len(second["uncarried"])) == (6, 3, 0)
    code, out = cover(tmp_path, ONE_AGENT, WITH_SUMMARIZER)
    summary = [line for line in out.splitlines() if line.startswith("- ")]
    assert summary == ["- One desktop agent: 8 whole, 0 split, 1 carried by no app.",
                       "- Agent and a cloud summarizer: 6 whole, 3 split, 0 carried by no app."]


def test_for_lead_passes_the_leak_check(tmp_path):
    code, out = cover(tmp_path, ONE_AGENT, WITH_SUMMARIZER, mode=("--for-lead",))
    assert code == 0, out
    for line in out.splitlines():
        assert say.leak_in(line) is None, line
    assert "Stop reading when a withdrawal is not confirmed" in out  # the requirement said by its name
    assert "Consent and identity" in out


def test_pure_core_needs_no_vault():
    requirements = {"CAP-001.FR1": "Read", "CAP-001.FR2": "Write", "CAP-002.FR1": "Send"}
    cuts = boundarycover.parse_cut(json.dumps({"version": 1, "cuts": [
        {"name": "Two", "apps": [{"name": "A", "carries": ["CAP-001"]}, {"name": "B", "carries": ["CAP-001.FR2"]}]}]}),
        requirements, {})
    (coverage,) = boundarycover.cover(cuts, list(requirements))
    assert coverage.whole == (("CAP-001.FR1", "A"),)
    assert coverage.split == (("CAP-001.FR2", ("A", "B")),)
    assert coverage.uncarried == ("CAP-002.FR1",)


def test_vault_without_requirements_says_so(tmp_path):
    code, out = run("boundary", "cover", "--cut", cut_file(tmp_path, ONE_AGENT),
                    "--vault", str(REPO / "tests" / "fixtures" / "mini"))
    assert code == 1
    assert "no functional requirements" in out
