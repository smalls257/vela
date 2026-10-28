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

needs_lizard = pytest.mark.skipif(quality_gate.shutil.which("lizard") is None, reason="lizard is not installed")
FAR = "tools/x.py::tangled\tccn=14\tsmalls257\t2035-01-01\tover the cap when the gate arrived\n"


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


@needs_lizard
def test_an_unwaived_function_over_cap_fails(tmp_path, capsys):
    root = repo(tmp_path)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 1
    out = capsys.readouterr().out
    assert "QG-CPX" in out and "tools/x.py::tangled" in out


@needs_lizard
def test_a_waived_function_passes(tmp_path):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 0


@needs_lizard
def test_missing_waiver_file_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, waivers=None)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    err = capsys.readouterr().err
    assert "could not run" in err and "git checkout -- .quality/complexity-waivers.tsv" in err
    assert "quality_seed" not in err


def test_missing_lizard_cannot_run(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path)
    monkeypatch.setattr(quality_gate.shutil, "which", lambda name: None)
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    assert "lizard is not installed" in capsys.readouterr().err


@needs_lizard
def test_unparseable_file_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, source="def f(:\n")
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 2
    assert "tools/x.py" in capsys.readouterr().err


def stage_waivers(root, text):
    (root / ".quality/complexity-waivers.tsv").write_text(text, encoding="utf-8")
    git(root, "add", ".quality/complexity-waivers.tsv")


FORGED_SEED = "# seeded 2026-10-28 at 1234abcd by smalls257: re-seed after a rename\n"


@needs_lizard
@pytest.mark.parametrize("line,why", [
    (WAIVER.replace("ccn=14", "ccn=99"), "records"),
    (WAIVER.replace("tangled", "invented"), "not over its cap"),
    (FAR, "more than a year out"),
])
def test_a_hand_added_line_fails_even_under_a_forged_seeded_line(tmp_path, capsys, line, why):
    root = repo(tmp_path)
    stage_waivers(root, FORGED_SEED + line)
    assert quality_gate.main(["--staged", *TODAY], root) == 1
    out = capsys.readouterr().out
    assert "QG-WAIVER" in out and why in out and "a seed would not write it" in out


@needs_lizard
def test_a_line_a_seed_would_write_passes(tmp_path):
    root = repo(tmp_path)
    stage_waivers(root, FORGED_SEED + WAIVER)
    assert quality_gate.main(["--staged", *TODAY], root) == 0


@needs_lizard
def test_staging_nothing_but_docs_checks_no_file(tmp_path):
    expired = WAIVER.replace("2027-04-27", "2026-01-01")
    root = repo(tmp_path, waivers=SEEDED + expired)
    assert quality_gate.main(["--staged", *TODAY], root) == 0


@needs_lizard
def test_an_expired_waiver_fails_a_commit_that_touches_its_file_and_the_whole_tree_gate(tmp_path, capsys):
    expired = WAIVER.replace("2027-04-27", "2026-01-01")
    root = repo(tmp_path, waivers=SEEDED + expired)
    assert quality_gate.main(["--staged", "tools/x.py", *TODAY], root) == 1
    assert quality_gate.main(["--base", "HEAD", *TODAY], root) == 1
    assert "expired on 2026-01-01" in capsys.readouterr().out


@needs_lizard
def test_full_mode_without_a_base_cannot_run(tmp_path, capsys):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    assert quality_gate.main(TODAY, root) == 2
    assert "no base" in capsys.readouterr().err
    assert quality_gate.main(["--base", "", *TODAY], root) == 2


@needs_lizard
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
    today = datetime.date(2026, 10, 27)
    found = quality_seed.reseed(
        [measure(kept, 14), measure(gone, 3), measure("tools/a.py::new", 20)],
        {kept: old(kept, datetime.date(2027, 1, 1)), gone: old(gone, today)}, "smalls257", "debt", today)
    by_key = {w.key: w for w in found}
    assert set(by_key) == {kept, "tools/a.py::new"}
    assert by_key[kept].expires == datetime.date(2027, 1, 1) and by_key[kept].limits == {"ccn": 14}
    assert by_key[kept].reason == "kept reason" and by_key["tools/a.py::new"].expires == today + datetime.timedelta(days=183)
    assert by_key["tools/a.py::new"].reason == "debt"


@needs_lizard
def test_the_seed_script_writes_a_file_the_gate_accepts(tmp_path, capsys):
    root = repo(tmp_path)
    assert quality_seed.main(["--owner", "smalls257", "--reason", "pre-gate debt", *TODAY], root) == 0
    assert "added: tools/x.py::tangled" in capsys.readouterr().out
    text = (root / ".quality/complexity-waivers.tsv").read_text(encoding="utf-8")
    assert text.count("# seeded 2026-10-27 at ") == 1 and "tools/x.py::tangled\tccn=14" in text
    assert text.rstrip().endswith("\tpre-gate debt")  # a reseed writes the owner's reason, not the first seed's
    assert quality_gate.main(["tools/x.py", *TODAY], root) == 0


@needs_lizard
def test_the_seed_refuses_a_missing_file_unless_first_and_first_refuses_an_existing_one(tmp_path, capsys):
    root = repo(tmp_path, waivers=None)
    assert quality_seed.main(["--reason", "x", *TODAY], root) == 2
    assert "git checkout -- .quality/complexity-waivers.tsv" in capsys.readouterr().err
    assert quality_seed.main(["--first", "--reason", "pre-gate debt", *TODAY], root) == 0
    assert "\tover the cap when the gate arrived\n" in (root / ".quality/complexity-waivers.tsv").read_text(encoding="utf-8")
    assert quality_seed.main(["--first", "--reason", "x", *TODAY], root) == 2


def test_new_expiries_are_staggered_across_six_to_twelve_months_worst_first():
    today = datetime.date(2026, 10, 27)
    days = [(d - today).days for d in quality_seed.staggered_expiries(5, today)]
    assert days[0] == 183 and days[-1] == 365 and days == sorted(set(days))
    assert [(d - today).days for d in quality_seed.staggered_expiries(1, today)] == [183]
    assert quality_seed.staggered_expiries(0, today) == []


def test_the_biggest_overage_expires_first():
    def measure(key, ccn):
        return quality_complexity.Measure(key, key.split("::")[0], 1, {"ccn": ccn, "nloc": 5, "params": 1, "nesting": 1})

    today = datetime.date(2026, 10, 27)
    found = quality_seed.reseed([measure("tools/a.py::mild", 13), measure("tools/a.py::worst", 40),
                                 measure("tools/a.py::mid", 20)], {}, "smalls257", "debt", today)
    order = [w.key.split("::")[1] for w in sorted(found, key=lambda w: w.expires)]
    assert order == ["worst", "mid", "mild"]


@needs_lizard
def test_renew_gives_named_keys_a_new_date_and_reason_and_the_gate_accepts_it(tmp_path, capsys):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    argv = ["--renew", "tools/x.py::tangled", "--until", "2027-06-01", "--reason", "split lands in November", *TODAY]
    assert quality_seed.main(argv, root) == 0
    text = (root / ".quality/complexity-waivers.tsv").read_text(encoding="utf-8")
    assert "\t2027-06-01\tsplit lands in November" in text
    git(root, "add", ".quality/complexity-waivers.tsv")
    assert quality_gate.main(["--staged", *TODAY], root) == 0


@needs_lizard
@pytest.mark.parametrize("argv,why", [
    (["--renew", "tools/x.py::nope", "--until", "2027-06-01"], "not in the waiver file"),
    (["--renew", "tools/x.py::tangled", "--until", "2035-01-01"], "must fall between"),
    (["--renew", "tools/x.py::tangled", "--until", "2026-01-01"], "must fall between"),
])
def test_renew_refuses_unknown_keys_and_dates_the_gate_would_reject(tmp_path, capsys, argv, why):
    root = repo(tmp_path, waivers=SEEDED + WAIVER)
    assert quality_seed.main([*argv, "--reason", "x", *TODAY], root) == 2
    assert why in capsys.readouterr().err


@needs_lizard
def test_the_seeded_tree_is_green():
    seeded_on = quality_waivers.seeded_line((REPO / quality_waivers.WAIVER_FILE).read_text(encoding="utf-8")).split()[2]
    assert quality_gate.main(["--base", "HEAD", "--today", seeded_on], REPO) == 0


def test_only_existing_python_files_with_a_layer_are_in_scope():
    named = ["tools/quality_gate.py", "README.md", "tools/missing.py", "tests/test_x.py"]
    assert quality_gate.choose_files(REPO, named) == ["tools/quality_gate.py"]


def test_the_root_is_found_when_a_git_hook_has_set_git_dir(monkeypatch):
    git_dir = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--absolute-git-dir"], capture_output=True,
                             text=True, check=True, timeout=30).stdout.strip()
    monkeypatch.setenv("GIT_DIR", git_dir)
    assert quality_gate.find_root() == REPO
