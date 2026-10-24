"""What a reader saw last, so the answer can start "Since October 17: ...". Pure.

It compares two snapshots of two copies of the plan and never asks git, so it works in a copy with no git. The line
rolls when the copy changes, not on every run: all week a director's answers start with "Since October 17: ...", and a
second question the same afternoon doesn't read "nothing changed" (plan ruling 16).
"""
import datetime

from vela import say


def snapshot(digest, today):
    """{"made", "date", "states": {id: state}, "open": [ids], "late": [ids]} of the copy the digest describes."""
    return {"made": digest["made"], "date": digest["made"]["date"],
            "states": {key: n["state"] for key, n in digest["names"].items() if n["state"]},
            "open": sorted(a["id"] for a in digest["asks"] if a["state"] == "open"),
            "late": sorted(s["key"] for s in digest["slices"] if s["overdue"])}


def roll(seen, current):
    """{"previous", "current"}. The same copy again doesn't roll; a new copy makes the old current the previous."""
    held = (seen or {}).get("current")
    if held and held["made"] == current["made"]:
        return seen
    return {"previous": held, "current": current}


def since_line(previous, current):
    """"Since October 17: 2 decided, 1 new question, nothing went late." "" with no previous copy to compare."""
    if not previous:
        return ""
    decided = sum(1 for key, state in current["states"].items() if state == "decided" and previous["states"].get(key) != "decided")
    asked = len(set(current["open"]) - set(previous["open"]))
    late = len(set(current["late"]) - set(previous["late"]))
    when = say.date_words(previous["date"], datetime.date.fromisoformat(current["date"]))
    if not (decided or asked or late):
        return f"Since {when}: nothing changed."
    parts = []
    if decided:
        parts.append(f"{decided} decided")
    if asked:
        parts.append(f"{asked} new question{'' if asked == 1 else 's'}")
    parts.append(f"{late} went late" if late else "nothing went late")
    return f"Since {when}: " + ", ".join(parts) + "."
