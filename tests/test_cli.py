import subprocess
import sys

from conftest import MINI, REPO, check, edit, findings, run


def test_mini_vault_is_clean(mini):
    code, out = check(mini)
    assert code == 0, out
    assert findings(out) == []
    assert out.splitlines()[0].startswith("planner check: 0 errors, 0 warnings in 12 pages. Today is 2026-01-15 (--today).")


def test_system_date_is_printed_when_no_today_given(mini):
    code, out = run("check", "--vault", str(mini))
    assert "(system date)" in out.splitlines()[0]


def test_findings_exit_1_and_name_a_fix(mini):
    edit(mini / "README.md", "authored: authored", "authored: by hand")
    code, out = check(mini)
    assert code == 1
    assert findings(out) == [("E105", "README.md")]
    assert out.splitlines()[1].startswith("README.md:5: E105 ")
    assert " Fix: Use one of: authored, generated, mixed." in out.splitlines()[1]


def test_no_config_is_tool_failure(tmp_path):
    code, out = run("check", "--vault", str(tmp_path))
    assert code == 2
    assert "no .planner.yaml" in out


def test_bad_today_is_tool_failure(mini):
    code, out = run("check", "--vault", str(mini), "--today", "15/01/2026")
    assert code == 2
    assert "--today" in out


def test_bad_arguments_are_tool_failure():
    assert run("frobnicate")[0] == 2


def test_check_writes_nothing(mini):
    before = {p: p.read_bytes() for p in mini.rglob("*") if p.is_file()}
    edit(mini / "README.md", "authored: authored", "authored: by hand")
    before[mini / "README.md"] = (mini / "README.md").read_bytes()
    check(mini)
    after = {p: p.read_bytes() for p in mini.rglob("*") if p.is_file()}
    assert before == after


def test_bin_planner_runs_without_install():
    result = subprocess.run([sys.executable, str(REPO / "plugin" / "bin" / "planner"), "check",
                             "--vault", str(MINI), "--today", "2026-01-15"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("planner check: 0 errors")
