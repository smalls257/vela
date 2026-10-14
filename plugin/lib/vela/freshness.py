"""Has anything changed since this copy was made? Pure: no disk, clock or network.

The Violation to prevent is the Silent Fallback of a stale copy: someone decides, or drafts, on pages the
owner has already replaced, and nothing told them. So every session start asks. The answer is only ever a
report. Nothing here pulls, updates or replays, and an unreachable source is a state to say plainly, never a
failure (a reader on a plane is not broken).

edge/vaultgit.py and edge/copies.py gather the facts; cli.py prints the report.
"""
from dataclasses import dataclass

CURRENT, NEWER, UNREACHABLE, UNKNOWN = "current", "newer", "unreachable", "unknown"
MIN_MATCH = 7  # shortest commit prefix two stamps may be compared by


@dataclass(frozen=True)
class Report:
    role: str
    state: str  # current, newer, unreachable or unknown
    checked_at: str
    message: str
    have: dict = None  # {"commit", "date"} of what this clone or copy holds
    latest: dict = None  # the same for the newest one known, or None
    behind: int = None  # owners only
    ahead: int = None
    uncommitted: int = None

    def as_dict(self):
        return {"role": self.role, "state": self.state, "checked_at": self.checked_at,
                "have": self.have, "latest": self.latest, "behind": self.behind, "ahead": self.ahead,
                "uncommitted": self.uncommitted, "message": self.message}


def same_commit(one, other):
    one, other = (one or "").strip(), (other or "").strip()
    return len(one) >= MIN_MATCH and len(other) >= MIN_MATCH and (one.startswith(other) or other.startswith(one))


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _short(commit):
    return (commit or "")[:MIN_MATCH]


def reader_report(workspace, stamp, unreachable, unreadable, checked_at):
    """Compare the workspace's baseline with the stamp at the source it was opened from.

    `stamp` is the source's published.json, or None; `unreachable` and `unreadable` are the reasons it is
    None ("" when not that). A source that cannot be reached is `unreachable`; one that answers with
    something that is not a published copy is `unknown`, and says why.
    """
    have = {"commit": _short(workspace.get("base_commit")), "date": workspace.get("base_date") or ""}
    if not have["commit"]:
        return Report("reader", UNKNOWN, checked_at, ".vela/workspace.json records no base_commit, so I cannot tell which "
                      "publish this copy came from.", have=have)
    if unreachable:
        return Report("reader", UNREACHABLE, checked_at,
                      f"I cannot reach the folder you opened this from (OneDrive offline?). Your copy is as of {have['date']}. "
                      f"({unreachable})", have=have)
    if unreadable:
        return Report("reader", UNKNOWN, checked_at, f"I reached the place you opened this from, but cannot tell what is there: "
                      f"{unreadable}. Your copy is as of {have['date']}.", have=have)
    latest = {"commit": _short(stamp.get("commit")), "date": stamp.get("date") or ""}
    changed_content = bool(workspace.get("base_tree_hash") and stamp.get("tree_hash")
                           and workspace["base_tree_hash"] != stamp["tree_hash"])
    if same_commit(workspace.get("base_commit"), stamp.get("commit")) and not changed_content:
        return Report("reader", CURRENT, checked_at,
                      f"Your copy is the latest published ({have['commit']}, {have['date']}).", have=have, latest=latest)
    where = f"A newer copy was published {latest['date']} (commit {latest['commit']})" if latest["commit"] != have["commit"] else \
        f"The copy at the source was published again {latest['date']} at the same commit with different contents"
    return Report("reader", NEWER, checked_at, f"{where}. Your drafts are kept. Run `/vela:open` on it to replay them.",
                  have=have, latest=latest)


def _counts(behind, ahead, uncommitted):
    return f"{_plural(behind, 'commit')} behind, {ahead} ahead, {_plural(uncommitted, 'uncommitted file')}"


def owner_report(local, upstream, behind, ahead, uncommitted, fetch_error, problem, checked_at):
    """The owner's clone against its upstream.

    `local` and `upstream` are {"commit", "date"} (upstream None when there is none); `fetch_error` is why
    git fetch failed ("" when it worked); `problem` is why there is nothing to compare ("no remote",
    "no upstream"), and makes the state `unknown`. Counts come from the last remote state git holds.
    """
    if problem:
        return Report("owner", UNKNOWN, checked_at, f"{problem[0].upper()}{problem[1:]}. {_plural(uncommitted, 'uncommitted file')}.",
                      have=local, uncommitted=uncommitted)
    counts = _counts(behind, ahead, uncommitted)
    if fetch_error:
        return Report("owner", UNREACHABLE, checked_at,
                      f"I could not reach origin; showing local state: {counts} (as of the last time you fetched). ({fetch_error})",
                      have=local, latest=upstream, behind=behind, ahead=ahead, uncommitted=uncommitted)
    if behind:
        return Report("owner", NEWER, checked_at, f"origin has moved on: {counts}. I have not pulled.",
                      have=local, latest=upstream, behind=behind, ahead=ahead, uncommitted=uncommitted)
    return Report("owner", CURRENT, checked_at, f"Your clone has everything origin has: {counts}.",
                  have=local, latest=upstream, behind=behind, ahead=ahead, uncommitted=uncommitted)
