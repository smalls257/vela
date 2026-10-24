"""vela size: show, set with the lead's reason, clear, and the line said once a session."""
import json

import yaml

import session_files
from conftest import run
from sizing_vault import write_plan
from vela import privaterecord, sizing

RECORD_ID = "2026-10-23-grill-jobs"
CAPTURE = '- [answer] (@dana) "It is bigger than it looks; Platform adds a third app next month." ^c14'


def open_session(root, captures=(CAPTURE,), stub_extra=None):
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-23", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-23 Grill: jobs", "", "## Captures", "", *captures, ""]
    session_files.write_record(root, RECORD_ID, "\n".join(lines) + "\n")


def small(tmp_path):
    return write_plan(tmp_path, apps=[("scheduler", "new"), ("jobs-api", "new")], capabilities=["new"],
                      releases=["2027-01-15"])


def test_show_says_the_band_and_its_counts(tmp_path):
    code, out = run("size", "--vault", str(small(tmp_path)))
    assert code == 0 and out.startswith("vela size: small (measured small; apps 2, capabilities 1, releases 1)")
    data = json.loads(run("size", "--vault", str(tmp_path), "--json")[1])
    assert data["band"] == "small" and [s["name"] for s in data["signals"]] == ["apps", "capabilities", "releases"]


def test_set_records_the_band_and_the_leads_reason(tmp_path):
    root = small(tmp_path)
    open_session(root)
    code, out = run("size", "set", "medium", "--because", "^c14", "--vault", str(root), "--today", "2026-10-23")
    assert code == 0, out
    config = yaml.safe_load((root / ".vela.yaml").read_text(encoding="utf-8"))
    assert config["size"] == {"band": "medium", "because": f"[[{RECORD_ID}]] c14", "date": "2026-10-23"}
    assert config["title"] == "Scheduled jobs"


def test_set_without_a_reason_on_record_asks_for_it_and_writes_nothing(tmp_path):
    root = small(tmp_path)
    open_session(root)
    before = (root / ".vela.yaml").read_text(encoding="utf-8")
    code, out = run("size", "set", "medium", "--because", "^c99", "--vault", str(root), "--today", "2026-10-23")
    assert code == 3 and (root / ".vela.yaml").read_text(encoding="utf-8") == before


def test_clear_goes_back_to_measuring(tmp_path):
    root = small(tmp_path)
    open_session(root)
    run("size", "set", "large", "--because", "^c14", "--vault", str(root), "--today", "2026-10-23")
    assert run("size", "clear", "--vault", str(root))[0] == 0
    assert "size" not in yaml.safe_load((root / ".vela.yaml").read_text(encoding="utf-8"))


def test_config_edits_keep_every_other_line():
    text = "initiative: INI-001\n# the name the dashboard shows\ntitle: Scheduled jobs\n"
    chosen = sizing.config_with_choice(text, sizing.Choice("medium", f"[[{RECORD_ID}]] c14", "2026-10-23"))
    assert "# the name the dashboard shows" in chosen
    assert sizing.config_without_choice(chosen) == text


def test_announce_says_it_once_and_records_it_on_the_open_stub(tmp_path):
    root = small(tmp_path)
    open_session(root)
    code, out = run("size", "announce", "--vault", str(root), "--for-lead")
    assert code == 0 and "I'm treating this as a small plan" in out
    meta = privaterecord.stub_meta(session_files.stub_text(root, RECORD_ID))
    assert meta["size"] == "small; apps 2, capabilities 1, releases 1"
    assert run("size", "announce", "--vault", str(root), "--for-lead")[1].strip() == ""


GROWN_STUB = {"id": "2026-10-01-grill-a", "status": "closed", "size": "small; apps 2, capabilities 1, releases 1"}


def test_the_growth_line_comes_first_so_the_four_line_cap_never_hides_it(tmp_path):
    # Recorded as said but cut into "N more; want them?" would mean the lead never heard it (a Black Box).
    apps = [(s, "new") for s in ("scheduler", "jobs-api", "audit", "billing", "mailer")]
    root = write_plan(tmp_path, apps=apps, capabilities=["new"], releases=["2027-01-15"], stubs=[GROWN_STUB])
    open_session(root)
    items = [arg for slug, _ in apps for arg in ("--item", f"APP-{slug}")]
    code, out = run("check", "--vault", str(root), "--gate", "grill", *items, "--for-lead")
    assert "The plan has grown" in out, out
    assert "The plan has grown" in out.splitlines()[0] or "The plan has grown" in out.split("more;")[0], out
    meta = privaterecord.stub_meta(session_files.stub_text(root, RECORD_ID))
    assert meta["size"].startswith("medium")
