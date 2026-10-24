"""Stand-in for a vela write and a vela render, for timing only. `write` bumps a counter; `render` draws the panel."""
import argparse
import json
import os
import pathlib
import time

FOLDER = pathlib.Path(".vela-probe")


def atomic(path, text):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def write(arm):
    FOLDER.mkdir(exist_ok=True)
    state_path = FOLDER / "state.json"
    n = (json.loads(state_path.read_text(encoding="utf-8"))["n"] if state_path.exists() else 0) + 1
    atomic(state_path, json.dumps({"n": n}))
    with open(FOLDER / "writes.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"arm": arm, "n": n, "t": time.time()}) + "\n")
    print(n)


PAGE = """<!doctype html><meta charset="utf-8"><title>Probe panel</title>
<body style="font:16px system-ui;margin:2rem"><div style="font-size:64px;font-weight:700">%d</div>
<div>written at %s</div></body>"""


def render():
    n = json.loads((FOLDER / "state.json").read_text(encoding="utf-8"))["n"]
    atomic(FOLDER / "panel.html", PAGE % (n, time.strftime("%H:%M:%S")))
    print(FOLDER / "panel.html")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("verb", choices=["write", "render"])
    parser.add_argument("--arm", default="A")
    args = parser.parse_args()
    write(args.arm) if args.verb == "write" else render()


if __name__ == "__main__":
    main()
