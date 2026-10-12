"""The gate hooks' decisions: what counts as bypassing the hooks, which tests a change needs, and when Stop blocks."""
import importlib.util
import pathlib

import pytest
import yaml

from conftest import REPO

spec = importlib.util.spec_from_file_location("gates", REPO / ".claude" / "hooks" / "gates.py")
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


@pytest.mark.parametrize("command", [
    "git push --no-verify origin main", "git commit -n -m wip", "git commit -am x --no-verify",
    "cd vault && git -c core.hooksPath=/dev/null push", "git config core.hooksPath .", "rm -rf .githooks",
    "chmod -x .githooks/pre-push",
])
def test_commands_that_skip_the_hooks_are_named(command):
    assert gates.bypass_reason(command)


@pytest.mark.parametrize("command", ["git push origin main", "git log -n 5", "git commit -m 'no -n here'",
                                     "python3 -m pytest -q", "ls .githooks"])
def test_ordinary_commands_pass(command):
    assert gates.bypass_reason(command) is None


def test_a_changed_planner_module_needs_its_test_file_and_cli_needs_none():
    changed = ["plugin/lib/planner/releases.py", "plugin/lib/planner/cli.py", "tests/test_search.py", "README.md"]
    assert gates.tests_for(changed) == ["tests/test_releases.py", "tests/test_search.py"]


def test_stop_blocks_once_then_tells_the_user_instead_of_looping():
    assert gates.stop_decision([], already_continuing=False) is None
    assert gates.stop_decision(["x"], already_continuing=False)["decision"] == "block"
    assert "decision" not in gates.stop_decision(["x"], already_continuing=True)


@pytest.mark.parametrize("command", ["git push -n origin main", "git merge -n feature"])
def test_dash_n_skips_hooks_only_on_commit(command):
    assert gates.bypass_reason(command) is None


@pytest.mark.parametrize("command", ["git config core.hooksPath .githooks", "git config --get core.hooksPath"])
def test_turning_the_hooks_on_or_reading_the_setting_passes(command):
    assert gates.bypass_reason(command) is None


@pytest.mark.parametrize("command", ["git config --unset core.hooksPath", "git config core.hooksPath /tmp/none"])
def test_turning_the_hooks_off_is_named(command):
    assert gates.bypass_reason(command)


def test_the_setting_named_inside_a_commit_message_is_not_a_change():
    assert gates.bypass_reason("git commit -m 'core.hooksPath to .githooks turns the hooks on'") is None


IGNORE = (REPO / ".semgrepignore").read_text().splitlines()


@pytest.mark.parametrize("path", ["prototypes/explorer/out/booking-demo.html", "plugin/lib/planner/assets/d3.min.js",
                                  "prototypes/gallery/assets/assets.bundle.js", ".semgrep/prototypes.js",
                                  "plugin/lib/planner/__pycache__/x.py"])
def test_files_semgrepignore_names_are_not_scanned_even_when_named(path):
    # Naming a file on semgrep's command line scans it despite .semgrepignore; a generated page then pasted
    # whole base64 lines into the Stop hook's feedback and pushed a session past its context window.
    assert gates.semgrep_ignores(path, IGNORE)


@pytest.mark.parametrize("path", ["prototypes/explorer/build.py", "plugin/lib/planner/explorer/assets/js/core.js",
                                  "tests/sim/test_x.py", "plugin/lib/planner/assets/app.js"])
def test_hand_written_files_are_scanned(path):
    assert not gates.semgrep_ignores(path, IGNORE)


def rule_paths():
    """(rule file, rule id, glob) for every path a semgrep rule includes or excludes."""
    for rules_file in sorted((REPO / ".semgrep").glob("*.yaml")):
        for rule in yaml.safe_load(rules_file.read_text(encoding="utf-8"))["rules"]:
            for glob in sum((rule.get("paths") or {}).values(), []):
                yield rules_file.name, rule["id"], glob


@pytest.mark.parametrize("file,rule,glob", list(rule_paths()))
def test_every_path_a_semgrep_rule_names_still_exists(file, rule, glob):
    # A rule whose path matches nothing passes every scan, so a move that leaves it watching an empty place is
    # invisible unless something checks. The part of the glob before its first wildcard must exist.
    fixed = []
    for part in pathlib.PurePosixPath(glob.lstrip("/")).parts:
        if any(c in part for c in "*?["):
            break
        fixed.append(part)
    assert REPO.joinpath(*fixed).exists(), f"{file}: {rule} names {glob}, which is not in the repo"


def test_the_asset_slot_rule_watches_the_explorer_where_it_lives_now():
    # The explorer's page code moved from prototypes/explorer into the plugin; the rule that keeps its JS to slot ids
    # has to follow it, or it passes by scanning nothing.
    globs = [g for _, rule, g in rule_paths() if rule == "prototype-asset-by-slot-id"]
    assert "/plugin/lib/planner/explorer/**" in globs
    assert (REPO / "plugin/lib/planner/explorer/assets/js/assets.js").is_file()
