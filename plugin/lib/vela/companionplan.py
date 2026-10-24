"""The plan digest: what the explain views read, cut from the dashboard's own data. Pure.

Every dashboard build already computes needs, lights, asks, progress, slices and flows. Cutting the digest from that
same dict (and never from a second reading of the vault) means a question about the plan is a lookup, not a rebuild
(Computational Friction ruled out: an extract is 2.9 s on the 24-app vault), and the panel can never count differently
from the dashboard (Distributed Monolith ruled out). It is stamped with the vault's fingerprint so a stale digest is
never served as current.
"""
import datetime

VERSION = 1
STUCK_LEVELS = ("warning", "caution")  # the lamp colors that mean something is held up; "override" is a lead's choice


def days_between(opened, today):
    try:
        return max(0, (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(opened)).days)
    except ValueError:
        return None


def names_of(data):
    return {key: {"name": e.get("title", key), "kind": e.get("kind", ""), "state": e.get("state", ""),
                  "page": e.get("path", "")} for key, e in data["entities"].items()}


def name(names, key):
    return names[key]["name"] if key in names else key


def asks_of(data, names):
    holds = {u["id"]: [name(names, h) for h in u.get("holds", [])] for u in data["unknowns"]}
    found = []
    for ask in data["asks"]:
        found.append({"id": ask["id"], "name": name(names, ask["id"]), "who": ask["ask"]["name"],
                      "who_key": ask["ask"]["key"], "state": ask["state"], "ask_by": ask["askBy"],
                      "opened": ask["opened"], "light": ask["light"]["level"], "urgency": ask["light"]["urgency"],
                      "open_days": days_between(ask["opened"], data["today"]) if ask["opened"] else None,
                      "holds": holds.get(ask["id"], [])})
    return found


def stuck_of(asks):
    """The open questions a lamp says are holding something up, most urgent first."""
    held = [a for a in asks if a["state"] == "open" and a["light"] in STUCK_LEVELS]
    return sorted(held, key=lambda a: (-a["urgency"], a["id"]))


def needs_of(data, names):
    return {"lines": [{"key": line["key"], "name": name(names, line["key"]), "kind": line["kind"], "for": line["for"],
                       "date": line.get("date", ""), "days": line.get("days"), "standing": line.get("standing", "")}
                      for line in data["needs"]["lines"]]}


def releases_of(data):
    return [{"name": s.get("name", ""), "target": s.get("target", ""), "state": s.get("state", "")}
            for s in data.get("releases", {}).get("states", []) if s.get("name") != "Today"]


def slices_of(data):
    return [{"key": s["key"], "name": s["name"], "status": s["status"] or "planned", "journey_due": s["journeyDue"],
             "milestone": s["milestone"], "overdue": s["overdue"]} for s in data["slicePlan"]["list"]]


def progress_of(data, names):
    found = []
    for row in data["progress"]["rows"]:
        mix = row["mix"]
        # mix is [early idea, assumption, confirmed, decided]: what is being planned is everything not already confirmed
        found.append({"app": row["app"], "name": name(names, row["app"]), "stage": row["stage"], "decided": mix[3],
                      "open": mix[0] + mix[1], "total": mix[0] + mix[1] + mix[3], "next": row["reason"]})
    return found


def flows_of(data, names):
    lanes = {lane["id"]: lane["name"] for lane in data["lanes"]}
    found = []
    for flow in data["flows"]:
        steps = []
        for step in flow["steps"]:
            pair = step["messages"][0] if step["messages"] else None
            steps.append({"n": step["n"], "from": lanes.get(pair["from"], name(names, pair["from"])) if pair else "",
                          "to": lanes.get(pair["to"], name(names, pair["to"])) if pair else "", "text": step["text"]})
        found.append({"key": flow["key"], "name": name(names, flow["key"]), "steps": steps})
    return found


def pages_of(data):
    return [{"key": key, "name": e["title"], "state": e.get("state", ""), "path": e.get("path", ""),
             "opening": (e.get("text") or "")[:300]}
            for key, e in data["entities"].items() if "anchor" not in e and e.get("path")]


def digest(data, made, fingerprint, next_line):
    """The digest (version 1). `made` is {"date", "commit", "from"}; `next_line` is vela next's first line."""
    names = names_of(data)
    asks = asks_of(data, names)
    return {"version": VERSION, "made": made, "fingerprint": fingerprint, "title": data["title"],
            "initiative": data["initiative"], "today": data["today"], "names": names, "asks": asks,
            "stuck": stuck_of(asks), "needs": needs_of(data, names), "releases": releases_of(data),
            "slices": slices_of(data), "progress": progress_of(data, names), "flows": flows_of(data, names),
            "pages": pages_of(data),
            "apps": [{"key": a["key"], "name": a["title"], "domain": a.get("domain", "")} for a in data["map"]["apps"]],
            "app_lights": {a["key"]: data["lights"].get(a["key"], {}).get("level", "dark") for a in data["map"]["apps"]},
            "next": {"text": next_line, "made": made["date"]}}
