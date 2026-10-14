"""What the voice-seed skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import subprocess
import sys

import yaml
from conftest import REPO, skill_text
from vela import schema

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def _verbatim_script(seed, file, passage):
    block = seed.split("Third, compare the stored body", 1)[1].split("```\n", 2)[1]
    return block.replace("<file>", str(file)).replace("<the passage, exactly as pasted>", passage.rstrip("\n"))


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_voice_seed_skips_git_for_a_reader():
    assert "only the local-only place is open" in text("skills/voice-seed/SKILL.md")


# --- From tests/test_voice.py: House-voice examples: license and attribution, copies in step, and the page-type map.

# v2: the owner's examples, retiring, and the cap of five.


def test_voice_seed_stores_the_owner_words_and_never_rewrites_them():
    seed = skill_text("voice-seed")
    assert "It never rewrites them." in seed
    assert "Never rewrite, shorten, correct or paraphrase the owner's words." in seed
    assert "Did you write this yourself?" in seed and "wait for an explicit yes to each" in seed
    assert "Store an accepted passage as it was pasted." in seed
    assert "Never write under `voice/corpus/`." in seed


def test_voice_seed_retires_the_seed_only_once_the_owner_has_two():
    seed = skill_text("voice-seed")
    assert "A `public-seed` example retires when" in seed
    assert "Set `state: retired` on each example in it. Change only the `state:` line." in seed
    assert "Never delete a seed example" in seed
    assert "A type with fewer than 2 owner passages keeps its seed." in seed
    assert f"A type holds at most {schema.VOICE_ACTIVE_MAX}." in seed


def test_voice_seed_commits_by_path_and_never_claims_a_pr():
    seed = skill_text("voice-seed")
    assert "Never use `git add -A`." in seed
    assert "Never say a PR exists unless `gh` printed its URL." in seed
    assert "gh api user -q .login" in seed


def test_the_example_voice_seed_writes_has_only_documented_fields():
    seed = skill_text("voice-seed")
    block = seed.split("## Write the examples (section 4)", 1)[1].split("````\n")[1]  # the recipe lives in WRITE.md
    filled = (block.replace("<type>", "decision").replace("NNN", "004").replace("<handle>", "hl-solution-lead")
              .replace("<where it comes from>", "design review").replace("<today>", "2026-11-20"))
    meta = yaml.safe_load(filled.split("---\n")[1])
    assert str(meta["added"]) == "2026-11-20"  # YAML reads an unquoted date as a date
    assert {k: v for k, v in meta.items() if k != "added"} == {
        "id": "VX-decision-004", "voice_type": "decision", "source": "owner", "author": "@hl-solution-lead",
        "from": "design review", "state": "active"}
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    for key in meta:
        assert f"`{key}`" in conventions, key


# fix round 1: write mechanism, risky lines, privacy, count and cap rules, quoting, final check.


def test_voice_seed_writes_verbatim_with_a_quoted_heredoc_and_compares():
    seed = skill_text("voice-seed")
    assert "write the frontmatter with the Write tool" in seed
    assert "cat >> <file> <<'VELA_EOF'" in seed
    assert "If the passage contains a line `VELA_EOF`, pick another delimiter" in seed
    assert "Compare the two with `cmp`" in seed
    assert "If `cmp` reports a difference, stop. Tell the owner and do not repair the file." in seed
    assert "A heredoc always ends its text with a newline, so a paste that had no final newline gains one" in seed
    assert "When the paste had none, tell the owner." in seed
    assert "It does not prove the chat text reached the heredoc unchanged." in seed
    assert "byte-exact" not in seed and "exactly as pasted" in seed


def test_voice_seed_warns_about_boundary_and_generated_lines():
    seed = skill_text("voice-seed")
    assert "Take everything after the frontmatter's closing `---` as the body." in seed
    assert "exactly `---`, or contains `<!-- generated:`" in seed
    assert "Store it only on an explicit yes, and never rewrite the line." in seed


def test_voice_seed_offers_a_local_only_place_and_says_what_is_committed():
    seed = skill_text("voice-seed")
    assert "`voice/examples/` is committed, pushed and opened as a PR, so anyone with access to this repository can read" in seed
    assert "local only: `voice/local/<type>/`" in seed
    assert "If the owner says their employer owns the text, or is not sure, recommend local only." in seed
    assert "A local-only run changes no committed file and makes no branch, commit or PR." in seed
    assert "Name local examples only as a count." in seed
    assert "Retiring a committed example changes a committed file, so it goes through the PR" in seed
    ignored = (REPO / "template" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "voice/local/" in ignored and "voice/corpus/" in ignored


def test_voice_seed_and_conventions_count_owner_examples_the_same_way():
    seed = skill_text("voice-seed")
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "A `public-seed` example retires when the active `owner` and `owner-edit` examples in its own folder, after this run, number at least 2." in seed
    assert "2 `active` examples with `source: owner` or `owner-edit` in the same folder as a `public-seed` example, counted after the run" in conventions
    assert "counting `voice/examples/` and `voice/local/` together" in conventions


def test_voice_seed_cap_order_and_refusal_match_conventions():
    seed = skill_text("voice-seed")
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "`public-seed` first, then `owner-edit`, then `owner`" in seed
    assert "the `public-seed` examples first, then the `owner-edit`, then the `owner`, the oldest `added` first" in conventions
    assert "The owner may refuse. If they refuse, store nothing new for that type and say why" in seed
    assert "The owner may refuse a retirement. Then nothing new is stored for that type." in conventions


def test_voice_seed_quotes_from_and_runs_a_final_check(tmp_path):
    seed = skill_text("voice-seed")
    assert "Write `from` in single-quoted YAML, and double any `'` inside it" in seed
    assert "re-read the frontmatter and confirm it parses as YAML" in seed
    block = seed.split("## Final check (section 6)", 1)[1].split("```\n", 2)[1]  # the count lives in WRITE.md
    script = block.split("<<'VELA_EOF'\n", 1)[1].rsplit("VELA_EOF", 1)[0]
    vault = tmp_path
    for folder, n in (("voice/examples", 3), ("voice/local", 3)):
        (vault / folder / "decision").mkdir(parents=True)
        for i in range(n):
            (vault / folder / "decision" / f"VX-decision-{folder[-1]}{i}.md").write_text(
                "---\nvoice_type: decision\nstate: active\nfrom: 'it''s'\n---\n\nbody\n", encoding="utf-8")
    assert block.startswith('python3 - "${CLAUDE_PLUGIN_ROOT}/lib" <<')  # the plugin's own PyYAML, no pip step
    lib = str(REPO / "plugin" / "lib")  # what ${CLAUDE_PLUGIN_ROOT}/lib expands to
    run = lambda: subprocess.run([sys.executable, "-c", script, lib], cwd=vault, capture_output=True, text=True, timeout=60)
    assert run().returncode == 1  # six active in one type
    next((vault / "voice" / "local" / "decision").glob("*.md")).write_text(
        "---\nvoice_type: decision\nstate: retired\n---\n", encoding="utf-8")
    assert run().returncode == 0
    next((vault / "voice" / "local" / "decision").glob("*.md")).write_text("---\n: : [\n---\n", encoding="utf-8")
    assert run().returncode == 1  # a file that does not parse


# fix round 2: local examples never change committed files; the verbatim check is a tool comparison.


def test_a_local_only_run_never_retires_a_committed_seed():
    seed = skill_text("voice-seed")
    assert "A local example never retires a committed seed" in seed
    assert "In a local-only run, nothing in `voice/examples/` retires." in seed
    assert "A local-only run changes no committed file and makes no branch, commit or PR." in seed
    assert "In a local-only run, only local examples may retire." in seed


def test_the_verbatim_check_compares_with_cmp(tmp_path):
    seed = skill_text("voice-seed")
    passage = "It’s “quoted”  \r\n---\ntrailing   \n\nlast line\n"
    stored = tmp_path / "VX-decision-001.md"
    head = "---\nid: VX-decision-001\nstate: active\n---\n\n"

    def run(body):
        stored.write_bytes((head + body).encode("utf-8"))
        script = _verbatim_script(seed, stored, passage)
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)

    assert run(passage).returncode == 0
    assert run(passage.replace("   \n", "\n")).returncode != 0   # trailing whitespace lost
    assert run(passage.replace("\r\n", "\n")).returncode != 0   # line ending changed
    assert run(passage.replace("’", "'")).returncode != 0    # quote straightened
    assert run(passage.replace("“", '"')).returncode != 0


def test_the_verbatim_check_block_cleans_up_its_own_temp_file(tmp_path):
    """Each block runs in a fresh shell, so the one that makes the temp file also removes it."""
    seed = skill_text("voice-seed")
    stored = tmp_path / "VX-decision-001.md"
    stored.write_text("---\nid: VX-decision-001\n---\n\nA passage.\n", encoding="utf-8")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    # macOS mktemp ignores TMPDIR, so the test points mktemp itself at the scratch folder
    script = f'mktemp() {{ command mktemp "{scratch}/t.XXXXXX"; }}\n' + _verbatim_script(seed, stored, "A passage.\n")
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0
    assert list(scratch.iterdir()) == []
