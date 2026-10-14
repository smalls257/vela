"""planner voicescore: an optional style-embedding reading of each prose paragraph against the
owner's own range. Free: a fake embedder stands in for StyleDistance, so no test needs torch,
a model download or the network."""
import json
import subprocess
import sys
import textwrap
import types

import pytest

from conftest import REPO, run, skill_text
from vela import cli, voicescore

PLUGIN = REPO / "plugin"
CLOSE = PLUGIN / "skills" / "close" / "SKILL.md"
REVIEWER = PLUGIN / "agents" / "voice-reviewer.md"

PAGE = textwrap.dedent("""\
    ---
    id: smoke
    type: decision
    title: "A page"
    ---

    # A heading

    First prose line of one paragraph,
    and its second line. ^c01

    | Contract | Calls |
    |---|---|
    | CON-003 | 2 |

    - **Owner:** @someone
    - [[CAP-014-hold-a-seat|Hold a seat]], serving G1
    1. A numbered step

    **Decision:** keep page-level locks.

    > A person's words, quoted from a capture.

    ```
    code that looks like prose
    ```

    <!-- generated:where-it-stands sha=0a1bc540: do not edit, run planner render -->
    Generated prose that render writes.
    <!-- /generated:where-it-stands -->

    ## Another heading

    The second paragraph.
    """)

# The fake embedder's world: owner examples cluster near (1, 0, 0); "near" sits among them; "far" does not.
VECTORS = {
    "owner one": (1.0, 0.00, 0.0),
    "owner two": (1.0, 0.10, 0.0),
    "owner three": (1.0, 0.20, 0.0),
    "owner four": (1.0, 0.30, 0.0),
    "owner five": (1.0, 0.40, 0.0),
    "seed one": (0.0, 0.0, 1.0),
    "seed two": (0.0, 0.1, 1.0),
    "seed three": (0.1, 0.0, 1.0),
    "Near the owner.": (1.0, 0.2, 0.0),
    "Far from the owner.": (0.0, 1.0, 0.0),
    "Middling.": (1.0, 0.5, 0.0),
}


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return [list(VECTORS[t]) for t in texts]


def example(root, folder, voice_type, number, source, text, state="active"):
    path = root / "voice" / folder / voice_type / f"VX-{voice_type}-{number:03d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: VX-{voice_type}-{number:03d}\nvoice_type: {voice_type}\nsource: {source}\n"
                    f"author: \"@owner\"\nstate: {state}\nadded: 2026-10-06\n---\n\n{text}\n", encoding="utf-8")


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    for n, word in enumerate(("one", "two", "three"), start=1):
        example(root, "examples", "decision", n, "public-seed", f"seed {word}")
    for n, word in enumerate(("one", "two", "three", "four", "five"), start=1):
        example(root, "local" if n <= 2 else "examples", "how-it-works", n, "owner" if n % 2 else "owner-edit", f"owner {word}")
    return root


@pytest.fixture
def scorer(monkeypatch, tmp_path):
    """The optional half installed and downloaded, with the fake embedder in place of the model."""
    home = tmp_path / "models"
    monkeypatch.setenv("PLANNER_VOICESCORE_HOME", str(home))
    monkeypatch.setattr(cli, "missing_dependencies", lambda: [])
    fake = FakeEmbedder()
    monkeypatch.setattr(cli, "load_styledistance", lambda path: fake)
    cli.model_dir().mkdir(parents=True)
    (cli.model_dir() / cli.MODEL_MARKER).write_text("{}", encoding="utf-8")
    return fake


def page(tmp_path, *paragraphs, name="page.md"):
    path = tmp_path / name
    path.write_text("---\nid: p\n---\n\n# Title\n\n" + "\n\n".join(paragraphs) + "\n", encoding="utf-8")
    return str(path)


# --- paragraph extraction -------------------------------------------------------------------

def test_only_prose_paragraphs_are_scored():
    found = voicescore.paragraphs(PAGE)
    assert [(p.number, p.line, p.text) for p in found] == [
        (1, 9, "First prose line of one paragraph, and its second line."),
        (2, 34, "The second paragraph."),
    ]


@pytest.mark.parametrize("skipped", [
    "| a | b |", "# Heading", "### Deep heading", "- **Owner:** @x", "* plain bullet", "2) numbered",
    "**Tested by:** EP-001", "> quoted", "<!-- a comment -->", "    indented code", "---",
])
def test_each_non_prose_line_is_skipped(skipped):
    assert voicescore.paragraphs(f"Prose before.\n\n{skipped}\n\nProse after.\n") == [
        voicescore.Paragraph(1, 1, "Prose before."), voicescore.Paragraph(2, 5, "Prose after.")]


def test_a_skipped_line_splits_a_paragraph_rather_than_joining_across_it():
    assert [p.text for p in voicescore.paragraphs("One.\n| a |\nTwo.\n")] == ["One.", "Two."]


def test_a_page_with_no_prose_is_not_scored(vault, scorer, tmp_path):
    path = tmp_path / "table.md"
    path.write_text("# Only a heading\n\n| a |\n|---|\n| 1 |\n", encoding="utf-8")
    code, out = run("voicescore", str(path), "--vault", str(vault))
    assert code == 2
    assert out.startswith("planner voicescore: not run: the file holds no prose paragraph")


# --- the owner's range ----------------------------------------------------------------------

def test_leave_one_out_measures_each_vector_against_the_centroid_of_the_others():
    spread = voicescore.leave_one_out([[1, 0], [0, 1], [1, 1]])
    assert spread[0] == pytest.approx(0.0)
    assert spread[1:] == pytest.approx([1 - 0.5 / 1.25 ** 0.5] * 2)


@pytest.mark.parametrize("distance, percentile, label", [
    (0.05, 0, "inside your range"),
    (0.10, 0, "inside your range"),
    (0.25, 38, "inside your range"),
    (0.46, 90, "inside your range"),
    (0.48, 95, "outside your range (p95)"),
    (0.50, 100, "outside your range (p100)"),
    (0.60, 101, "outside your range (p100+)"),
])
def test_a_distance_is_placed_by_percentile_of_the_range(distance, percentile, label):
    placed = voicescore.place(distance, [0.1, 0.2, 0.3, 0.4, 0.5])
    assert (placed.percentile, placed.label) == (percentile, label)
    assert placed.inside == label.startswith("inside")


def test_paragraphs_are_labeled_against_the_owner_range_never_as_a_bare_number(vault, scorer, tmp_path):
    code, out = run("voicescore", page(tmp_path, "Near the owner.", "Far from the owner."), "--vault", str(vault))
    assert code == 0
    lines = out.splitlines()
    assert lines[0].endswith("against your voice (5 owner examples).")
    assert lines[1].startswith("¶1 line 7: inside your range.")
    assert lines[2].startswith("¶2 line 9: outside your range (p100+).")
    assert "voicescore: 1 of 2 paragraphs inside your range; ¶2 outside (p100+)" in lines
    assert "0." not in out.replace("0 of", "")  # no distance is printed as a number


def test_the_summary_line_is_the_one_close_copies():
    scored = [voicescore.Scored(voicescore.Paragraph(n, n, "x"), voicescore.place(d, [0.1, 0.2, 0.3, 0.4, 0.5]))
              for n, d in ((1, 0.2), (2, 0.49), (3, 0.3), (4, 0.1))]
    assert voicescore.summary(scored) == "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p98)"


def test_owner_examples_come_from_both_folders_active_only(vault):
    example(vault, "local", "decision", 9, "owner", "owner retired", state="retired")
    example(vault, "examples", "decision", 8, "public-seed", "seed active")
    examples, unreadable = cli.voice_examples(vault)
    ref = voicescore.reference(examples)
    assert not unreadable
    assert [e.text for e in ref.examples] == ["owner one", "owner two", "owner three", "owner four", "owner five"]
    assert [e.folder for e in ref.examples][:2] == ["local", "local"]
    assert not ref.warning


# --- too few owner examples, and the seed only by name ---------------------------------------

def test_fewer_than_five_owner_examples_says_the_score_is_unreliable(vault, scorer, tmp_path):
    for n in (4, 5):
        path = next((vault / "voice" / "examples" / "how-it-works").glob(f"*-00{n}.md"))
        path.write_text(path.read_text(encoding="utf-8").replace("state: active", "state: retired"), encoding="utf-8")
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 0
    assert "against your voice (3 owner examples)" in out
    assert "UNRELIABLE: only 3 active owner examples, and a range needs at least 5." in out
    assert "seed" not in out.split("UNRELIABLE", 1)[1].split("\n", 1)[0]


def test_the_seed_is_never_used_when_owner_examples_are_missing(vault, scorer, tmp_path):
    for path in (vault / "voice").rglob("*.md"):
        if "owner" in path.read_text(encoding="utf-8").split("---")[1]:
            path.unlink()
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 2
    assert out.startswith("planner voicescore: not run: 0 active owner examples")
    assert "`--against seed` scores against the public seed instead, labeled as such." in out
    assert scorer.calls == []  # nothing was embedded, so no seed vector stood in for the owner


def test_one_owner_example_is_not_enough_to_form_a_range():
    one = [voicescore.Example("VX-a-001", "examples", "owner", "active", "owner one")]
    with pytest.raises(voicescore.NotScorable, match="1 active owner examples"):
        voicescore.reference(one)


def test_against_seed_is_labeled_as_the_seed(vault, scorer, tmp_path):
    code, out = run("voicescore", page(tmp_path, "Far from the owner."), "--vault", str(vault), "--against", "seed")
    assert code == 0
    assert "against the public seed, not your voice (3 public-seed examples)." in out
    assert "the seed's range" in out and "your range" not in out
    assert "UNRELIABLE: only 3 active public-seed examples" in out
    code, out = run("voicescore", page(tmp_path, "Far from the owner."), "--vault", str(vault), "--against", "seed", "--json")
    answer = json.loads(out)
    assert answer["against"] == "seed" and answer["examples"] == ["VX-decision-001", "VX-decision-002", "VX-decision-003"]


def test_an_unreadable_example_stops_the_score_rather_than_shrinking_the_reference(vault, scorer, tmp_path):
    (vault / "voice" / "examples" / "how-it-works" / "VX-how-it-works-099.md").write_text("no frontmatter\n", encoding="utf-8")
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 2 and "cannot read the frontmatter of voice/examples/how-it-works/VX-how-it-works-099.md" in out


# --- ranking --------------------------------------------------------------------------------

def test_rank_puts_the_draft_closest_to_the_owner_first(vault, scorer, tmp_path):
    far = page(tmp_path, "Far from the owner.", name="far.md")
    mid = page(tmp_path, "Middling.", name="mid.md")
    near = page(tmp_path, "Near the owner.", name="near.md")
    code, out = run("voicescore", "--rank", far, mid, near, "--vault", str(vault))
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == "planner voicescore --rank: 3 candidates against your voice (5 owner examples), closest first."
    assert lines[1] == f"1. {near}: inside your range"
    assert lines[2].startswith(f"2. {mid}: outside your range (p")
    assert lines[3] == f"3. {far}: outside your range (p100+)"
    answer = json.loads(run("voicescore", "--rank", far, near, "--vault", str(vault), "--json")[1])
    assert [r["file"] for r in answer["ranked"]] == [near, far]


def test_rank_needs_two_candidates(vault, scorer, tmp_path):
    code, out = run("voicescore", "--rank", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 2 and "at least two candidate files" in out


# --- the optional dependency and the model --------------------------------------------------

def test_missing_dependency_exits_2_with_the_install_hint_and_size(vault, monkeypatch, tmp_path):
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: None)
    for argv in (["voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault)], ["voicescore", "setup"]):
        code, out = run(*argv)
        assert code == 2
        assert out.startswith("planner voicescore: not run: sentence-transformers and torch not installed.")
        assert "pip install sentence-transformers" in out and "about 1–2 GB" in out


def test_missing_model_exits_2_and_suggests_setup(vault, monkeypatch, tmp_path):
    monkeypatch.setenv("PLANNER_VOICESCORE_HOME", str(tmp_path / "empty"))
    monkeypatch.setattr(cli, "missing_dependencies", lambda: [])
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 2
    assert "model is not downloaded yet" in out and "Run planner voicescore setup once" in out
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault), "--json")
    assert json.loads(out)["ran"] is False


def test_setup_says_it_uses_the_network_before_it_downloads(monkeypatch, tmp_path):
    monkeypatch.setenv("PLANNER_VOICESCORE_HOME", str(tmp_path / "models"))
    monkeypatch.setattr(cli, "missing_dependencies", lambda: [])
    seen = []

    def download(target):
        seen.append(target)
        target.mkdir(parents=True)
    monkeypatch.setattr(cli, "download_styledistance", download)
    out_lines = []

    class Out:
        def write(self, text):
            out_lines.append((len(seen), text))

        def flush(self):
            pass
    code = cli.main(["voicescore", "setup"], out=Out())
    assert code == 0 and seen == [cli.model_dir()]
    announced = "".join(t for n, t in out_lines if n == 0)
    assert "the only planner command that uses the network" in announced
    assert voicescore.MODEL_ID in announced and voicescore.MODEL_REVISION[:12] in announced
    assert (cli.model_dir() / cli.MODEL_MARKER).is_file()
    code, out = run("voicescore", "setup", "--json")
    assert code == 0 and json.loads(out)["downloaded"] is False and len(seen) == 1


def test_a_failed_download_leaves_the_model_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("PLANNER_VOICESCORE_HOME", str(tmp_path / "models"))
    monkeypatch.setattr(cli, "missing_dependencies", lambda: [])

    def download(target):
        target.mkdir(parents=True)
        raise OSError("proxy refused")
    monkeypatch.setattr(cli, "download_styledistance", download)
    code, out = run("voicescore", "setup")
    assert code == 2 and "not run: the download failed: proxy refused" in out
    assert not (cli.model_dir() / cli.MODEL_MARKER).exists()


def test_the_model_is_pinned_to_one_revision():
    assert voicescore.MODEL_ID == "StyleDistance/styledistance"
    assert len(voicescore.MODEL_REVISION) == 40 and int(voicescore.MODEL_REVISION, 16)
    assert cli.model_dir().name == voicescore.MODEL_REVISION


def test_scoring_loads_the_model_in_offline_mode(monkeypatch, tmp_path):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    seen = {}

    class SentenceTransformer:
        def __init__(self, path, device):
            seen.update(path=path, device=device, hub=cli.os.environ.get("HF_HUB_OFFLINE"),
                        transformers=cli.os.environ.get("TRANSFORMERS_OFFLINE"))

        def encode(self, texts, **kwargs):
            return [[1.0, 0.0] for _ in texts]
    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=SentenceTransformer))
    embed = cli.load_styledistance(tmp_path / "m")
    assert seen == {"path": str(tmp_path / "m"), "device": "cpu", "hub": "1", "transformers": "1"}
    assert embed(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]


# --- the cache ------------------------------------------------------------------------------

def test_the_cache_key_is_the_text_and_the_exact_model():
    key = voicescore.cache_key("A paragraph.")
    assert len(key) == 64 and key == voicescore.cache_key("A paragraph.")
    assert key != voicescore.cache_key("A paragraph!")
    assert key != voicescore.cache_key("A paragraph.", revision="0" * 40)


def git_init(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True, timeout=60)


def test_vectors_are_cached_under_dot_git_and_reused(vault, scorer, tmp_path):
    git_init(vault)
    path = page(tmp_path, "Near the owner.")
    assert run("voicescore", path, "--vault", str(vault))[0] == 0
    folder = vault / ".git" / "planner-voicescore"
    assert (folder / f"{voicescore.cache_key('Near the owner.')}.json").is_file()
    assert len(list(folder.glob("*.json"))) == 6
    first = len(scorer.calls)
    code, out = run("voicescore", path, "--vault", str(vault))
    assert code == 0 and len(scorer.calls) == first  # every vector came from the cache
    assert f"cache: {folder.resolve()}" in out
    status = subprocess.run(["git", "-C", str(vault), "status", "--porcelain", "--ignored"], capture_output=True, text=True, timeout=60).stdout
    assert "planner-voicescore" not in status


def test_a_fully_cached_run_never_loads_the_model(vault, scorer, monkeypatch, tmp_path):
    git_init(vault)
    path = page(tmp_path, "Near the owner.")
    run("voicescore", path, "--vault", str(vault))
    loads = []
    monkeypatch.setattr(cli, "load_styledistance", lambda p: loads.append(p) or scorer)
    assert run("voicescore", path, "--vault", str(vault))[0] == 0
    assert loads == []


def test_a_corrupt_cache_file_is_embedded_again(vault, scorer, tmp_path):
    git_init(vault)
    path = page(tmp_path, "Near the owner.")
    run("voicescore", path, "--vault", str(vault))
    bad = vault / ".git" / "planner-voicescore" / f"{voicescore.cache_key('Near the owner.')}.json"
    bad.write_text("{not json", encoding="utf-8")
    calls = len(scorer.calls)
    assert run("voicescore", path, "--vault", str(vault))[0] == 0
    assert scorer.calls[calls:] == [["Near the owner."]]
    assert json.loads(bad.read_text(encoding="utf-8")) == list(VECTORS["Near the owner."])


def test_outside_git_the_cache_is_off_and_says_so(vault, scorer, tmp_path):
    code, out = run("voicescore", page(tmp_path, "Near the owner."), "--vault", str(vault))
    assert code == 0 and "cache: off, the vault is not a git repository" in out


def test_json_carries_labels_and_the_summary(vault, scorer, tmp_path):
    code, out = run("voicescore", page(tmp_path, "Near the owner.", "Far from the owner."), "--vault", str(vault), "--json")
    answer = json.loads(out)
    assert code == 0 and answer["ran"] and answer["reliable"]
    assert answer["summary"] == "voicescore: 1 of 2 paragraphs inside your range; ¶2 outside (p100+)"
    assert [p["label"] for p in answer["paragraphs"]] == ["inside your range", "outside your range (p100+)"]
    assert answer["revision"] == voicescore.MODEL_REVISION


# --- the rest of the toolkit stays Python plus PyYAML ----------------------------------------

def test_check_works_when_the_optional_dependency_cannot_be_imported(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # import raises ImportError
    monkeypatch.setitem(sys.modules, "torch", None)
    code, out = run("check", "--vault", str(REPO / "examples" / "unified-booking"), "--today", "2026-11-20")
    assert code == 0 and "0 errors," in out


def test_importing_the_cli_never_imports_the_optional_dependency():
    script = ("import sys; sys.path.insert(0, sys.argv[1]); import vela.cli; "
              "print(sorted(m for m in ('sentence_transformers', 'torch', 'huggingface_hub', 'numpy') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", script, str(PLUGIN / "lib")], capture_output=True, text=True, check=True, timeout=60).stdout
    assert out.strip() == "[]"


def test_only_the_cli_touches_the_disk_or_network():
    source = (PLUGIN / "lib" / "vela" / "voicescore.py").read_text(encoding="utf-8")
    for word in ("open(", "pathlib", "import os", "subprocess", "sentence_transformers", "huggingface", "urllib", "time."):
        assert word not in source, word


# --- the close skill ------------------------------------------------------------------------

def voice_review():
    return (PLUGIN / "skills" / "close" / "VOICE-REVIEW.md").read_text(encoding="utf-8")  # read by close at the voice review


def test_close_scores_drafts_only_when_available_and_never_gates_on_it():
    part = voice_review()
    assert "planner voicescore" in part
    assert "at least 5 active `owner` and `owner-edit` examples" in part
    assert "information, not a gate" in part
    assert "Never block, rewrite or skip a paragraph because of its voicescore" in part
    assert '"voicescore: not run (<reason>)"' in part
    assert "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p96)" in part


def test_close_still_runs_the_voicecheck_fact_guard_unchanged():
    part = voice_review()
    assert 'python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)' in part
    assert "Never commit a rewrite voicecheck could not check." in part


def test_the_pr_body_reports_voicescore_in_the_voice_review_line():
    close = skill_text("close")
    line = next(l for l in close.splitlines() if l.strip().startswith("- **Voice review:**"))
    assert "voicescore" in line and "not run (<reason>)" in line


def test_the_reviewer_may_read_a_voicescore_as_a_hint_only():
    body = REVIEWER.read_text(encoding="utf-8")
    assert "voicescore" in body and "a hint" in body
    assert "Never flag a paragraph only because its voicescore is outside the range" in body


# --- the docs -------------------------------------------------------------------------------

def test_conventions_say_voicescore_is_optional_in_every_copy():
    copies = [REPO / "template" / "CONVENTIONS.md", REPO / "tests" / "stub-conventions" / "CONVENTIONS.md",
              REPO / "examples" / "unified-booking" / "CONVENTIONS.md"]
    texts = {p.read_bytes() for p in copies}
    assert len(texts) == 1
    text = copies[0].read_text(encoding="utf-8")
    assert "`planner voicescore" in text and "optional" in text.split("`planner voicescore", 1)[1].split("\n", 1)[0]


def test_readme_explains_install_setup_offline_and_privacy():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Optional: voicescore", 1)[1].split("\n## ", 1)[0]
    for words in ("pip install sentence-transformers", "1–2 GB", "planner voicescore setup", "one-off download",
                  "offline", "never leaves this machine", "not a gate"):
        assert words in section, words
