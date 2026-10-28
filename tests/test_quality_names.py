"""QG-NAME: vague function, class and module names."""
import ast
import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import quality_names


def names(src, path="plugin/lib/vela/x.py"):
    return [f.message.split(":")[0] for f in quality_names.vague_names(path, ast.parse(src))]


def test_vague_names_are_found_and_domain_words_pass():
    src = "def common(p): pass\ndef process_rows(r): pass\nclass PageManager: pass\n" \
          "def handle(v): pass\ndef lead_handle(): pass\nclass Handler: pass\ndef common_target(): pass\n" \
          "class Page:\n    def do_GET(self): pass\n"
    assert names(src) == ["common", "process_rows", "PageManager"]


def test_a_vague_module_name_is_found():
    assert names("", "tools/utils.py") == ["utils"]
