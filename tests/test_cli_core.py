"""C28 --version, C33 next-id counts the default branch, C35 a folder passed without --vault is explained."""
import json
import subprocess

from conftest import REPO, run
from vela import cli


def test_c28_version_prints_the_plugin_json_version():
    declared = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    assert run("--version") == (0, f"Vela planner {declared}\n")


def test_c28_a_missing_plugin_json_is_said_not_hidden(tmp_path):
    assert cli.plugin_version(tmp_path / "nope.json").startswith("unknown (nope.json could not be read")


def _sh(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   check=True, capture_output=True, timeout=60)


def test_c33_a_number_used_on_a_merged_and_deleted_branch_is_not_handed_out_again(mini):
    _sh(mini, "init", "-q", "-b", "main")
    _sh(mini, "add", "-A")
    _sh(mini, "commit", "-q", "-m", "vault")
    _sh(mini, "switch", "-q", "-c", "session/x")
    with open(mini / "11-unknowns-and-risks.md", "a", encoding="utf-8") as page:
        page.write("\n### UNK-004 Merged then deleted\n")
    _sh(mini, "commit", "-qam", "unknown")
    _sh(mini, "switch", "-q", "main")
    _sh(mini, "merge", "-q", "session/x")
    _sh(mini, "branch", "-q", "-D", "session/x")
    (mini / "11-unknowns-and-risks.md").write_text(
        (mini / "11-unknowns-and-risks.md").read_text(encoding="utf-8").replace("### UNK-004 Merged then deleted", "### UNK-002b gone"),
        encoding="utf-8")
    code, out = run("next-id", "UNK", "--vault", str(mini))
    assert (code, out.strip()) == (0, "UNK-005")


def test_c35_a_folder_given_without_vault_says_to_use_vault(mini):
    code, out = run("check", str(mini))
    assert code == 2
    assert f"planner check --vault {mini}" in out


def test_c13_view_does_not_stamp_a_token_from_the_remote_url(mini, tmp_path):
    out_file = tmp_path / "v.html"
    code, out = run("view", "--vault", str(mini), "--out", str(out_file), "--date", "2026-01-15",
                    "--repo-url", "https://bob:ghp_SECRET123@github.com/acme/plan.git")
    assert code == 0, out
    html = out_file.read_text(encoding="utf-8")
    assert "ghp_SECRET123" not in html and "https://github.com/acme/plan.git" in html
