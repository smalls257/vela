#!/usr/bin/env python3
"""Compare two finished sim runs on the numbers the overhaul's mid-point gate reads, arm by arm.

Usage:
  python3 tests/sim/compare.py <old-run-dir> <new-run-dir> [--json]

It reads what each run stored and replays nothing: run.json `per_arm`, each arm's scorecard.json, and the assistant
turns of each arm's transcript.jsonl. Arms pair by name. Runs recorded before the tool was renamed to vela keep their
old arm folders and their old command names; `LEGACY_NAMES` below is the one place those names live, and it exists
only so such a run compares with a new one. The product never reads them.

What it counts, per paired arm:
- lead-facing turns: every assistant turn's text (what the lead read), matched against `say.LEAD_PATTERNS`, the
  same patterns `--for-lead` enforces, plus the tool's own names (`vela <command>`, `/vela:x`, `scripts/vela`).
  An old run's text goes through LEGACY_TEXT first, so its old command names count exactly as today's do. Without
  that, the old run's tool names would not count at all, and the new run's would look like new leaks.
- detail parity: the `vela capture` counts the scorecard stored for the final vault.
- judge verdicts: items captured, challenged, surfaced and decided, and the counts of decided-without-yes,
  invented facts and drafted messages.
- sessions: how each session ended, and what the arm spent.

It does not count skipped close steps, consent before a push, ledger rows or items written: run.py stores none of
them, and tool-call inputs in the transcript are cut at 200 characters, so a count read from them would quietly
miss some. The report names them as not counted, so nobody reads a missing number as zero.

Exit codes: 0 compared; 2 a folder is not a run, or the two runs share no arm.
"""
import argparse
import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "plugin" / "lib"))
from vela import cli, say  # noqa: E402

# Arm folders and `per_arm` keys of runs recorded before the rename, mapped to the arm they are now.
LEGACY_NAMES = {"planner": "vela", "planner-seuss": "vela-seuss"}


def _commands():
    """vela's command names, read from its own parser, so a new command counts without an edit here."""
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")
    return sorted(sub.choices, key=len, reverse=True)  # longest first: check-slice before check


COMMANDS = _commands()
_COMMAND = "(?:" + "|".join(re.escape(c) for c in COMMANDS) + r")\b"

# LEGACY_NAMES for text: an old run's words for the tool, rewritten to today's before anything is counted.
# Order matters only in that each rule leaves text the next one won't touch again.
LEGACY_TEXT = (
    (re.compile(r"(?<![\w-])planner:(?=[a-z])"), "vela:"),  # /planner:close, planner:voice-reviewer  # legacy-name
    (re.compile(r"\b(scripts|bin)/planner\b"), r"\1/vela"),  # the launcher path  # legacy-name
    (re.compile(r"(?<![\w-])\.planner\b"), ".vela"),  # .planner/ and .planner.yaml  # legacy-name
    (re.compile(r"\bPLANNER_"), "VELA_"),  # environment variables  # legacy-name
    (re.compile(r"(?<![\w/.-])planner (?=" + _COMMAND + ")"), "vela "),  # planner check  # legacy-name
)

# The tool's own names in a lead-facing turn. One mention counts once: `scripts/vela check` is a launcher path, so the
# command after it is not counted again.
TOOL_NAME = re.compile(r"/vela:[a-z][\w-]*|\b(?:scripts|bin)/vela\b|(?<![\w/.-])vela " + _COMMAND)

JUDGED = (("knows", "captured"), ("wrong", "challenged"), ("unaware", "surfaced"), ("conflicts", "surfaced"),
          ("decisions", "decided"), ("decisions", "yes_asked"))
LISTED = ("decided_without_yes", "invented_facts", "drafted_messages", "told_not_asked")
NOT_COUNTED = ("skipped close steps", "consent before push", "ledger rows", "items written")


class NotARun(Exception):
    """A folder the comparison can't read as a run. Exit 2, never a guessed number."""


def current_arm(name):
    """The arm a stored arm name is now, through LEGACY_NAMES for a run recorded before the rename."""
    return LEGACY_NAMES.get(name, name)


def modern_text(text):
    """An old run's text in today's names, so one pattern set counts both runs alike."""
    for pattern, replacement in LEGACY_TEXT:
        text = pattern.sub(replacement, text)
    return text


def lead_counts(texts):
    """Codes, IDs and tool names in the turns the lead read. `texts` are already in today's names."""
    kinds = collections.Counter()
    leaking_turns = 0
    for text in texts:
        found = collections.Counter({kind: sum(1 for _ in pattern.finditer(text))
                                     for kind, pattern in say.LEAD_PATTERNS.items()})
        found["tool name"] = sum(1 for _ in TOOL_NAME.finditer(text))
        kinds.update(found)
        leaking_turns += any(found[kind] for kind in say.ID_KINDS)
    turns = len(texts)
    codes = sum(kinds[kind] for kind in say.ID_KINDS)
    plumbing = sum(n for kind, n in kinds.items() if kind != "tool name" and kind not in say.ID_KINDS)
    return {"turns": turns, "codes_and_ids": codes, "plumbing": plumbing, "tool_names": kinds["tool name"],
            "codes_and_ids_per_turn": round(codes / turns, 3) if turns else None,
            "tool_names_per_turn": round(kinds["tool name"] / turns, 3) if turns else None,
            "turns_with_any": leaking_turns, "by_kind": {k: kinds[k] for k in [*say.LEAD_PATTERNS, "tool name"]}}


def assistant_texts(transcript_path, legacy):
    texts = []
    for n, line in enumerate(transcript_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NotARun(f"{transcript_path} line {n} is not JSON: {exc}") from exc
        if entry.get("speaker") == "assistant":
            text = str(entry.get("text") or "")
            texts.append(modern_text(text) if legacy else text)
    return texts


def judged_counts(card):
    counts = {}
    for category, field in JUDGED:
        items = card.get(category) or []
        counts[f"{category} {field}"] = f"{sum(1 for i in items if i.get(field))} of {len(items)}"
    for key in LISTED:
        counts[key] = len(card.get(key) or [])
    return counts


def endings_of(record):
    reasons = collections.Counter(e.get("reason", "?") for e in record.get("endings") or [])
    return ", ".join(f"{reason} {n}" for reason, n in sorted(reasons.items())) or "none recorded"


def read_arm(arm_dir, stored_name, record):
    """One arm's stored numbers. A missing scorecard is reported as not scored, never as zeros."""
    transcript = arm_dir / "transcript.jsonl"
    if not transcript.is_file():
        raise NotARun(f"{transcript} does not exist")
    legacy = stored_name in LEGACY_NAMES
    arm = {"stored_as": stored_name, "legacy_names_mapped": legacy,
           "lead_facing": lead_counts(assistant_texts(transcript, legacy)),
           "spent_usd": record.get("spent_usd"), "endings": endings_of(record)}
    card_path = arm_dir / "scorecard.json"
    if card_path.is_file():
        card = json.loads(card_path.read_text(encoding="utf-8"))
        capture = card.get("capture") or {}
        arm["detail"] = {k: v for k, v in (capture.get("counts") or {}).items() if isinstance(v, int)}
        if capture.get("error"):
            arm["detail_error"] = capture["error"]
        arm["judged"] = judged_counts(card)
        gate = card.get("completeness_gate") or {}
        if "percent" in gate:
            arm["completeness"] = gate["percent"]
    else:
        arm["not_scored"] = f"{card_path.name} is missing, so detail and judge counts are not known"
    return arm


def read_run(run_dir):
    """{current arm name: stored numbers} for a run folder. A run that stopped before run.json held `per_arm` is read
    from its arm folders, and says so."""
    run_dir = pathlib.Path(run_dir)
    if not run_dir.is_dir():
        raise NotARun(f"{run_dir} is not a folder")
    summary_path = run_dir / "run.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    per_arm = summary.get("per_arm") or {}
    names = list(per_arm) or sorted(p.name for p in run_dir.iterdir() if (p / "transcript.jsonl").is_file())
    if not names:
        raise NotARun(f"{run_dir} has no arm with a transcript.jsonl")
    arms = {}
    for name in names:
        arm = read_arm(run_dir / name, name, per_arm.get(name) or {})
        if not per_arm:
            arm["note"] = "run.json holds no per_arm, so spend and endings are not known"
        if current_arm(name) in arms:
            raise NotARun(f"{run_dir} holds two arms that are both {current_arm(name)!r} today")
        arms[current_arm(name)] = arm
    return {"run": run_dir.name, "arms": arms}


def compare(old_dir, new_dir):
    old, new = read_run(old_dir), read_run(new_dir)
    paired = [name for name in old["arms"] if name in new["arms"]]
    if not paired:
        raise NotARun(f"{old['run']} (arms {', '.join(old['arms'])}) and {new['run']} "
                      f"(arms {', '.join(new['arms'])}) share no arm")
    return {"old": old["run"], "new": new["run"],
            "pairs": {name: {"old": old["arms"][name], "new": new["arms"][name]} for name in paired},
            "unpaired": {"old": [n for n in old["arms"] if n not in paired],
                         "new": [n for n in new["arms"] if n not in paired]},
            "not_counted": list(NOT_COUNTED)}


def change(before, after, detail=False):
    """The change in words. Only a detail count is flagged when it falls more than 10%, the gate's threshold: fewer
    codes and IDs is the hoped-for direction, not a loss."""
    if isinstance(before, bool) or not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return ""
    if before == 0:
        return "" if after == 0 else "  (was 0)"
    percent = round(100 * (after - before) / before)
    return f"  ({percent:+d}%{', more than 10% down' if detail and percent < -10 else ''})"


def rows(title, old, new, keys, detail=False):
    lines = [f"  {title}"]
    for key in keys:
        a, b = old.get(key), new.get(key)
        a, b = ("not known" if a is None else a), ("not known" if b is None else b)
        lines.append(f"    {key}: {a} -> {b}{change(a, b, detail)}")
    return lines


def report(result):
    lines = [f"Old run: {result['old']}", f"New run: {result['new']}"]
    for name, pair in result["pairs"].items():
        old, new = pair["old"], pair["new"]
        lines += ["", f"Arm {name} (old run stored it as {old['stored_as']!r}, new run as {new['stored_as']!r})"]
        if old["legacy_names_mapped"]:
            lines.append("  the old run's text was read through LEGACY_NAMES before counting")
        lead_keys = ["turns", "codes_and_ids", "codes_and_ids_per_turn", "tool_names", "tool_names_per_turn",
                     "turns_with_any"]
        lines += rows("lead-facing turns", old["lead_facing"], new["lead_facing"], lead_keys)
        lines += rows("by kind", old["lead_facing"]["by_kind"], new["lead_facing"]["by_kind"],
                      list(old["lead_facing"]["by_kind"]))
        for side in (old, new):
            for key in ("not_scored", "detail_error", "note"):
                if side.get(key):
                    lines.append(f"  {side['stored_as']} in {'old' if side is old else 'new'} run: {side[key]}")
        if "detail" in old or "detail" in new:
            keys = sorted(set(old.get("detail", {})) | set(new.get("detail", {})))
            lines += rows("detail parity (vela capture)", old.get("detail", {}), new.get("detail", {}), keys, True)
        if "judged" in old or "judged" in new:
            keys = [f"{c} {f}" for c, f in JUDGED] + list(LISTED)
            lines += rows("judge", old.get("judged", {}), new.get("judged", {}), keys)
        lines += rows("sessions", old, new, ["endings", "spent_usd", "completeness"])
    for side in ("old", "new"):
        if result["unpaired"][side]:
            lines.append(f"\nOnly in the {side} run: {', '.join(result['unpaired'][side])}")
    lines.append("\nNot counted here (read the transcripts): " + ", ".join(result["not_counted"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="compare.py", description=__doc__.split("\n")[0])
    parser.add_argument("old", help="the earlier run folder, such as results/<baseline run>")
    parser.add_argument("new", help="the later run folder")
    parser.add_argument("--json", action="store_true", help="print the numbers as JSON")
    args = parser.parse_args(argv)
    try:
        result = compare(args.old, args.new)
    except (NotARun, json.JSONDecodeError) as exc:
        print(f"compare: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.json else report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
