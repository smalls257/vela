"""Two rules every skill and reference keeps, checked over all of them at once (a glob, so no one skill's pin).

1. **Only vela stages and commits** (overhaul plan Task 24). The Claude Code hook now denies every model-run `git add`
   and staging `git commit`, so a skill line that still tells the model to stage by hand would stop the session there,
   and where hooks don't fire it would stage whatever sat in the tree. Every commit goes through `vela close stage`,
   `vela close finish`, `vela proposals` or `vela team commit`. Rule deletion: these fail if a hand-typed stage or
   commit comes back into any skill text. The commands are judged by `hookverdict`, the hook's own reader, so the test
   and the hook can't disagree about what counts as staging.

2. **What the lead hears comes through `--for-lead`.** The commands a skill relays (freshness, check-slice, the
   session's question digest, handoff verify, next) each print the lead's words under `--for-lead`; a skill that runs
   one bare would pass branch names, counts and codes to the lead (voice audit, C90). An imperative "run `vela X`" of
   one of them carries `--for-lead`, or `--json` where the skill reasons over the result instead of saying it.
"""
import re

from conftest import REPO
from vela import hookverdict

PLUGIN = REPO / "plugin"
TEXTS = sorted([*PLUGIN.glob("skills/*/*.md"), *PLUGIN.glob("references/*.md")])
SPAN = re.compile(r"`([^`\n]+)`")
NEGATED = re.compile(r"\b(never|not|no)\b[^.]{0,80}$", re.I)  # "Never use `git add -A`" names what not to do


def instructions(path):
    """(line number, code span) for each backticked command a text gives that isn't a prohibition."""
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in SPAN.finditer(line):
            if not NEGATED.search(line[:match.start()]):
                yield n, match.group(1)


def is_git_commit(span):
    return any(words[0].rsplit("/", 1)[-1] == "git" and hookverdict.git_subcommand(words)[0] == "commit"
               for words in hookverdict.simple_commands(span))


def test_no_skill_tells_the_model_to_stage_or_commit_by_hand():
    found = []
    for path in TEXTS:
        for n, span in instructions(path):
            span = re.sub(r"<[^<>`]+>", "X", span)  # a placeholder such as <worktree> is a word, not a redirection
            verdict = hookverdict.bash_verdict(span)
            if (verdict is not None and verdict.decision == hookverdict.DENY) or is_git_commit(span):
                found.append(f"{path.relative_to(PLUGIN)}:{n}: {span}")
    assert not found, "\n".join(found)


def test_a_checkpoint_or_a_team_commit_names_the_command_that_makes_it():
    """Prose like "commit a checkpoint" with no command is how a model reached for `git add`: every such sentence
    names `vela close stage --checkpoint` (a session) or `vela team commit` (a team's design branch)."""
    loose = []
    for path in TEXTS:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                if re.search(r"\bcommit(ting)? (a checkpoint|after each|it on the branch)\b|\bcommit per section\b",
                             sentence, re.I) and not re.search(r"vela (close stage|team commit)", sentence):
                    loose.append(f"{path.relative_to(PLUGIN)}:{n}: {sentence.strip()}")
    assert not loose, "\n".join(loose)


RELAYED = re.compile(r"\b[Rr]un `(?:python3 \S+ |)vela (freshness|check-slice|handoff verify|next|questions --digest "
                     r"--session)\b([^`]*)`")


def test_every_relayed_command_is_run_for_the_lead():
    bare = []
    for path in TEXTS:
        text = path.read_text(encoding="utf-8")
        for match in RELAYED.finditer(text):
            if "--for-lead" not in match.group(2) and "--json" not in match.group(2):
                line = text.count("\n", 0, match.start()) + 1
                bare.append(f"{path.relative_to(PLUGIN)}:{line}: {match.group(0)}")
    assert not bare, "\n".join(bare)
