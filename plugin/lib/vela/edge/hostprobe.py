"""What this host gives a session (git, network, `gh`, hooks, `!` injection), asked once and written to
`.vela/host.json` (CLI/skill overhaul plan 7.1-7.3, `vela where --probe`).

The Violation this module exists to prevent is the Black Box: before it, nobody knew what a Cowork session could do
until a step failed at push, and the first move against a Black Box is a sensor, not a guess. Its second is the Silent
Fallback: plugin hooks are documented for Cowork but reported not to fire there (#27398, #63360), and a hook that
didn't run looks exactly like one that passed. So the SessionStart hook leaves `.vela/hooks-active` and a PreToolUse
canary on this very command leaves `.vela/hook-canary`; the probe says "no" plainly when either is missing or belongs
to another session, and nothing downstream may treat a missing marker as a pass.

Every check answers `yes`, `no` or `couldn't tell`, and a check that timed out or could not be tried is
`couldn't tell` with the reason, never `yes` and never left out. That is why a `gh` that hangs is reported, not
skipped.

Shape: the judging half (`*_row`, `host_record`, `missing`, `stance`) is pure and takes what was observed; the
gathering half (`run`, `gather`, `write_host`) runs the programs and touches the disk. They share a file because the
plan gives the probe one module; `stance` is what `session start`, `close gate` and `close push` import, and it
reads only the dict.
"""
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass

from vela.edge import atomic

YES, NO, UNSURE = "yes", "no", "couldn't tell"
PYTHON_FLOOR = (3, 9)  # the launcher refuses below this (plugin/scripts/vela), so no gate can run there
TIMEOUT = 10  # plan 7.1: network and gh checks get ten seconds, so a dead network costs seconds, not a hung session
CANARY_FRESH = 600  # the canary fires just before this command; one older than this belongs to an earlier probe
HOST_FILE = ".vela/host.json"
ACTIVE_FILE = ".vela/hooks-active"
CANARY_FILE = ".vela/hook-canary"
INSIDE_MARKER = ".vela/probe-marker"
OUTSIDE_MARKER = ".cache/vela/probe-marker"  # under the home folder: outside every working folder
# A credential prompt would hang a probe with no terminal; it must fail fast and say so instead.
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true", "GH_PROMPT_DISABLED": "1",
             "NO_COLOR": "1"}

LABELS = {
    "skill_dir": "The skill's folder was filled in",
    "plugin_root": "The plugin's folder was filled in",
    "python": "Python 3.9 or later",
    "yaml": "The plugin's own YAML reader loads",
    "git": "git runs in this folder",
    "network": "This folder can reach its shared copy",
    "gh": "GitHub's command line is signed in",
    "hooks": "Plugin hooks run",
    "injection": "Skill lines that start with ! run",
    "folder": "Only the working folder keeps files between sessions",
}
NEEDED = ("python", "yaml", "git", "network", "gh")  # what an owner's session needs, close and push included
NEEDED_BY_READER = ("python", "yaml")  # a published copy uses no git: it reads, drafts and proposes


class ProbeFailed(Exception):
    """The probe itself could not finish (its record could not be written). Exit 2."""


@dataclass(frozen=True)
class Ran:
    """How one program call went: `ok`, `failed`, `missing` (not on PATH) or `timeout`, with its output."""
    how: str
    out: str = ""
    err: str = ""

    def first_line(self):
        text = (self.err or self.out).strip()
        return text.splitlines()[0] if text else ""


@dataclass(frozen=True)
class Row:
    key: str
    answer: str
    meaning: str  # plain words for the lead: no paths, no program output
    detail: str = ""  # what was seen (paths, git's message), for the default mode, the JSON and bug reports

    @property
    def label(self):
        return LABELS[self.key]

    def as_json(self):
        return {**asdict(self), "label": self.label}


# The judging half: pure.

def filled_row(key, value, what):
    """Whether the host substituted `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PLUGIN_ROOT}` before the skill ran: a literal
    `${` or an empty value is `no`, since a skill that relied on it would build a path to nowhere."""
    if value is None:
        return Row(key, UNSURE, f"The skill didn't pass the {what} value, so this wasn't checked.")
    if not value.strip():
        return Row(key, NO, f"The host left the {what} value empty, so skills can't use it to find vela.")
    if "${" in value:
        return Row(key, NO, f"The host left the {what} value unfilled, so skills can't use it to find vela.", value)
    return Row(key, YES, f"The host filled in the {what} value.", value)


def python_row(version):
    shown = ".".join(str(part) for part in version[:3])
    if tuple(version[:2]) >= PYTHON_FLOOR:
        return Row("python", YES, f"Python {shown} is here; vela needs 3.9 or later.")
    return Row("python", NO, f"Python {shown} is older than 3.9, so vela can't run its checks here.")


def yaml_row(yaml_file, lib_dir):
    """The launcher puts the plugin's lib/ first so every machine reads YAML the same way; a copy loaded from
    anywhere else means that promise failed."""
    if not yaml_file:
        return Row("yaml", NO, "The plugin's own YAML reader didn't load, so vela can't read the vault.")
    if pathlib.Path(yaml_file).resolve().is_relative_to(pathlib.Path(lib_dir).resolve()):  # 3.9 has it: the floor
        return Row("yaml", YES, "The plugin's own YAML reader loads.", yaml_file)
    return Row("yaml", NO, "A YAML reader from elsewhere on this machine loaded instead of the plugin's own.",
               yaml_file)


def git_row(version, toplevel, has_dot_git, reader):
    if version.how == "missing":
        return Row("git", NO, "git isn't installed here.")
    if version.how != "ok":
        return Row("git", NO, "git is here but didn't run.", version.first_line())
    if reader:
        return Row("git", YES, "git runs. This is your copy, so vela uses no git in it.", version.out.strip())
    if toplevel.how == "ok":
        return Row("git", YES, "git runs, and this folder is a git repo.", version.out.strip())
    if has_dot_git:
        return Row("git", NO, "This folder is a git repo, but git can't work in it here.", toplevel.first_line())
    return Row("git", NO, "git runs, but this folder isn't a git repo.", toplevel.first_line())


def network_row(git, origin, remote, reader, timeout):
    if reader:
        return Row("network", UNSURE, "A published copy sends nothing with git, so this wasn't tried.")
    if git.answer != YES:
        return Row("network", UNSURE, "git can't run in this folder, so the shared copy wasn't tried.")
    if origin.how != "ok":
        return Row("network", UNSURE, "This folder has no shared copy set up (no remote called origin).")
    if remote.how == "ok":
        return Row("network", YES, "The shared copy answered, so sessions can be sent.", origin.out.strip())
    if remote.how == "timeout":
        return Row("network", UNSURE, f"The shared copy didn't answer within {timeout} seconds.", origin.out.strip())
    return Row("network", NO, "The shared copy couldn't be reached or refused the sign-in.", remote.first_line())


def gh_row(auth, login, timeout):
    """`gh` opens the pull request at close. A `gh` that hangs is `couldn't tell`, never a quiet yes."""
    if auth.how == "missing":
        return Row("gh", NO, "GitHub's command line isn't installed here, so close can't open the pull request.")
    if auth.how == "timeout":
        return Row("gh", UNSURE, f"GitHub's command line gave no answer within {timeout} seconds.")
    if auth.how != "ok":
        return Row("gh", NO, "GitHub's command line is here but not signed in.", auth.first_line())
    if login.how == "ok" and login.out.strip():
        return Row("gh", YES, "GitHub's command line is signed in.", f"signed in as {login.out.strip()}")
    if login.how == "timeout":
        return Row("gh", UNSURE, f"Signed in, but GitHub gave no answer within {timeout} seconds.")
    return Row("gh", NO, "Signed in, but GitHub wouldn't say who you are.", login.first_line())


def hooks_row(active, canary, canary_age, in_session):
    """Both markers must belong to this session: the canary fires just before this command, and the SessionStart
    marker must carry the same session id. A marker left by an earlier session proves nothing about this one."""
    fresh = canary is not None and canary_age is not None and canary_age <= CANARY_FRESH
    same = fresh and active is not None and active.get("session_id") and \
        active.get("session_id") == canary.get("session_id")
    if same:
        return Row("hooks", YES, "Both plugin hooks ran in this session.")
    if fresh:
        return Row("hooks", NO, "The hook before each command ran, but the session-start hook didn't run for this "
                                "session. Close checks everything itself.")
    if active is not None:
        return Row("hooks", NO, "A session-start marker is here, but the hook before this command didn't run, so "
                                "hooks can't be relied on here. Close checks everything itself.")
    if not in_session:
        return Row("hooks", UNSURE, "This ran outside a Claude session, where plugin hooks never run.")
    return Row("hooks", NO, "No plugin hook left its marker, so hooks don't run here. Close checks everything itself.")


def injection_row(value):
    if value is None:
        return Row("injection", UNSURE, "The skill didn't say whether its ! line ran.")
    if value == YES:
        return Row("injection", YES, "The host ran the skill's ! line before the skill started.")
    return Row("injection", NO, "The host showed the skill's ! line as text, so skills run those commands themselves.")


def folder_row(inside_before, outside_before):
    """Told from markers the previous probe left: one inside the working folder, one in the home folder. Only a
    second run can tell, so the first says so instead of guessing."""
    if outside_before:
        return Row("folder", NO, "A file left outside this folder by an earlier check was still there, so other "
                                 "folders keep files too.")
    if inside_before:
        return Row("folder", YES, "Only this folder kept the file an earlier check left, so keep the vault's work in "
                                  "this folder.")
    return Row("folder", UNSURE, "This is the first check here. Run it again in a later session to tell.")


def missing(rows, reader):
    """The needed rows that are not a plain yes, in order: what stops a full session here."""
    needed = NEEDED_BY_READER if reader else NEEDED
    return [row.key for row in rows if row.key in needed and row.answer != YES]


def host_record(rows, python_version, git_repo, reader, checked):
    """The `.vela/host.json` dict: one answer per field, plus what `stance` needs to tell a broken git from none."""
    answers = {row.key: row.answer for row in rows}
    seen = {row.key: row.detail for row in rows if row.key in ("skill_dir", "plugin_root") and row.detail}
    return {"git": answers["git"], "network": answers["network"], "gh": answers["gh"],
            "python": ".".join(str(part) for part in python_version[:3]), "hooks": answers["hooks"],
            "injection": answers["injection"], "skill_dir": answers["skill_dir"],
            "plugin_root": answers["plugin_root"], "checked": checked, "git_repo": bool(git_repo),
            "reader": bool(reader), "seen": seen}


def _python_ok(shown):
    try:
        return tuple(int(part) for part in str(shown).split(".")[:2]) >= PYTHON_FLOOR
    except ValueError:
        return False


def stance(host):
    """(row, plain sentence): what a session may do on this host (plan 7.3). Pure: takes the host.json dict.

    Rows: `everything` (git, network and gh work), `no-send` (git works, sending doesn't: close in Claude Code),
    `git-broken` (a repo, but git can't run: the reader path), `no-git` (no git, or a Python the launcher refuses:
    the reader path), and `reader` (a published copy, which uses no git by design)."""
    if host.get("reader"):
        return "reader", ("This is your copy. Here you can read, ask, find, explore and draft; drafts reach the "
                          "plan as a proposal.")
    # voice audit row 216: "this host can't use git" sat under a row saying git runs; the stance names what's missing
    if not _python_ok(host.get("python")):
        return "no-git", ("This machine's Python is too old for vela's checks, so sessions are recorded in Claude "
                          "Code. Here you can read, ask, find, explore and draft; drafts reach the plan as a proposal.")
    if host.get("git") != YES and not host.get("git_repo"):
        return "no-git", ("This folder isn't set up with git, so sessions are recorded in Claude Code. Here you can "
                          "read, ask, find, explore and draft; drafts reach the plan as a proposal.")
    if host.get("git") != YES:
        return "git-broken", ("This folder is a git repo, but git doesn't run here, so I can't record a session here. "
                              "Here you can read, ask, find, explore and draft.")
    if host.get("network") == YES and host.get("gh") == YES:
        if host.get("hooks") == YES:
            return "everything", "Everything a session needs works here."
        return "everything", "Everything a session needs works here. Hooks don't run here, so close checks everything itself."
    return "no-send", ("I can file the session here, but I can't send it. Open Claude Code in this folder and type "
                       "/vela:close to send it.")


# The gathering half: programs and the disk.

def run(command, cwd, timeout):
    """One program call, never raising: a missing program, a timeout and a failure each come back named. The call
    gets its own process group, killed whole on timeout, so a child it started (a credential helper, ssh) can't keep
    the probe waiting past its timeout."""
    try:
        child = subprocess.Popen(command, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 env={**os.environ, **NO_PROMPT}, start_new_session=True)
    except FileNotFoundError:
        return Ran("missing")
    except OSError as exc:
        return Ran("failed", err=str(exc))
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except OSError:
            child.kill()
        child.communicate()
        return Ran("timeout")
    return Ran("ok" if child.returncode == 0 else "failed", out, err)


def read_json(path):
    """A marker's contents, `{}` for one that isn't JSON (it still counts as present), None when absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(f"vela where --probe: couldn't read {path}: {exc}", file=sys.stderr)
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def age(path, now):
    try:
        return now - path.stat().st_mtime
    except OSError:
        return None


def loaded_yaml():
    try:
        import yaml
    except ImportError:
        return ""
    return getattr(yaml, "__file__", "") or ""


def is_reader_copy(root):
    from vela import roles
    facts = roles.Facts(git_here=(root / ".git").exists(), has_workspace=(root / ".vela" / "workspace.json").is_file())
    return facts.has_workspace and not facts.git_here and roles.decide(facts).role == roles.READER


def has_command(name):
    return shutil.which(name) is not None


def git_checks(root, reader, timeout):
    version = run(["git", "--version"], root, timeout) if has_command("git") else Ran("missing")
    if reader or version.how != "ok":
        return version, Ran("failed"), Ran("failed"), Ran("failed")
    toplevel = run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], root, timeout)
    if toplevel.how != "ok":
        return version, toplevel, Ran("failed"), Ran("failed")
    origin = run(["git", "-C", str(root), "remote", "get-url", "origin"], root, timeout)
    remote = run(["git", "-C", str(root), "ls-remote", "origin", "HEAD"], root, timeout) if origin.how == "ok" \
        else Ran("failed")
    return version, toplevel, origin, remote


def gh_checks(root, timeout):
    if not has_command("gh"):
        return Ran("missing"), Ran("failed")
    auth = run(["gh", "auth", "status"], root, timeout)
    login = run(["gh", "api", "user", "-q", ".login"], root, timeout) if auth.how == "ok" else Ran("failed")
    return auth, login


def swap_markers(root, home, token):
    """Read what the last probe left inside and outside the working folder, then leave fresh ones. An outside write
    that fails is said on stderr and counts as no outside marker; it never stops the probe."""
    inside, outside = root / INSIDE_MARKER, pathlib.Path(home) / OUTSIDE_MARKER
    before = (inside.is_file(), outside.is_file())
    atomic.write_atomic(inside, token + "\n")
    try:
        outside.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_atomic(outside, token + "\n")
    except OSError as exc:
        print(f"vela where --probe: couldn't leave the outside marker at {outside}: {exc}", file=sys.stderr)
    return before


def gather(root, plugin_root, skill_dir, injection, timeout, now, checked, home, in_session):
    """Run every check and return (rows, host). Raises ProbeFailed when the working folder can't be written, since
    then neither the markers nor `.vela/host.json` can be."""
    import vela
    reader = is_reader_copy(root)
    version, toplevel, origin, remote = git_checks(root, reader, timeout)
    git = git_row(version, toplevel, (root / ".git").exists(), reader)
    auth, login = gh_checks(root, timeout)
    try:
        (root / ".vela").mkdir(exist_ok=True)
        inside_before, outside_before = swap_markers(root, home, checked)
    except OSError as exc:
        raise ProbeFailed(f"couldn't write in {root / '.vela'}: {exc}") from exc
    rows = [filled_row("skill_dir", skill_dir, "skill folder"),
            filled_row("plugin_root", plugin_root, "plugin folder"),
            python_row(sys.version_info),
            yaml_row(loaded_yaml(), pathlib.Path(vela.__file__).resolve().parent.parent),
            git,
            network_row(git, origin, remote, reader, timeout),
            gh_row(auth, login, timeout),
            hooks_row(read_json(root / ACTIVE_FILE), read_json(root / CANARY_FILE), age(root / CANARY_FILE, now),
                      in_session),
            injection_row(injection),
            folder_row(inside_before, outside_before)]
    git_repo = (root / ".git").exists() or toplevel.how == "ok"
    return rows, host_record(rows, sys.version_info, git_repo, reader, checked)


def write_host(root, host):
    try:
        atomic.write_atomic(root / HOST_FILE, json.dumps(host, indent=2) + "\n")
    except OSError as exc:
        raise ProbeFailed(f"couldn't write {HOST_FILE}: {exc}") from exc
    return HOST_FILE
