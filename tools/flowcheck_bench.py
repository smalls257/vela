#!/usr/bin/env python3
"""Measure the flow checker on synthetic slices: states, transitions per second, time and peak memory.

A synthetic slice is one flow: App 0 calls apps 1..N-1 in turn over undrawn contracts (ok, refused, and optionally a
timeout and retries); a thread-wide ON rule ends the journey on anything but ok, so the main thread is a straight
line, as in a real call stack. Each of the first M calls' ok case emits an event, handled by another app in a par
block that moves one of K entities. Concurrency comes from the handlers, which is what the review says dominates.

    python3 tools/flowcheck_bench.py                      # the table, every configuration in its own process
    python3 tools/flowcheck_bench.py --one '{"apps": 5, "events": 3}'   # one configuration, JSON out

`synthetic_slice` is pure: it returns {path: text}, the same input the checker takes from a vault.
"""
import argparse
import json
import pathlib
import resource
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "plugin" / "lib"))

DEFAULTS = {"apps": 5, "events": 3, "entities": 2, "delivery": "exactly-once", "retries": False, "timeout": False,
            "shared": False, "reductions": "all", "max_states": 200_000, "max_seconds": 60.0}


def synthetic_slice(apps, events, entities, delivery, retries, timeout, shared):
    names = [f"App {i}" for i in range(apps)]
    keys = [f"app-{i}" for i in range(apps)]
    callees = list(range(1, apps))
    # Event j is emitted by callee j % (apps - 1) + 1 and handled by the next callee round.
    emitted = {}
    for j in range(events):
        producer = callees[j % len(callees)]
        subscriber = callees[(j + 1) % len(callees)] if len(callees) > 1 else 0
        emitted.setdefault(producer, []).append((j, subscriber))
    states = {k: ["new"] + [f"s{j}" for j in range(events) if j % entities == k] for k in range(entities)}
    files = {".vela.yaml": "initiative: INI-900\ntitle: Synthetic\n",
             "04b-releases.md": "---\nid: releases\ntype: initiative-section\ntitle: Releases\n---\n\n# Releases\n\n"
                                "## Release one\n\n- **Target:** 2027-01-01\n- **Tracer:** [[FLO-900-synthetic|FLO-900]], synthetic\n"}
    for i in range(apps):
        contracts, evts = "", ""
        if i > 0:
            emits = ", ".join(f"EVT-{200 + j}" for j, _ in emitted.get(i, []))
            contracts = (f"\n### CON-{100 + i} Do step {i}\n\n- **Can time out:** {'yes' if timeout else 'no'}\n"
                         f"- **Retries:** {'1 after timeout' if retries and timeout else 'none'}\n\n"
                         "| Case | When | Status | Answer | Emits | Sets |\n|---|---|---|---|---|---|\n"
                         f"| ok | | 200 | done | {emits} | |\n| refused | | 409 | refused | | |\n")
        for j, subscriber in emitted.get(i, []):
            evts += (f"\n### EVT-{200 + j} Event {j}\n\n- **Delivery:** {delivery}\n- **Order:** any\n\n"
                     f"| Subscriber | Retries |\n|---|---|\n| {names[subscriber]} | none |\n")
        files[f"05-building-blocks/{keys[i]}-building-blocks.md"] = (
            f"---\nid: APP-{keys[i]}\ntype: app-building-blocks\ntitle: {names[i]}\n---\n\n# {names[i]}\n{contracts}{evts}")
    for k in range(entities):
        rows = "".join(f"| {a} | {b} | EVT-{200 + int(b[1:])} handled |\n" for a in states[k] for b in states[k][1:] if a != b)
        files[f"entities/e{k}.md"] = (f"---\nid: ENT-{900 + k}\ntype: entity\ntitle: Entity {k}\napp: APP-app-0\nshared: {'true' if shared and k == 0 else 'false'}\n"
                                      f"initial: new\nfinal: [{', '.join(states[k])}]\n---\n\n# Entity {k}\n\n"
                                      f"| From | To | Allowed by |\n|---|---|---|\n{rows}")
    lines = [f"participant A{i} as {names[i]}" for i in range(apps)]
    lines.append("Note over A0: ON refused, timeout, gave_up: END stopped")
    for i in callees:
        lines.append(f"A0->>A{i}: CON-{100 + i} do step {i}")
        for j, subscriber in emitted.get(i, []):
            lines += [f"A{i}-)A{subscriber}: EVT-{200 + j}", f"par App {subscriber} handles event {j}",
                      f"Note over A{subscriber}: SET e{j % entities} s{j}", f"Note over A{subscriber}: END handled", "end"]
    lines.append("Note over A0: END done")
    files["06-runtime/flows/FLO-900-synthetic.md"] = ("---\nid: FLO-900\ntype: flow\ntitle: Synthetic\n---\n\n# Synthetic\n\n```mermaid\n"
                                                      "sequenceDiagram\n" + "\n".join("    " + l for l in lines) + "\n```\n")
    return files


def measure(config):
    from vela import flowcheck
    from vela.flowcheck import semantics
    c = dict(DEFAULTS, **config)
    files = synthetic_slice(c["apps"], c["events"], c["entities"], c["delivery"], c["retries"], c["timeout"], c["shared"])
    reductions = {"all": semantics.ALL_REDUCTIONS, "none": frozenset(), "symmetry": {semantics.SYMMETRY},
                  "local": {semantics.LOCAL_STEPS}}[c["reductions"]]
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    result = flowcheck.check_slice(files, "Release one", "2026-10-13", c["max_states"], c["max_seconds"], time.perf_counter, reductions)
    seconds = time.perf_counter() - started
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    scale = 1 if sys.platform == "darwin" else 1024  # macOS reports bytes, Linux kilobytes
    return {**c, "states": result.states, "transitions": result.transitions, "seconds": round(seconds, 3),
            "per_second": round(result.transitions / seconds) if seconds else 0, "peak_mb": round(peak * scale / 2**20, 1),
            "grew_mb": round((peak - before) * scale / 2**20, 1), "status": result.status,
            "codes": sorted({f.code for f in result.findings if f.severity == "error"})}


TABLE = [{"apps": n, "events": min(3, n - 1)} for n in (3, 5, 8, 10, 12, 15)] + \
        [{"apps": n, "events": min(3, n - 1), "delivery": "at-least-once"} for n in (3, 8, 15)] + \
        [{"apps": n, "events": min(3, n - 1), "shared": True} for n in (3, 8, 15)] + \
        [{"apps": n, "events": min(3, n - 1), "timeout": True, "retries": True} for n in (3, 8, 15)] + \
        [{"apps": n, "events": n - 1} for n in (3, 5, 8, 10)] + \
        [{"apps": n, "events": min(3, n - 1), "shared": True, "delivery": "at-least-once", "timeout": True, "retries": True} for n in (5, 10, 15)] + \
        [{"apps": n, "events": min(3, n - 1), "shared": True, "delivery": "at-least-once", "timeout": True, "retries": True,
          "reductions": r} for n in (10,) for r in ("none", "local", "symmetry")]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--one", help="one configuration as JSON; prints the measurement as JSON")
    args = parser.parse_args()
    if args.one:
        print(json.dumps(measure(json.loads(args.one))))
        return 0
    print("| apps | events | delivery | timeout+retries | shared | reductions | states | transitions | seconds | transitions/s | peak MB | result |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for config in TABLE:
        out = subprocess.run([sys.executable, __file__, "--one", json.dumps(config)], capture_output=True, text=True, timeout=600)
        if out.returncode:
            print(f"| {config} | failed: {out.stderr.strip().splitlines()[-1] if out.stderr else out.returncode} |")
            continue
        m = json.loads(out.stdout)
        print(f"| {m['apps']} | {m['events']} | {m['delivery']} | {'yes' if m['timeout'] else 'no'} | {'yes' if m['shared'] else 'no'} | "
              f"{m['reductions']} | {m['states']:,} | {m['transitions']:,} | {m['seconds']} | {m['per_second']:,} | {m['peak_mb']} | "
              f"{m['status']}{' ' + ','.join(m['codes']) if m['codes'] else ''} |", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
