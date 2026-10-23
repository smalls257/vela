"""What the Claude Code hooks decide about one tool call: pure, text in and a verdict out (no stdin, disk or git).

Every rule here is already held somewhere that does not depend on a hook firing, because a hook that didn't run looks
exactly like one that passed (Silent Fallback, plan section 1): `vela close stage` is the only thing that stages and
the vault's pre-commit `guard staged` refuses a forbidden path; `vela decide` is the only thing that moves a state,
and `close gate` refuses a state change with no quoted capture; render refuses a hand-edited generated block; `close
push` refuses to send without the lead's yes on record. In Claude Code the hooks only say so earlier, before the
mistake is on disk. So this module holds no rule of its own: paths are judged by `guard.never_rule`, the generated
markers are `parse.MARKER_OPEN`/`MARKER_CLOSE`, and the state lines are the two forms the vault format defines.

**Paper Tiger (a deny-list of `git add` spellings), ruled out.** Matching `git add -A`, `git add .` and `--all` passes
its own test and misses `-u`, `git -C x add`, `git stage`, `sh -c '...'`, `$(...)` and `commit -a`. So the command is
read the way a shell reads it, into simple commands (quotes, `;`, `&&`, `|`, `$(...)`, backticks, `sh -c`, `eval`,
`env`/`xargs`-style wrappers and here-documents), and every `git` run that would write the index is denied whatever
its spelling: `add`, `stage`, `update-index`, `apply --index|--cached`, and a `commit` that stages on its way
(`-a`/`--all`, `-i`, `-o`, `-p`, `--pathspec-from-file`, or a path after the options). A plain `git commit -m` stays
allowed: it commits what is already staged, and only the CLI stages. Words are never commands, so a capture that
says "git add" in quotes, or a here-document fed to python, is left alone. The CLI's own git runs inside
`sh .../scripts/run-vela ...` and never reaches this text.

**Leaky Narrative, ruled out at the reason.** A deny names the way that works ("`vela close stage` stages ...",
"use `vela decide`") in plain words; the model reads it and retries the right way instead of guessing a spelling the
hook might miss.

Asked, not denied: `git push`, `gh pr create` and `gh pr comment`, the only calls that send something off the machine
(plan 9.3 Q9). `ask` puts the send in front of the human; bypass-permissions mode may auto-allow it, which is why
`close push`'s consent check stays the real gate.
"""
import posixpath
import re
from dataclasses import dataclass, field

from vela import guard, parse

DENY, ASK = "deny", "ask"


@dataclass
class Verdict:
    decision: str  # DENY or ASK
    reason: str  # plain words for the model, naming the way that works
    forbidden: list = field(default_factory=list)  # paths guard.py says a commit may never carry, as given


# --------------------------------------------------------------------------- reading a shell command

SEPARATORS = ";&|()\n"
KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "for", "case", "esac", "{", "}", "!",
            "time", "[[", "]]", "function", "select", "coproc", "in"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")


class _Reader:
    """A small shell lexer: enough of POSIX sh to find every simple command a line would run, never a full parser.

    It errs toward finding a command: text it can't place (an unclosed quote) ends the word there, and the words so far
    are still judged. Substitutions (`$(...)`, backticks) are read as commands of their own, even inside double
    quotes, because the shell runs them there too; single quotes and here-document bodies are data."""

    def __init__(self, text):
        self.text = text
        self.i = 0
        self.commands = []  # each a list of words
        self.words = []
        self.word = None
        self.heredocs = []  # delimiters waiting for the next newline
        self.skip_next = False  # the word after a redirection is its target, not an argument

    def finish_word(self):
        if self.word is not None:
            if self.skip_next:
                self.skip_next = False
            elif not self.words and self.word in KEYWORDS:
                pass  # `then git add x`: the keyword starts a command, it isn't one
            else:
                self.words.append(self.word)
        self.word = None

    def finish_command(self):
        self.finish_word()
        if self.words:
            self.commands.append(self.words)
        self.words = []

    def add(self, text):
        self.word = (self.word or "") + text

    def substitution(self, end_char):
        """Read up to the matching `)` or backtick from self.i; return the inner text. Nested parentheses count."""
        depth, start, quote = 0, self.i, None
        while self.i < len(self.text):
            c = self.text[self.i]
            if quote:
                if c == quote:
                    quote = None
                elif c == "\\" and quote == '"':
                    self.i += 1
            elif c in "'\"" and end_char == ")":
                quote = c
            elif c == "\\":
                self.i += 1
            elif end_char == ")" and c == "(":
                depth += 1
            elif c == end_char and depth == 0:
                inner = self.text[start:self.i]
                self.i += 1
                return inner
            elif end_char == ")" and c == ")":
                depth -= 1
            self.i += 1
        return self.text[start:]

    def nested(self, inner):
        self.commands.extend(simple_commands(inner))
        self.add("_")  # the substitution's output is a word of the outer command

    def read_heredoc_bodies(self):
        """At a newline: skip each waiting here-document's body, up to its delimiter line."""
        for strip_tabs, delimiter in self.heredocs:
            while self.i < len(self.text):
                end = self.text.find("\n", self.i)
                line = self.text[self.i:] if end == -1 else self.text[self.i:end]
                self.i = len(self.text) if end == -1 else end + 1
                if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                    break
        self.heredocs = []

    def heredoc(self):
        """After `<<` or `<<-`: the next word is the delimiter (quotes removed)."""
        strip_tabs = self.text.startswith("-", self.i)
        self.i += 1 if strip_tabs else 0
        while self.i < len(self.text) and self.text[self.i] in " \t":
            self.i += 1
        start = self.i
        while self.i < len(self.text) and self.text[self.i] not in " \t\n;&|()<>":
            self.i += 1
        self.heredocs.append((strip_tabs, self.text[start:self.i].replace("'", "").replace('"', "").replace("\\", "")))

    def double_quoted(self):
        self.add("")
        while self.i < len(self.text):
            c = self.text[self.i]
            self.i += 1
            if c == '"':
                return
            if c == "\\" and self.i < len(self.text):
                self.add(self.text[self.i])
                self.i += 1
            elif c == "`":
                self.nested(self.substitution("`"))
            elif c == "$" and self.text.startswith("(", self.i):
                self.i += 1
                self.nested(self.substitution(")"))
            else:
                self.add(c)

    def read(self):
        text = self.text
        while self.i < len(text):
            c = text[self.i]
            self.i += 1
            if c == "\n":
                self.finish_command()
                self.read_heredoc_bodies()
            elif c in " \t":
                self.finish_word()
            elif c == "#" and self.word is None:
                end = text.find("\n", self.i)
                self.i = len(text) if end == -1 else end
            elif c == "'":
                end = text.find("'", self.i)
                self.add(text[self.i:] if end == -1 else text[self.i:end])
                self.i = len(text) if end == -1 else end + 1
            elif c == '"':
                self.double_quoted()
            elif c == "\\":
                if self.i < len(text) and text[self.i] != "\n":
                    self.add(text[self.i])
                self.i += 1
            elif c == "`":
                self.nested(self.substitution("`"))
            elif c == "$" and text.startswith("(", self.i):
                self.i += 1
                self.nested(self.substitution(")"))
            elif c in "<>":
                if self.word is not None and self.word.isdigit():
                    self.word = None  # `2>`: the descriptor isn't an argument
                self.finish_word()
                if c == "<" and text.startswith("<<", self.i):
                    self.i += 2  # `<<<`: a here-string, whose word is data
                    self.skip_next = True
                    continue
                if c == "<" and text.startswith("<", self.i):
                    self.i += 1
                    self.heredoc()
                    continue
                while self.i < len(text) and text[self.i] in "<>&|":
                    self.i += 1
                if self.i < len(text) and text[self.i].isdigit() and text[self.i - 1] == "&":
                    self.i += 1  # `2>&1` names a descriptor, not a file
                    continue
                self.skip_next = True
            elif c in SEPARATORS:
                self.finish_command()
            else:
                self.add(c)
        self.finish_command()
        return self.commands


def simple_commands(text):
    """Every simple command `text` would run, as word lists, substitutions and `sh -c` bodies included."""
    found = []
    for words in _Reader(text).read():
        found.extend(_unwrap(words))
    return found


SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# Wrappers that run the rest of their words as a command, with the options that take a value after them.
WRAPPERS = {"env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}, "sudo": {"-u", "-g", "-C", "-D"},
            "command": set(), "exec": {"-a"}, "nohup": set(), "nice": {"-n"}, "time": set(), "builtin": set(),
            "xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a"}, "timeout": {"-s", "-k", "--signal"},
            "caffeinate": set(), "stdbuf": {"-i", "-o", "-e"}}


def _unwrap(words):
    """The command a wrapper runs: `env A=1 git add` is `git add`; `sh -c 'x'` and `eval x` are read again."""
    while words:
        while words and ASSIGNMENT.match(words[0]):
            words = words[1:]
        if not words:
            return []
        name = posixpath.basename(words[0])
        if name == "eval":
            return simple_commands(" ".join(words[1:]))
        if name in SHELLS:
            for n, word in enumerate(words[1:], 1):
                if word.startswith("-") and not word.startswith("--") and "c" in word[1:]:
                    return simple_commands(words[n + 1]) if n + 1 < len(words) else []
            return [words]
        if name not in WRAPPERS:
            return [words]
        rest, takes = words[1:], WRAPPERS[name]
        while rest and (rest[0].startswith("-") or (name == "env" and ASSIGNMENT.match(rest[0]))):
            rest = rest[2:] if rest[0] in takes else rest[1:]
        if name == "timeout" and rest:
            rest = rest[1:]  # the duration
        words = rest
    return []


# --------------------------------------------------------------------------- what a git or gh run does

GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix",
                     "--exec-path"}
COMMIT_SHORT_VALUES = set("mFCctS")  # short options of `git commit` that take the rest of the word, or the next one
COMMIT_LONG_VALUES = {"--message", "--file", "--reuse-message", "--reedit-message", "--template", "--author", "--date",
                      "--cleanup", "--fixup", "--squash", "--trailer", "--gpg-sign", "--untracked-files"}
COMMIT_STAGES_LONG = {"--all", "--include", "--only", "--interactive", "--patch", "--pathspec-from-file"}
COMMIT_STAGES_SHORT = set("aiop")


def git_subcommand(words):
    """(subcommand, its arguments) for a `git` word list, past git's own options; (None, []) for a bare `git`."""
    rest = words[1:]
    while rest and rest[0].startswith("-"):
        option = rest[0]
        rest = rest[2:] if option in GIT_VALUE_OPTIONS else rest[1:]
    return (rest[0], rest[1:]) if rest else (None, [])


def commit_stages(args):
    """True when this `git commit` would stage files before committing (and so does what only the CLI may)."""
    n = 0
    while n < len(args):
        word = args[n]
        n += 1
        if word == "--":
            return n < len(args)
        if word.startswith("--"):
            name = word.split("=", 1)[0]
            if name in COMMIT_STAGES_LONG:
                return True
            if name in COMMIT_LONG_VALUES and "=" not in word:
                n += 1
            continue
        if word.startswith("-") and len(word) > 1:
            for k, letter in enumerate(word[1:], 1):
                if letter in COMMIT_STAGES_SHORT:
                    return True
                if letter in COMMIT_SHORT_VALUES:
                    if k == len(word) - 1 and letter not in "S":
                        n += 1  # the value is the next word
                    break
            continue
        return True  # a path: `git commit x.md` stages x.md first
    return False


def writes_index(sub, args):
    if sub in ("add", "stage", "update-index"):
        return True
    if sub == "apply":
        return any(a in ("--index", "--cached") for a in args)
    if sub == "commit":
        return commit_stages(args)
    return False


def named_paths(args):
    """The arguments of an index-writing git run that look like paths: what guard.py is asked about."""
    paths, after_dashes = [], False
    for word in args:
        if word == "--" and not after_dashes:
            after_dashes = True
        elif after_dashes or not word.startswith("-"):
            paths.append(word)
    return paths


def sends(words):
    """True for the runs that send work off this machine: `git push`, `gh pr create`, `gh pr comment`."""
    name = posixpath.basename(words[0])
    if name == "git":
        return git_subcommand(words)[0] == "push"
    if name == "gh":
        rest = [w for w in words[1:] if not w.startswith("-")]
        return rest[:1] == ["pr"] and rest[1:2] in (["create"], ["comment"])
    return False


STAGE_REASON = ("In a vela vault only vela stages and commits, by exact path from its allow-list: run `vela close "
                "stage` (with `--checkpoint`, `--draft` or `--close` to commit), and `vela close finish` at the end of "
                "a close. A proposal's worktree commits through `vela proposals commit`. Staging by hand is how the "
                "inbox, private voice files or another session's work end up in a pull request.")
SEND_REASON = ("This sends work off this machine (a push or a pull request). In a vela vault `vela close push` and "
               "`vela close pr` do it once the lead has said yes; ask the lead before it goes.")


SHORT_BROAD = set("Au")  # `git add -A`, `git add -u`
LONG_BROAD = {"--all", "--update"}
GLOB = re.compile(r"[*?\[]")
OUTSIDE_PLANS_REASON = (" This folder holds plans. The plan's files go through vela (`vela close stage`); to stage the "
                        "other files by hand, name each path, for example `git add notes/todo.md`, and do not use -A, "
                        "-u, `.` or a folder or pattern that reaches a plan.")


def stages_broadly(sub, args):
    """True when this index-writing run names no path to limit it (`add -A`, `add -u`, `commit -a`, `apply --index`)
    or `add`'s flags say everything."""
    flags = [w for w in args if w.startswith("-") and w != "--"]
    letters = {c for w in flags if not w.startswith("--") for c in w[1:]}
    if sub in ("add", "stage"):
        return bool(letters & SHORT_BROAD or set(flags) & LONG_BROAD) and not named_paths(args)
    if sub == "commit":  # a commit that names a path is judged by that path; a plain one by what the index holds
        return bool(letters & set("aip")) or bool(set(flags) & {"--all", "--include", "--patch", "--interactive"})
    return sub in ("apply", "update-index") and not named_paths(args)


def reaches_a_plan(path, cwd, plan_roots):
    """True when a path named in a git run lands inside a plan folder or covers one (a parent folder, `.`, or a pattern
    whose fixed part does). Judged on strings from `cwd`; an absolute path is taken as it is."""
    literal = GLOB.split(path, 1)[0]
    if literal != path:
        literal = literal.rsplit("/", 1)[0] if "/" in literal else ""
    full = posixpath.normpath(posixpath.join(cwd, literal or "."))
    return any(full == root or full.startswith(root + "/") or root.startswith(full.rstrip("/") + "/")
               for root in plan_roots)


def bash_verdict(command, cwd="", plan_roots=None, staged=()):
    """The hook's verdict on one Bash command line, or None for no opinion.

    In a plan every index-writing git run is denied. Opened at a repo's root (or a folder with no plan above it) that
    holds plans, `plan_roots` lists their absolute folders and only a run that reaches a plan is denied: one that
    names a path inside a plan or over one, or stages broadly. Named paths outside every plan are the owner's own
    work and pass. A plain `git commit` commits only the index, so it is denied only when `staged` (absolute paths the
    index holds; None when they could not be read, which counts as holding a plan's) reaches a plan."""
    denied, forbidden, asked = False, [], False
    for words in simple_commands(command):
        name = posixpath.basename(words[0])
        if name == "git":
            sub, args = git_subcommand(words)
            if sub == "commit" and plan_roots is not None and not writes_index(sub, args):
                denied = denied or staged is None or any(reaches_a_plan(p, cwd, plan_roots) for p in staged)
            elif writes_index(sub, args):
                if plan_roots is None:
                    denied = True
                    forbidden += [p for p in named_paths(args) if guard.never_rule(p) is not None]
                elif stages_broadly(sub, args) or any(reaches_a_plan(p, cwd, plan_roots) for p in named_paths(args)):
                    denied = True
        if sends(words):
            asked = True
    if denied:
        rules = [guard.never_rule(p) for p in forbidden]
        said = " ".join(dict.fromkeys(rule.plain for rule in rules))
        return Verdict(DENY, STAGE_REASON + (OUTSIDE_PLANS_REASON if plan_roots is not None else "")
                       + (f" {said}" if said else ""), forbidden)
    if asked:
        return Verdict(ASK, SEND_REASON)
    return None


# --------------------------------------------------------------------------- what an edit changes

STATE_LINE = re.compile(r"^\s*[-*]\s+\*\*State:\*\*")
STATE_REASON = ("A state moves only through `vela decide` (or `vela check --fix W326`), which writes the state with "
                "the lead's quoted yes and its Changes row; a hand edit is a state change the close gate refuses. "
                "Use `vela decide`.")
GENERATED_REASON = ("That text sits inside a generated block (`<!-- generated: ... -->`), which `vela render` "
                    "rewrites from the pages; a hand edit there is lost or refused. Change the item it comes from, "
                    "then run `vela render`.")


def state_lines(text):
    """The state lines of a page, in order: its frontmatter `state:` and every `**State:**` bullet."""
    lines = parse.lines_of(text)
    found = []
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith("state:"):
                found.append(line.strip())
    found += [line.strip() for line in lines if STATE_LINE.match(line)]
    return found


def generated_blocks(text):
    """{block name: its text, markers included} for every closed generated block."""
    blocks, open_name, held = {}, None, []
    for line in parse.lines_of(text):
        opening, closing = parse.MARKER_OPEN.match(line), parse.MARKER_CLOSE.match(line)
        if opening and open_name is None:
            open_name, held = opening.group(1), [line]
        elif open_name is not None:
            held.append(line)
            if closing and closing.group(1) == open_name:
                blocks.setdefault(open_name, "\n".join(held))
                open_name = None
    return blocks


def removed(before, after):
    """Items of `before` that `after` no longer holds, counted (a changed line is one removed, one added)."""
    left = list(after)
    gone = []
    for item in before:
        if item in left:
            left.remove(item)
        else:
            gone.append(item)
    return gone


def edit_verdict(before, after):
    """The verdict on changing a vault page from `before` to `after`, or None. A new page (`before` None) and a
    newly added item are not a state change; changing or removing an existing state line is."""
    if before is None or after is None:
        return None
    if removed(state_lines(before), state_lines(after)):
        return Verdict(DENY, STATE_REASON)
    after_blocks = generated_blocks(after)
    if any(after_blocks.get(name) != text for name, text in generated_blocks(before).items()):
        return Verdict(DENY, GENERATED_REASON)
    return None


def apply_edits(before, edits):
    """The text after an Edit or MultiEdit, or None when an old string isn't there (the tool will refuse it itself)."""
    text = before
    for one in edits:
        old, new = one.get("old_string", ""), one.get("new_string", "")
        if not old or old not in text:
            return None
        text = text.replace(old, new) if one.get("replace_all") else text.replace(old, new, 1)
    return text
