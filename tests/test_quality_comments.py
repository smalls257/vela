"""QG-CMT-*: what-comments, restating docstrings, unexplained suppressions."""
import ast
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import quality_comments


def test_a_what_comment_is_found():
    src = "# read the vault pages\npages = read_vault_pages(root)\n"
    assert [f.line for f in quality_comments.what_comments("x.py", src)] == [1]


def test_a_why_comment_that_shares_words_passes():
    src = ("# git says ~/Code while Claude may say ~/code, so a string prefix test skips every edit\n"
           "base = next((p for p in path.parents if os.path.samefile(p, root)), None)\n")
    assert quality_comments.what_comments("x.py", src) == []


def test_banners_pass():
    assert quality_comments.what_comments("x.py", "# --- the cache key ---\ndef cache_key(text): pass\n") == []


def test_a_restating_docstring_is_found_and_a_why_docstring_passes():
    bad = ast.parse('def parse_page(page):\n    """Parses the page."""\n')
    good = ast.parse('def parse_page(page):\n    """The front matter, or {} when it has none: a page without it is still a page."""\n')
    assert len(quality_comments.restating_docstrings("x.py", bad)) == 1
    assert quality_comments.restating_docstrings("x.py", good) == []


@pytest.mark.parametrize("line,found", [
    ("x = 1  # noqa: E731\n", 1), ("import a  # noqa: E402 -- after the sys.path insert above\n", 0),
    ("try:  # nosemgrep: except-pass\n", 1), ("try:  # nosemgrep: except-pass -- a stray temp file is harmless\n", 0),
    ("def f():  # lizard forgives\n", 1), ("import a  # noqa: S506 (a SafeLoader subclass)\n", 0),
])
def test_suppressions_need_a_reason(line, found):
    assert len(quality_comments.unexplained_suppressions("x.py", line)) == found


def test_content_words_split_identifiers_and_drop_filler():
    assert quality_comments.content_words("returns the pageCount of read_vault") == ["page", "count", "read", "vault"]
    assert quality_comments.same_word("parses", "parse") and not quality_comments.same_word("is", "isle")
