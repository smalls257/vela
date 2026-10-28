"""The quality gate command and its seed script, run against a tmp git repo so no real file is judged."""
import datetime
import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import quality_complexity
import quality_gate
import quality_seed
import quality_waivers

BRANCHY = "def tangled(a):\n" + "".join(f"    if a == {i}:\n        return {i}\n" for i in range(13)) + "    return -1\n"
SEEDED = "# seeded 2026-10-27 at 4dfa3eb0 by smalls257: pre-gate debt\n"
WAIVER = "tools/x.py::tangled\tccn=14\tsmalls257\t2027-04-27\tover the cap when the gate arrived\n"
TODAY = ["--today", "2026-10-27"]

pytestmark = pytest.mark.skipif(quality_gate.shutil.which("lizard") is None, reason="lizard is not installed")


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@x", *args],
                   check=True, capture_output=True, timeout=30)


def repo(tmp_path, source=BRANCHY, waivers=SEEDED):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/x.py").write_text(source, encoding="utf-8")
    if waivers is not None:
        (tmp_path / ".quality").mkdir()
        (tmp_path / ".quality/complexity-waivers.tsv").write_text(waivers, encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def test_an_unwaived_function_over_cap_fails(tmp_path, capsys):
    root = repo(tmp_path)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 1
    out = capsys.readouterr().out
    assert "QG-CPX" in out and "tools/x.py::tangled" in out


def test_a_waived_function_passes(tmp_path):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 0


def test_missing_waiver_file_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, waivers=None)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    assert "could not run" in capsys.readouterr().err


def test_missing_lizard_cannot_run(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path)
    monkeypatch.setattr(quality_gate.shutil, "which", lambda name: None)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    assert "lizard is not installed" in capsys.readouterr().err


def test_unparseable_file_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, source="def f(:\n")
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    assert "tools/x.py" in capsys.readouterr().err


def test_a_staged_added_waiver_line_fails(tmp_path, capsys):
    root = repo(tmp_path)
    (root / ".quality/complexity-waivers.tsv").write_text(SEEDED + WAIVER, encoding="utf-8")
    git(root, "add", ".quality/complexity-waivers.tsv")
    assert quality_gate.main(["--staged", *TODAY], root) == 1
    assert "added outside a reseed" in capsys.readouterr().out


def test_full_mode_without_a_base_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    assert quality_gate.main(TODAY, root) == 2
    assert "no base" in capsys.readouterr().err
    assert quality_gate.main(["--base", "", *TODAY], root) == 2


def test_a_renamed_waived_function_says_reseed(tmp_path, capsys):
    root = repo(tmp_path, source=BRANCHY.replace("tangled", "untangled"), waivers=SEEDED + WAIVER)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 1
    out = capsys.readouterr().out
    assert "no longer exists" in out and "quality_seed.py" in out and "tools/x.py::untangled" in out and "QG-CPX" in out


def test_reseed_keeps_old_expiry_drops_passing_and_adds_new():
    def measure(key, ccn):
        path = key.split("::")[0]
        return quality_complexity.Measure(key, path, 1, {"ccn": ccn, "nloc": 5, "params": 1, "nesting": 1})

    def old(key, expires):
        return quality_waivers.Waiver(key, {"ccn": 13}, "smalls257", expires, "kept reason", 3)

    kept, gone = "tools/a.py::kept", "tools/a.py::gone"
    given = datetime.date(2027, 4, 27)
    found = quality_seed.reseed(
        [measure(kept, 14), measure(gone, 3), measure("tools/a.py::new", 20)],
        {kept: old(kept, datetime.date(2027, 1, 1)), gone: old(gone, given)}, "smalls257", "debt", given)
    by_key = {w.key: w for w in found}
    assert set(by_key) == {kept, "tools/a.py::new"}
    assert by_key[kept].expires == datetime.date(2027, 1, 1) and by_key[kept].limits == {"ccn": 14}
    assert by_key[kept].reason == "kept reason" and by_key["tools/a.py::new"].expires == given


def test_the_seed_script_writes_a_file_the_gate_accepts(tmp_path, capsys):
    root = repo(tmp_path)
    assert quality_seed.main(["--owner", "smalls257", "--reason", "pre-gate debt", *TODAY], root) == 0
    assert "added: tools/x.py::tangled" in capsys.readouterr().out
    text = (root / ".quality/complexity-waivers.tsv").read_text(encoding="utf-8")
    assert text.count("# seeded 2026-10-27 at ") == 1 and "tools/x.py::tangled\tccn=14" in text
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 0


def test_the_seeded_tree_is_green():
    assert quality_gate.main(["--base", "HEAD"], REPO) == 0


def test_only_existing_python_files_with_a_layer_are_in_scope():
    named = ["tools/quality_gate.py", "README.md", "tools/missing.py", "tests/test_x.py"]
    assert quality_gate.choose_files(REPO, named) == ["tools/quality_gate.py"]


def test_the_root_is_found_when_a_git_hook_has_set_git_dir(monkeypatch):
    git_dir = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--absolute-git-dir"], capture_output=True,
                             text=True, check=True, timeout=30).stdout.strip()
    monkeypatch.setenv("GIT_DIR", git_dir)
    assert quality_gate.find_root() == REPO
