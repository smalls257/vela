"""What the voice-seed skill says, pinned in one place (overhaul plan Task 3, rewritten by Task 22i).

The retire plan, the verbatim write and its compare, and the frontmatter are `vela voice plan` / `vela voice save`
now (tests/test_voice_cli.py proves them). What stays here is the conversation the skill holds with the owner, the
one recipe the CLI can't do (getting the paste into a file), and rule-deletion asserts: a moved rule left behind in
the text is a second copy that drifts from the code.
"""
import re
import shlex
import subprocess

from conftest import REPO, skill_text
from vela import cli, schema

PLUGIN = REPO / "plugin"
SEED = PLUGIN / "skills" / "voice-seed"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- Reader mode: no git in a read copy.


def test_voice_seed_skips_git_for_a_reader():
    assert "only the local-only place is open" in text("skills/voice-seed/SKILL.md")


# --- The owner's words, the two yeses, and the places.


def test_voice_seed_stores_the_owner_words_and_never_rewrites_them():
    seed = skill_text("voice-seed")
    assert "It never rewrites them." in seed
    assert "Never rewrite, shorten, correct or paraphrase the owner's words." in seed
    assert "Did you write this yourself?" in seed and "wait for an explicit yes to each" in seed
    assert "Store an accepted passage as it was pasted." in seed
    assert "Never write under `voice/corpus/`." in seed


def test_voice_seed_captures_each_yes_and_passes_it_to_save():
    """`voice save` refuses without the consent captures, so each yes is a capture in the owner's words."""
    seed = skill_text("voice-seed")
    assert "vela record add '\"<their words>\"' --origin @<handle> --tag instruction" in seed
    assert "--consent ^c<N> --commit-consent ^c<M>" in seed
    assert "never pass another capture in its place" in seed
    assert "Saving a sample needs an open session" in seed  # voice save reads the yeses from the open record


def test_voice_seed_keeps_the_cap_conversation_and_the_seed_line():
    seed = skill_text("voice-seed")
    assert f"a type holds at most {schema.VOICE_ACTIVE_MAX}" in seed
    assert "The owner may refuse. If they refuse, store nothing new for that type and say why" in seed
    assert "A type with fewer than 2 owner passages keeps its seed" in seed
    assert "I have only one sample of how you explain how things work" in seed


def test_voice_seed_offers_a_local_only_place_and_says_what_is_committed():
    seed = skill_text("voice-seed")
    assert "`voice/examples/` is committed, pushed and opened as a PR, so anyone with access to this repository can read" in seed
    assert "local only: `voice/local/<type>/`" in seed
    assert "If the owner says their employer owns the text, or is not sure, recommend local only." in seed
    assert "A local-only run changes no committed file and makes no branch, commit or PR." in seed
    assert "A local example never retires a committed seed" in seed
    assert "Name local examples only as a count" in seed
    ignored = (REPO / "template" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "voice/local/" in ignored and "voice/corpus/" in ignored


def test_voice_seed_warns_about_boundary_lines_and_asks():
    seed = skill_text("voice-seed")
    assert "--from .vela/voice-passage.md --for-lead" in seed  # voice plan reports the lines and the word count
    assert "Store it only on an explicit yes, and never rewrite the line." in seed


def test_voice_seed_commits_by_path_and_never_claims_a_pr():
    seed = skill_text("voice-seed")
    # Task 24: the samples ride a checkpoint through vela, by exact path; the hand-typed stage and commit are gone
    assert "run `vela close stage --checkpoint --for-lead`" in seed and "Never stage or commit by hand." in seed
    assert "git status --short voice/examples" not in seed and "Commit with the message" not in seed
    assert "Never say a PR exists unless `gh` printed its URL." in seed
    assert "vela whoami --json" in seed


# --- The one recipe left: the paste into a file, byte for byte.


def heredoc_block(seed):
    return seed.split("## 4. Save each one", 1)[1].split("```\n", 2)[1]


def test_voice_seed_writes_the_paste_with_a_quoted_heredoc():
    seed = skill_text("voice-seed")
    assert "cat > .vela/voice-passage.md <<'VELA_EOF'" in heredoc_block(seed)
    assert "If the passage contains a line `VELA_EOF`, pick another delimiter" in seed
    assert "A heredoc always ends its text with a newline, so a paste that had no final newline gains one" in seed
    assert "When the paste had none, tell the owner." in seed
    assert "It does not prove the chat text reached the heredoc unchanged." in seed
    assert "rm -f .vela/voice-passage.md" in seed


def test_the_heredoc_keeps_the_paste_byte_for_byte(tmp_path):
    seed = skill_text("voice-seed")
    passage = "It’s “quoted”  \r\n---\n$HOME `x` trailing   \n\nlast line"
    (tmp_path / ".vela").mkdir()
    script = heredoc_block(seed).replace("<the passage, exactly as pasted>", passage)
    done = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert (tmp_path / ".vela" / "voice-passage.md").read_bytes() == (passage + "\n").encode("utf-8")


# --- Rule deletion: these moved into `vela voice plan` / `vela voice save`; no copy stays in the skill.


def test_the_moved_rules_are_gone_from_the_skill():
    seed = skill_text("voice-seed")
    assert not (SEED / "WRITE.md").exists()
    for gone in ("VX-<type>-NNN", "write the frontmatter with the Write tool", "cat >> <file>", "cmp", "shasum",
                 "awk ", "A `public-seed` example retires when", "`public-seed` first, then `owner-edit`",
                 "Set `state: retired`", "single-quoted YAML", "gh api user", "git switch -c voice/seed",
                 "about 80 to 300 words", "glob.glob", 'vela conventions "Voice examples"'):
        assert gone not in seed, gone


def test_voice_seed_names_only_commands_that_exist():
    parser = cli.build_parser()
    seed = skill_text("voice-seed")
    found = re.findall(r"`vela ((?:whoami|session|record|voice) [^`]*)`", seed)
    assert len(found) >= 5, found
    for call in found:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)
