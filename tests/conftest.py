"""Shared test helpers. Tests build broken copies of a vault in tmp_path."""
import contextlib
import fcntl
import io
import os
import pathlib
import pickle
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugin" / "lib"))

MINI = REPO / "tests" / "fixtures" / "mini"
FINDING = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+): (?P<code>[EW]\d{3}) ")


def run(*argv):
    """Run the vela CLI in-process. Returns (exit code, output text)."""
    from vela import cli
    out = io.StringIO()
    code = cli.main(list(argv), out=out)
    return code, out.getvalue()


# Findings about the example's own content that no rule under test is about: its decided items record no Why yet
# (design 20: the example carries no reasons in the lead's words, and none are invented for it), and its flows were
# drawn before the flow check's strict form, so each slice is not fully checked (W391) until a boundary redraws them.
OPEN_IN_THE_EXAMPLE = ("W390", "W391")


def findings(output, keep_open=False):
    """[(code, path)] for every finding line in check output, except those the example leaves open on purpose."""
    found = [(m["code"], m["path"]) for m in map(FINDING.match, output.splitlines()) if m]
    return found if keep_open else [f for f in found if f[0] not in OPEN_IN_THE_EXAMPLE]


def edit(path, old, new):
    """Replace `old` with `new` in a file. `old` must occur exactly once."""
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in {path}, expected exactly 1"
    path.write_text(text.replace(old, new), encoding="utf-8")


@pytest.fixture
def mini(tmp_path):
    """A fresh copy of the mini vault."""
    dest = tmp_path / "mini"
    shutil.copytree(MINI, dest)
    return dest


def check(vault, today="2026-01-15"):
    return run("check", "--vault", str(vault), "--today", today)


@pytest.fixture(autouse=True)
def isolate_git_config(tmp_path, monkeypatch):
    """Isolate each test from the developer's global git config by setting environment variables.
    This ensures tests don't fail under global settings like commit signing or custom hooks."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    # Clear git-related env vars that might interfere
    for var in ["GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"]:
        monkeypatch.delenv(var, raising=False)


def pytest_sessionstart(session):
    _BASETEMP.append(session.config._tmp_path_factory.getbasetemp())


def pytest_configure(config):
    """Register custom markers, and under xdist schedule by group (see SHARED_BUILDS)."""
    config.addinivalue_line("markers", "browser: browser smoke tests (require Chrome; slow)")
    if getattr(config.option, "dist", "no") == "load":
        config.option.dist = "loadgroup"  # plain `load` with every test of a group kept on one worker
    if hasattr(config, "workerinput"):
        config.option.loadgroup = True  # a worker learns the mode from its own reading of the options, not the controller's


# Fixtures that build something costly, and the xdist group their tests share. `built_once` already builds each of them
# once per session, but a worker that asks while another is building sits idle behind the lock for up to two minutes;
# grouped, the tests that need the build all run on the worker that builds it, and the others take other work.
SHARED_BUILDS = {"full_run": "sim-full-run", "complete_run": "sim-complete-run", "plugin_leaks": "seal-plugin-leaks"}


@pytest.hookimpl(tryfirst=True)  # before xdist's own hook, which reads the group marks to schedule by them
def pytest_collection_modifyitems(config, items):
    for item in items:
        for fixture, group in SHARED_BUILDS.items():
            if fixture in getattr(item, "fixturenames", ()):
                item.add_marker(pytest.mark.xdist_group(group))


# ---------------------------------------------------------------- builds shared across the whole session
# A module fixture runs once per xdist worker that needs it, so a 135 s stub run was built on three workers at once
# (Computational Friction: the same result paid for N times). `built_once` builds each distinct thing one time per
# pytest session, behind a file lock every worker can see, and hands every test the same read-only folder. A test that
# changes what it is given copies it first (shutil.copytree) so tests stay independent.

_FACTORY = []  # the session's tmp_path_factory, for helpers that are plain functions and cannot ask for a fixture


@pytest.fixture(autouse=True, scope="session")
def _remember_tmp_path_factory(tmp_path_factory):
    _FACTORY[:] = [tmp_path_factory]


def _shared_root(tmp_path_factory):
    base = (tmp_path_factory or _FACTORY[0]).getbasetemp()
    root = (base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base) / "shared-builds"
    root.mkdir(exist_ok=True)
    return root


def built_once(tmp_path_factory, key, build):  # tmp_path_factory may be None once a test has run
    """The folder `build(folder)` filled, built on the first request in this session and reused after. `key` names
    the inputs: two requests with the same key must want the same result. The folder is read-only to callers."""
    root = _shared_root(tmp_path_factory)
    folder, done = root / key, root / f"{key}.done"
    with open(root / f"{key}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not done.exists():
            shutil.rmtree(folder, ignore_errors=True)
            folder.mkdir()
            build(folder)
            done.write_text("ok", encoding="utf-8")
    return folder


def value_built_once(tmp_path_factory, key, produce):
    """Like built_once for a plain picklable value that `produce()` returns."""
    def build(folder):
        (folder / "value.pickle").write_bytes(pickle.dumps(produce()))
    return pickle.loads((built_once(tmp_path_factory, key, build) / "value.pickle").read_bytes())


def copy_of(shared, destination):
    """A private copy of a shared folder, for a test that is going to change it."""
    shutil.copytree(shared, destination)
    return destination


def skill_text(name):
    """A skill's SKILL.md and the files beside it that it sends the model to, read together. A rule that moved to a file
    read only at the step that needs it is still the skill's rule."""
    folder = REPO / "plugin" / "skills" / name
    parts = [(folder / "SKILL.md").read_text(encoding="utf-8")]
    parts += [path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.md")) if path.name != "SKILL.md"]
    return "\n".join(parts)


@pytest.fixture(autouse=True)
def _no_installed_plugins(tmp_path_factory, monkeypatch):
    """No test may find a vela plugin installed on the machine that runs it (~/.claude/plugins): point the plugins root at
    an empty folder. A test that wants an installed copy sets CLAUDE_CODE_PLUGIN_CACHE_DIR itself."""
    monkeypatch.setenv("CLAUDE_CODE_PLUGIN_CACHE_DIR", str(tmp_path_factory.mktemp("no-plugins")))


_CHROME_PROFILES = []
_BASETEMP = []  # pytest's base temp for this process, set at session start (scratch_root)


def scratch_root():
    """Where the suite's own temp folders go: under pytest's base temp for this run, so the retention setting in
    pytest.ini sweeps them even when a run is killed before its cleanup. Folders made with a bare tempfile.mkdtemp
    lived in $TMPDIR forever whenever a run was cut short: 168 Chrome profiles (50-80 MB each) and dozens of published
    caches filled the disk on 2026-10-21 and failed whole gate runs."""
    import tempfile
    return str(_BASETEMP[0]) if _BASETEMP else tempfile.gettempdir()


def chrome_profile():
    """A `--user-data-dir` flag naming a fresh profile folder for one headless Chrome launch. Without it, parallel
    launches share the default profile, and while the user's own Chrome holds that profile's lock a headless one can
    hang with no output until the test's timeout (the browser-test flakes under `-n auto`, E86)."""
    import tempfile
    folder = tempfile.mkdtemp(prefix="vela-chrome-", dir=scratch_root())
    _CHROME_PROFILES.append(folder)
    return f"--user-data-dir={folder}"


def pytest_unconfigure(config):
    for folder in _CHROME_PROFILES:
        shutil.rmtree(folder, ignore_errors=True)  # nosemgrep: except-pass -- best-effort cleanup of temp profiles


ATTEMPTS = 3


class ChromeStalled(Exception):
    """One headless Chrome launch outlasted its share of the timeout."""


def _launch_chrome_once(cmd, timeout):
    import signal
    import subprocess
    import tempfile
    import time
    started = time.monotonic()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdout=out, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                out.seek(0, os.SEEK_END)
                raise ChromeStalled(f"did not exit within {timeout:.0f}s (waited {time.monotonic() - started:.1f}s, "
                                    f"{out.tell()} bytes of DOM written)") from None
        finally:
            with contextlib.suppress(ProcessLookupError):  # the whole group may already be gone, which is the goal
                os.killpg(proc.pid, signal.SIGKILL)  # group id is the main pid (start_new_session)
            proc.wait()
        out.seek(0)
        err.seek(0)
        dom = out.read().decode("utf-8", errors="replace")
        if proc.returncode != 0:
            sys.stderr.write(f"headless Chrome exited {proc.returncode}: {cmd}\n{err.read().decode('utf-8', errors='replace')[-500:]}\n")
        return proc.returncode, dom


def run_chrome(cmd, timeout):
    """Run one headless Chrome launch and return (returncode, dom text). Chrome's output goes to temp files, not pipes,
    and only the main process is waited on. With a pipe, Chrome can dump the DOM and exit while a leftover helper
    keeps the pipe open, so `communicate` waits out the whole timeout for an EOF that never comes (E87). Chrome runs in
    its own process group, and the group is killed after the main process ends so no helper lingers.
    Separately, under load a launch sometimes stalls with an idle Chrome and 0 bytes written, however long it is
    given (seen: a renderer alive, nothing happening). A healthy launch takes seconds, so `timeout` is split into
    ATTEMPTS equal shares: a stalled share is killed, printed to stderr, and the launch tried again. When every share
    stalls this raises TimeoutError naming the command and each stall; it never returns empty output."""
    share = timeout / ATTEMPTS
    stalls = []
    for attempt in range(1, ATTEMPTS + 1):
        if attempt > 1:  # the stalled attempt may have saved page state (localStorage) in its profile
            cmd = [chrome_profile() if arg.startswith("--user-data-dir=") else arg for arg in cmd]
        try:
            return _launch_chrome_once(cmd, share)
        except ChromeStalled as stall:
            stalls.append(f"attempt {attempt}: {stall}")
            sys.stderr.write(f"E87: headless Chrome stalled ({stalls[-1]}); {'trying again' if attempt < ATTEMPTS else 'giving up'}\n")
    raise TimeoutError(f"headless Chrome stalled on every attempt ({'; '.join(stalls)}): {cmd}")
