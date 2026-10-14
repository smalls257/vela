"""House-voice examples: license and attribution, copies in step, and the page-type map."""
import re
import subprocess
import sys

import pytest
import yaml

from conftest import REPO, skill_text
from planner import parse, schema

EXAMPLES = REPO / "template" / "voice" / "examples"
FILES = sorted(EXAMPLES.glob("*/*.md"))
VOICE_TYPES = ("diagnosis", "decision", "how-it-works")
MAP_VALUES = VOICE_TYPES + ("structured",)
SKILL = REPO / "plugin" / "skills" / "house-voice" / "SKILL.md"


def split(path):
    text = path.read_text(encoding="utf-8")
    _, head, body = text.split("---\n", 2)
    return yaml.safe_load(head), body


def test_two_or_three_examples_per_voice_type():
    for voice_type in VOICE_TYPES:
        count = len(list((EXAMPLES / voice_type).glob("*.md")))
        assert 2 <= count <= 3, f"{voice_type} has {count} examples"
    assert sorted(p.name for p in EXAMPLES.iterdir()) == sorted(VOICE_TYPES)


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_every_example_carries_license_and_attribution(path):
    meta, body = split(path)
    assert meta["id"] == path.stem
    assert meta["voice_type"] == path.parent.name
    assert meta["source"] == "public-seed"
    assert meta["license"] == "CC BY 3.0"
    assert meta["license_url"] == "https://creativecommons.org/licenses/by/3.0/"
    assert meta["author"] and meta["chapter"].startswith("Chapter ")
    assert meta["work"].startswith("The Architecture of Open Source Applications, Volume ")
    assert re.match(r"^https://aosabook\.org/en/v[12]/[a-z]+\.html$", meta["url"])
    assert meta["changes"].startswith("none")
    words = len(body.split())
    assert 80 <= words <= 300, f"{path.name} has {words} words"
    assert "[[" not in body


def test_only_public_seed_text_is_committed():
    """Evans, Luu and Fowler stay in the gitignored voice/corpus/. Nothing committed names them as a source."""
    for root in (REPO / "template", REPO / "examples" / "unified-booking", REPO / "plugin"):
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"\b(Evans|Luu|Fowler)\b", text), f"{path} names a corpus author"
        assert not list(root.rglob("corpus/*")), f"{root} holds corpus files"


def test_fixture_examples_equal_the_template():
    fixture = REPO / "examples" / "unified-booking" / "voice" / "examples"
    got = sorted(p.relative_to(fixture).as_posix() for p in fixture.glob("*/*.md"))
    assert got == sorted(p.relative_to(EXAMPLES).as_posix() for p in FILES)
    for path in FILES:
        assert (fixture / path.relative_to(EXAMPLES)).read_bytes() == path.read_bytes()


def voice_map():
    text = SKILL.read_text(encoding="utf-8")
    section = text.split("## Page types and voice types", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `([a-z0-9-]+)` \| ([a-z-]+) \|$", section, re.M)
    return dict(rows)


def test_voice_map_values():
    mapping = voice_map()
    assert mapping, "the house-voice skill has no page-type table"
    for key, value in mapping.items():
        assert value in MAP_VALUES, f"{key} maps to {value}"


def test_every_page_type_has_a_voice_type():
    mapping = voice_map()
    for page_type in schema.PAGE_TYPES:
        assert page_type in mapping, f"page type {page_type} has neither a voice type nor structured"


def test_every_template_page_resolves_to_a_voice_type():
    mapping = voice_map()
    template = REPO / "template"
    for path in template.rglob("*.md"):
        rel = path.relative_to(template)
        if rel.parts[0] in ("voice", ".github") or rel.name in schema.SKIP_FILES:
            continue
        page = parse.parse_page(rel.as_posix(), path.read_text(encoding="utf-8"))
        assert page.id in mapping or page.type in mapping, f"{rel} ({page.id}, {page.type}) has no voice type"


# v2: the owner's examples, retiring, and the cap of five.

SEED_SKILL = REPO / "plugin" / "skills" / "voice-seed" / "SKILL.md"


def test_template_examples_use_the_schema_values():
    for path in FILES:
        meta, _ = split(path)
        assert meta["voice_type"] in schema.VOICE_TYPES
        assert meta["source"] in schema.VOICE_SOURCES
        assert meta["state"] in schema.VOICE_STATES
    for voice_type in schema.VOICE_TYPES:
        active = [p for p in (EXAMPLES / voice_type).glob("*.md") if split(p)[0]["state"] == "active"]
        assert len(active) <= schema.VOICE_ACTIVE_MAX


def test_house_voice_reads_only_active_examples():
    voice = SKILL.read_text(encoding="utf-8")
    assert "Read every example of that type whose frontmatter says `state: active`, in file-name order" in voice
    assert "Skip every `state: retired` example." in voice
    assert "If the type has fewer than two active examples" in voice
    assert "`/planner:voice-seed`" in voice


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
    assert "cat >> <file> <<'PLANNER_EOF'" in seed
    assert "If the passage contains a line `PLANNER_EOF`, pick another delimiter" in seed
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


def test_house_voice_reads_the_local_folder_too():
    voice = SKILL.read_text(encoding="utf-8")
    assert "`voice/local/<voice type>/*.md`" in voice
    assert "local `owner` and `owner-edit` examples first, then `voice/examples/`, then any other local example" in voice
    assert "fewer than two active examples across both folders" in voice


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
    script = block.split("<<'PLANNER_EOF'\n", 1)[1].rsplit("PLANNER_EOF", 1)[0]
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
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    voice = SKILL.read_text(encoding="utf-8")
    assert "A local example never retires a committed seed" in seed
    assert "In a local-only run, nothing in `voice/examples/` retires." in seed
    assert "A local-only run changes no committed file and makes no branch, commit or PR." in seed
    assert "In a local-only run, only local examples may retire." in seed
    assert "A local example never retires a committed seed, so every clone keeps its seed." in conventions
    assert "reads local `owner` and `owner-edit` examples ahead of the committed ones" in conventions
    assert "local `owner` and `owner-edit` examples first" in voice


def _verbatim_script(seed, file, passage):
    block = seed.split("Third, compare the stored body", 1)[1].split("```\n", 2)[1]
    return block.replace("<file>", str(file)).replace("<the passage, exactly as pasted>", passage.rstrip("\n"))


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
