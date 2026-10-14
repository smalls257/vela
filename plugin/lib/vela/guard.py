"""Which changed paths a close may stage, which it leaves out, and which are never staged. Pure: paths in, verdicts out.

Two Violations shape this module.

**Silent Fallback (hooks as the only gate).** If a hook were the only thing between `.inbox/` and a commit, a hook that
did not fire (Cowork, a clone without `core.hooksPath`) would look exactly like one that passed. So the rule lives
here, and the CLI applies it first: `vela close stage` never stages a forbidden path, and `vela guard staged`
(the vault's pre-commit hook) and `vela guard path` (later Claude Code hooks) only catch earlier what the CLI
already refuses.

**Paper Tiger (a deny-list of `git add` spellings).** Blocking `git add -A`, `.` and `--all` passes its own test and
misses `-u`, `-- .`, globs and `commit -a`. So staging is an **allow-list by exact path**: what a close may stage is
named below, and anything else that changed is named back to the model and left out. Nothing here inspects how git
was called; it only judges paths.

Never staged, at any depth or case the file system would treat as the same folder (a Mac's disk is case-insensitive,
so `.Inbox/` is `.inbox/`), matching the template's `.gitignore`:

- `.inbox/` holds company material, meeting notes and transcripts, that only the vault's owner may send. Committing it
  puts it on every clone and in every pull request, and no later commit takes it back out of the history.
- `voice/local/` holds the owner's private voice examples: kept on this machine by the owner's choice when they were
  saved.
- `voice/corpus/` is reading material the voice is learned from, often other people's writing; it never leaves the
  machine and never enters a draft.
- `.vela/` is the tool's working state on this machine (a reader's workspace stamp, replay backups, review packets,
  the session marker). The one exception is `.vela/explorer-pins.json`, the explorer's pinned layout, which the
  team shares on purpose.

Staged by a close (the allow-list):

- **Changed vault pages**: every Markdown file the vault parses as a page (the caller passes them, as
  `cli.page_kind` decides). `vela render` only ever rewrites vault pages, so render's files are always inside this
  rule; `close stage --paths-from-render` adds the proof that they are render's latest output, which is why a page
  left out of the commit used to fail CI's render check.
- **The open session record** `sessions/<id>.md`. Another session's record is left out: a close files one session,
  and a change to another record is someone else's work.
- **Harvested voice examples** under `voice/examples/`, which the owner agreed to share when they were saved.
- **The pins file** `.vela/explorer-pins.json`, **`.vela.yaml`** (the initiative's settings) and
  **`sources.md`**.

Left out on purpose, though they belong to the vault:

- `handoffs/*.md`: a handoff manifest records the commit it was written on, so it is written after the close commit
  and committed alone. Swept into a checkpoint it would name a commit that does not hold it.
- `dashboard.html`: rebuilt as the last step of every close and committed alone (`Rebuild dashboard`), so a close
  commit never carries a dashboard built before the pages it shows.
- Everything else (the plugin folder, `README.md`, `CONVENTIONS.md`, workflows, scratch files): not this session's
  work, or work that deserves its own commit.
"""
import posixpath
from dataclasses import dataclass

PINS = ".vela/explorer-pins.json"
SETTINGS = (".vela.yaml", "sources.md")
EXAMPLES = "voice/examples/"
SESSIONS = "sessions/"


@dataclass(frozen=True)
class Rule:
    """A never-staged rule: `key` for JSON and the refusal, `plain` for the lead, `fix` for the model."""
    key: str
    plain: str
    fix: str


INBOX = Rule("inbox", "The meeting notes in the inbox stay on this machine; I've left them out.",
             "Nothing to do; never stage `.inbox/`.")
VOICE_LOCAL = Rule("voice-local", "Your private voice examples stay on this machine; I've left them out.",
                   "Nothing to do; never stage `voice/local/`.")
VOICE_CORPUS = Rule("voice-corpus", "The writing the voice learns from stays on this machine; I've left it out.",
                    "Nothing to do; never stage `voice/corpus/`.")
TOOL_STATE = Rule("tool-state", "Vela's own working files stay on this machine; I've left them out.",
                  "Nothing to do; only `.vela/explorer-pins.json` is shared from `.vela/`.")
RULES = (INBOX, VOICE_LOCAL, VOICE_CORPUS, TOOL_STATE)

# Why an allowed-looking file is still left out. Every other leftover gets OTHER.
HANDOFF = "a handoff manifest is committed on its own, after the close commit, so it names a commit that holds it"
DASHBOARD = "the dashboard is rebuilt last and committed on its own"
OTHER_SESSION = "another session's record; this close files only its own"
OTHER = "not one of the files a close stages"


@dataclass(frozen=True)
class Plan:
    """What to stage, what is left out and why, and what is never staged under which rule. Each list keeps the order
    the paths came in."""
    stage: tuple
    left: tuple  # (path, reason)
    never: tuple  # (path, Rule)


def normal(path):
    """A vault-relative POSIX path: backslashes and `./` gone, `a/../b` folded. A path that climbs out of the vault
    keeps its `..`, so no rule below can match it by accident."""
    text = str(path).replace("\\", "/")
    folded = posixpath.normpath(text) if text else text
    return folded.lstrip("/") if folded != "." else ""


def never_rule(path):
    """The Rule that forbids staging `path`, or None. Compared case-folded, as the Mac's disk compares names."""
    folded = normal(path).casefold()
    parts = folded.split("/")
    if ".inbox" in parts[:-1]:  # `.inbox/` in .gitignore has no leading slash, so it matches at any depth
        return INBOX
    if folded.startswith("voice/local/"):
        return VOICE_LOCAL
    if folded.startswith("voice/corpus/"):
        return VOICE_CORPUS
    if folded.startswith(".vela/") and folded != PINS:
        return TOOL_STATE
    return None


def leave_reason(path, vault_pages, record):
    """Why the allow-list leaves `path` out, or None when it is staged. `path` has already passed `never_rule`."""
    path = normal(path)
    if path == record or path == PINS or path in SETTINGS or path.startswith(EXAMPLES):
        return None
    if path.startswith(SESSIONS):
        return OTHER_SESSION
    if path in vault_pages:
        return None
    if path.startswith("handoffs/"):
        return HANDOFF
    if path == "dashboard.html":
        return DASHBOARD
    return OTHER


def plan(changed, vault_pages, session_id):
    """Sort `changed` (vault-relative paths git reports as modified, added, deleted or untracked) into a Plan.

    `vault_pages` is the set of those paths the vault parses as pages; `session_id` names the open record. Never-staged
    rules win over the allow-list, so no page rule can let an inbox file through."""
    record = f"{SESSIONS}{session_id}.md" if session_id else None
    pages = {normal(p) for p in vault_pages}
    stage, left, never = [], [], []
    for raw in changed:
        path = normal(raw)
        rule = never_rule(path)
        if rule is not None:
            never.append((path, rule))
            continue
        reason = leave_reason(path, pages, record)
        if reason is None:
            stage.append(path)
        else:
            left.append((path, reason))
    return Plan(tuple(dict.fromkeys(stage)), tuple(left), tuple(never))


def forbidden(staged):
    """[(path, Rule)] for each staged path a commit must not carry: the pre-commit hook's whole judgment. Only the
    never-staged rules apply here, so an owner's own commit of the plugin folder or the README still goes through."""
    found = []
    for path in staged:
        rule = never_rule(path)
        if rule is not None:
            found.append((normal(path), rule))
    return found


def rules_hit(never):
    """The distinct Rules in a never list, in RULES order, so the lead hears each reason once."""
    keys = {rule.key for _, rule in never}
    return [rule for rule in RULES if rule.key in keys]
