"""`vela explore`: the command a vault's user runs to get the explorer page.

The builder's own checks are in test_explorer.py. These check what the command promises a user who has only the
plugin: the page and the pinned layout land in the vault, nothing lands in the plugin, the page carries no path of
the machine that built it, and the whole thing runs from a copy of plugin/ with no repo around it.
"""
import ast
import filecmp
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from conftest import REPO, run

SNAPSHOT = REPO / "tests/sim/snapshots/trading-coach/after-80b"
PLUGIN = REPO / "plugin"
PINS = ".vela/explorer-pins.json"
PAGE = "dashboard.html"


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, root)
    return root


def explore(vault, *extra):
    return run("explore", str(vault), "--today", "2026-10-10", *extra)


def test_the_first_build_writes_the_pins_and_the_page_into_the_vault_and_says_so(vault):
    code, said = explore(vault)
    assert code == 0, said
    assert (vault / PAGE).is_file() and (vault / PINS).is_file()
    assert f"first build: wrote the pinned positions of 4 apps and parties to {PINS}" in said
    pins = json.loads((vault / PINS).read_text(encoding="utf-8"))
    assert set(pins) >= {"APP-tickertalk", "APP-coach"}


def test_a_later_build_keeps_every_app_where_it_was_and_does_not_rewrite_the_pins(vault):
    explore(vault)
    before = (vault / PINS).read_bytes()
    pinned = {"APP-tickertalk": [3, 2]}  # a lead's earlier choice must win over where the layout would put it
    pins = json.loads(before)
    pins.update(pinned)
    (vault / PINS).write_text(json.dumps(pins), encoding="utf-8")
    code, said = explore(vault)
    assert code == 0 and "first build" not in said
    assert json.loads((vault / PINS).read_text(encoding="utf-8"))["APP-tickertalk"] == [3, 2]


def test_a_new_app_is_pinned_without_moving_the_others(vault):
    explore(vault)
    pins = json.loads((vault / PINS).read_text(encoding="utf-8"))
    dropped = pins.pop("APP-coach")
    (vault / PINS).write_text(json.dumps(pins), encoding="utf-8")
    code, said = explore(vault)
    assert code == 0 and f"pinned new positions in {PINS}: APP-coach" in said
    again = json.loads((vault / PINS).read_text(encoding="utf-8"))
    assert all(again[k] == v for k, v in pins.items()) and again["APP-coach"] == dropped


def test_a_pins_file_that_cannot_be_read_stops_the_build_instead_of_moving_every_app(vault):
    (vault / ".vela").mkdir()
    (vault / PINS).write_text("{not json", encoding="utf-8")
    code, said = explore(vault)
    assert code == 2 and "cannot read pins file" in said and PINS in said
    assert not (vault / PAGE).exists()


def test_out_puts_the_page_where_asked_and_the_default_stays_in_the_vault(vault, tmp_path):
    elsewhere = tmp_path / "pages" / "x.html"
    code, said = explore(vault, "-o", str(elsewhere))
    assert code == 0 and elsewhere.is_file()
    assert not (vault / PAGE).exists()
    assert (vault / PINS).is_file()  # the layout belongs to the vault whichever place the page goes


def test_the_page_carries_no_path_of_the_machine_that_built_it(vault, tmp_path):
    out = tmp_path / "out.html"
    explore(vault, "-o", str(out))
    page = out.read_text(encoding="utf-8")
    for private in (str(pathlib.Path.home()), str(tmp_path), str(tmp_path.resolve()), str(vault.resolve())):
        assert private not in page, private
    explore(vault)
    assert str(vault.resolve()) not in (vault / PAGE).read_text(encoding="utf-8")


def test_a_page_built_beside_the_vault_links_to_its_files_relatively(vault):
    explore(vault)
    page = (vault / PAGE).read_text(encoding="utf-8")
    assert '"vault":"."' in page


def test_the_report_warns_when_the_vault_would_not_commit_the_page(vault):
    (vault / ".gitignore").write_text("voice/local/\ndashboard.html\n", encoding="utf-8")
    code, said = explore(vault)
    assert code == 0 and "lists dashboard.html" in said
    (vault / ".gitignore").write_text("voice/local/\n.vela/*\n!.vela/explorer-pins.json\n", encoding="utf-8")
    code, said = explore(vault)
    assert "lists dashboard.html" not in said


@pytest.mark.parametrize("args,message", [
    (["--theme", "neon"], "theme 'neon' is not one of console, graphite, daylight, vaporwave"),
    (["--design", "APP-nope=missing.md"], "--design"),
    (["--assets", "missing.json"], "--assets"),
])
def test_bad_arguments_fail_with_a_reason_and_write_nothing(vault, args, message):
    code, said = explore(vault, *args)
    assert code == 2 and message in said
    assert not (vault / PAGE).exists() and not (vault / PINS).exists()


def test_a_folder_that_is_not_a_vault_is_named(tmp_path):
    code, said = run("explore", str(tmp_path), "--today", "2026-10-10")
    assert code == 2 and "not a vault" in said


def test_a_date_that_is_not_a_date_is_named(vault):
    code, said = run("explore", str(vault), "--today", "tomorrow")
    assert code == 2 and "tomorrow" in said


def test_the_demo_vault_arrives_with_its_pins_and_keeps_them(tmp_path):
    sys.path.insert(0, str(REPO / "tests/fixtures/explorer"))
    import make_demo_vault
    demo = tmp_path / "demo"
    make_demo_vault.main(demo)
    shipped = REPO / "tests/fixtures/explorer/pins/unified-booking.json"
    assert filecmp.cmp(shipped, demo / PINS, shallow=False)
    code, said = run("explore", str(demo), "--today", "2026-11-20")
    assert code == 0 and "pinned new positions" not in said
    assert json.loads(shipped.read_text(encoding="utf-8")) == json.loads((demo / PINS).read_text(encoding="utf-8"))


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def test_it_runs_from_a_copy_of_the_plugin_alone(vault, tmp_path):
    # Nothing but plugin/ is copied: no tests/, no repo layout above it. If the builder reached for
    # anything outside the plugin, this build fails where a user's install would.
    alone = tmp_path / "installed" / "vela"
    shutil.copytree(PLUGIN, alone, ignore=shutil.ignore_patterns("__pycache__"))
    before = tree(alone)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = tmp_path / "page.html"
    done = subprocess.run([sys.executable, str(alone / "scripts/vela"), "explore", str(vault), "-o", str(out),
                           "--today", "2026-10-10"], capture_output=True, text=True, cwd=tmp_path, env=env, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert tree(alone) == before  # nothing is written into the plugin, not even a compiled cache
    from_copy = out.read_bytes()
    (vault / PINS).unlink()  # a first build again, so both plugins start from the same place
    code, _ = explore(vault, "-o", str(out))
    assert code == 0
    # Compared as a bool: pytest would spend minutes diffing two 3 MB lines to explain a failure.
    same = out.read_bytes() == from_copy
    assert same, "the copied plugin drew a different page from the repo's"


def test_a_copy_of_the_plugin_alone_pins_a_first_build_in_the_vault(vault, tmp_path):
    alone = tmp_path / "installed" / "vela"
    shutil.copytree(PLUGIN, alone, ignore=shutil.ignore_patterns("__pycache__"))
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    done = subprocess.run([sys.executable, str(alone / "scripts/vela"), "explore", str(vault), "--today", "2026-10-10"],
                          capture_output=True, text=True, cwd=tmp_path, env=env, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "first build" in done.stdout and (vault / PINS).is_file() and (vault / PAGE).is_file()


def test_the_plugin_imports_nothing_from_the_tests_and_never_edits_the_path():
    for path in (PLUGIN / "lib/vela/explorer").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not any(n.split(".")[0] in ("tests",) for n in names), path
            assert not (isinstance(node, ast.Attribute) and node.attr == "path" and getattr(node.value, "id", "") == "sys"), path
