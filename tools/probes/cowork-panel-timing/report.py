"""Turn times per arm from the hook stamps and the write stamps. Usage: python3 report.py <working folder>"""
import json
import pathlib
import statistics
import sys

UNDER = 1.0  # seconds: the owner's "no extra model turn" rule, in time


def read_lines(path):
    path = pathlib.Path(path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def turns(hooks, writes):
    """{arm: [seconds]}: each prompt paired with the next stop, filed under the arm of the write between them."""
    found = {}
    prompt = None
    for stamp in sorted(hooks, key=lambda s: s["t"]):
        if stamp["event"] == "prompt":
            prompt = stamp["t"]
        elif stamp["event"] == "stop" and prompt is not None:
            inside = [w for w in writes if prompt <= w["t"] <= stamp["t"]]
            if inside:
                found.setdefault(inside[0]["arm"], []).append(round(stamp["t"] - prompt, 3))
            prompt = None
    return found


def p90(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))]


def summary(found):
    if not found:
        return ["No hook stamps were found, so Cowork's hooks did not fire here.",
                "Type in your stopwatch times (ten per arm) and compare the medians by hand."]
    lines = []
    base = statistics.median(found["A"]) if "A" in found else None
    for arm in sorted(found):
        median = statistics.median(found[arm])
        text = f"{arm}: median {median} s, p90 {p90(found[arm])} s"
        if arm != "A" and base is not None:
            gap = round(median - base, 3)
            text = f"{arm}: median {median} s, gap to A {gap} s, under {UNDER} s: {'yes' if gap < UNDER else 'no'}"
        lines.append(text)
    return lines


def main(argv):
    folder = pathlib.Path(argv[0]) / ".vela-probe" if argv else pathlib.Path(".vela-probe")
    for line in summary(turns(read_lines(folder / "hooks.jsonl"), read_lines(folder / "writes.jsonl"))):
        print(line)


if __name__ == "__main__":
    main(sys.argv[1:])
