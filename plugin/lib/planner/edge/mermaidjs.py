"""Run the pinned mermaid's own parser over many diagrams in one node process.

    parse_all(sources) -> [None | {message, token, text, expected}]    one verdict per source, in order
    Parse(sources).verdicts()                                          the same, started now and read later
    raises Unavailable(reason) when there is no node, or the parser could not run

One process for every block: loading the 3 MB bundle is most of the cost (about 0.1 s), so the cost does not grow
with the number of diagrams. `PLANNER_NODE` names the node to use; without it, node on the PATH.
"""
import json
import os
import pathlib
import shutil
import subprocess

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
MERMAID = ASSETS / "mermaid.min.js"
RUNNER = ASSETS / "mermaid-parse.js"
TIMEOUT_SECONDS = 60


class Unavailable(Exception):
    """Nothing could judge the diagrams; the message says why, in a reader's words."""


def find_node():
    named = os.environ.get("PLANNER_NODE")
    if named is not None:
        if not (pathlib.Path(named).is_file() and os.access(named, os.X_OK)):
            raise Unavailable(f"PLANNER_NODE names {named or '(nothing)'}, which is not a program that runs")
        return named
    found = shutil.which("node")
    if not found:
        raise Unavailable("Node.js (node) is not installed or not on the PATH, and mermaid's parser needs it")
    return found


class Parse:
    """One node run over every source, started at once so the caller can do other work while mermaid parses.
    `verdicts()` waits for it. A failure to start is kept and raised from `verdicts()`, so callers have one place
    to meet Unavailable."""

    def __init__(self, sources):
        self.sources, self.process, self.failure = list(sources), None, None
        if not self.sources:
            return
        try:
            for asset in (MERMAID, RUNNER):
                if not asset.is_file():
                    raise Unavailable(f"{asset.name} is missing from the plugin; reinstall it")
            node = find_node()
            try:
                self.process = subprocess.Popen([node, str(RUNNER), str(MERMAID)], stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            except OSError as exc:
                raise Unavailable(f"{node} could not run ({exc})") from exc
        except Unavailable as exc:
            self.failure = exc

    def verdicts(self):
        if self.failure:
            raise self.failure
        if self.process is None:
            return []
        try:
            stdout, stderr = self.process.communicate(json.dumps(self.sources), timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate()
            raise Unavailable(f"mermaid's parser took over {TIMEOUT_SECONDS} s and was stopped") from None
        except OSError as exc:  # node exited before reading its input
            self.process.wait()
            stdout, stderr = "", str(exc)
        if self.process.returncode != 0:
            detail = (stderr.strip().splitlines() or ["no message"])[0][:200]
            raise Unavailable(f"mermaid's parser stopped with exit {self.process.returncode} ({detail})")
        return self.read(stdout)

    def read(self, stdout):
        try:
            verdicts = json.loads(stdout)
        except ValueError:
            raise Unavailable("mermaid's parser wrote something that is not its list of results") from None
        if not isinstance(verdicts, list) or len(verdicts) != len(self.sources):
            raise Unavailable(f"mermaid's parser answered for {len(verdicts) if isinstance(verdicts, list) else 0} "
                              f"of {len(self.sources)} diagrams")
        return verdicts


def parse_all(sources):
    return Parse(sources).verdicts()
