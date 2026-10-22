"""The codelab under docs/codelab/. The Violation these tests hold off is a tutorial that drifts from the plan it teaches
or lets a reader finish a step without proof: the committed page matches its Markdown, every step ends in a checkpoint,
every middle step folds a "Why this step" and a "Stuck?", every link and image lands on a real file, and the page
works from file:// with no network."""
import re
import sys

import pytest

from conftest import REPO

DOCS = REPO / "docs"
CODELAB = DOCS / "codelab"
sys.path.insert(0, str(DOCS))
import render_codelab  # noqa: E402
import render_method  # noqa: E402


@pytest.fixture(scope="module")
def built():
    return render_codelab.build()


def steps_of(page):
    return re.findall(r'<section class="step" id="step-(\d+)".*?</section>', page, re.S), re.findall(
        r'(<section class="step" id="step-\d+".*?</section>)', page, re.S)


def test_committed_page_matches_its_markdown(built):
    assert (CODELAB / "index.html").read_text(encoding="utf-8") == built, "run python3 docs/render_codelab.py"


def test_the_page_has_the_thirteen_steps_in_order(built):
    numbers, _ = steps_of(built)
    assert numbers == [str(n) for n in range(1, 14)]


def test_every_step_has_a_checkpoint_and_the_middle_ones_a_why_and_a_stuck(built):
    _, sections = steps_of(built)
    for index, section in enumerate(sections):
        assert 'class="cl cl-checkpoint"' in section, f"step {index + 1}"
        if 0 < index < len(sections) - 1:
            assert "<summary>Why this step</summary>" in section, f"step {index + 1}"
            assert "<summary>Stuck?</summary>" in section, f"step {index + 1}"


def test_a_step_without_a_checkpoint_is_refused():
    with pytest.raises(render_codelab.StepError, match="no checkpoint"):
        render_codelab.check_step("02-x.md", ["text"], 1, 3)


def test_a_middle_step_without_a_stuck_fold_is_refused():
    with pytest.raises(render_codelab.StepError, match="Stuck"):
        render_codelab.check_step("02-x.md", ["::: checkpoint", "ok", ":::", "::: fold Why this step", "x", ":::"], 1, 3)


def test_the_times_add_up_to_the_total_the_page_states(built):
    minutes = [int(m) for m in re.findall(r'data-min="(\d+)"', built)]
    assert f"About {sum(minutes)} minutes." in built
    assert f'<span id="timeleft">{sum(minutes)} min left</span>' in built


def test_every_link_and_image_lands_on_a_real_file(built):
    missing = []
    for target in re.findall(r'(?:href|src)="([^"#:]+)(?:#[^"]*)?"', built):
        home = DOCS / "site" / "index.html" if target == "../index.html" else CODELAB / target
        if not home.resolve().exists():
            missing.append(target)
    assert not missing, missing


def test_links_into_the_method_site_land_on_a_real_heading_or_card(built):
    method = render_method.build_all()
    bad = []
    for page, anchor in re.findall(r'href="\.\./method/([\w-]+)\.html#([^"]+)"', built):
        if f'id="{anchor}"' not in method[page]:
            bad.append(f"{page}#{anchor}")
    assert not bad, bad


def test_the_page_never_loads_anything_from_the_network(built):
    assert not re.search(r'(?:src|href)="https?://', built)
    assert "http" not in (CODELAB / "codelab.css").read_text(encoding="utf-8")


def test_the_page_carries_the_shared_theme_toggle(built):
    assert 'id="theme-toggle"' in built
    assert built.count('"vela-theme"') == 2
    assert built.index("localStorage.getItem") < built.index("<body")


def test_the_landing_page_and_the_method_home_link_to_it():
    assert 'href="codelab/index.html"' in (DOCS / "site" / "index.html").read_text(encoding="utf-8")
    assert 'href="../codelab/index.html"' in render_method.build_all()["index"]


def test_no_catch_in_the_codelab_script_is_empty_or_on_one_line():
    script = (CODELAB / "codelab.js").read_text(encoding="utf-8")
    assert not re.search(r"catch \(\w+\) \{[^\n]*\}", script)


def test_every_arrow_points_at_a_marker_that_exists(built):
    for target in set(re.findall(r'marker-end="url\(#([^)]+)\)"', built)):
        assert f'<marker id="{target}"' in built
