import pathlib, shutil, sys

# ruleid: plugin-imports-only-plugin
from tests.conftest import REPO  # noqa: F401 - semgrep rule example
# ruleid: plugin-imports-only-plugin
import prototypes.explorer.build  # noqa: F401 - semgrep rule example
# ok: plugin-imports-only-plugin
from planner import schema  # noqa: F401 - semgrep rule example

# ok: plugin-imports-only-plugin
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
# ruleid: plugin-imports-only-plugin
sys.path.insert(0, "/repo/prototypes/explorer")

USER_SKILLS = pathlib.Path.home() / ".claude" / "skills"

def copy_in(repo, skill):
    # ok: no-write-under-home-claude
    shutil.copytree(USER_SKILLS / skill, repo / ".claude" / "skills" / skill)

def install(src):
    target = pathlib.Path.home() / ".claude" / "skills" / "planner"
    # ruleid: no-write-under-home-claude
    shutil.copytree(src, target)
    # ruleid: no-write-under-home-claude
    (target / "x.md").write_text("hi")
