"""Scales, ceilings, power and the voice for the probe loop (the 2026-10-15 rebuild).

Round two of the probe loop could not show an improvement even where one might exist. Three Violations, each with
its own fix here:

- **Paper Tiger** (a scale too short to move). Decisions topped out at 2, the hospitals holdout had 4 conflicts, and
  most scores sat at the floor or the ceiling, so a real change and noise looked alike. The checks below count 6 to 10
  items each, and every one returns a *measure* (a count of N) as well as pass or fail, so runs can be averaged.
- **Black Box** (an unknown reachable ceiling). A score of 0 of 8 says nothing until we know what a session that is
  told plainly to do the behavior gets. `oracle_argv` passes a case's `oracle:` text to the assistant as an appended
  system prompt, for that probe only. It never touches `plugin/**`: it measures the material, not the skill. A low
  ceiling means the persona or the snapshot is broken, and the material is fixed, not the skill.
- **Silent Fallback** in the loop's verdict (a change kept because one run moved). `summarize` gives every measure
  its mean and spread over the runs; `compare` calls a move real only when the mean moves by more than the larger of
  the two spreads. The spread is the sample standard deviation (0 for one run).

Every probe also reports the voice on its lead-facing turns (the user's voice gate, 2026-10-15): codes and IDs per
turn by `vela.say.LEAD_PATTERNS`, the voice score (the share of turns with none), turns that told rather than asked,
turns that put more than `say.LEAD_LIMIT` things to the lead, and whether the voice-loading step ran. All mechanical,
all counts, so they print blind. A change that lifts accuracy and hurts the voice is reverted (`probe_keep.py`).

Nothing here names a persona's items. A check reads items by kind, category and the generic flags a persona file sets
(`open_question: true` on a fact, `blocked: true` and `item:` on a decision); its summary holds counts only, and
item IDs go only to the detail, which a blind run writes to the DO-NOT-READ file.
"""
import contextlib
import re
import statistics

from vela import cli, model, parse, say

VOICE_FILE = "CONVERSATION-VOICE"
HIGHER, LOWER = "higher", "lower"


def measure(name, value, of=None, better=HIGHER):
    return {"name": name, "value": value, "of": of, "better": better}


# ------------------------------------------------------------------ the ceiling

@contextlib.contextmanager
def oracle_argv(sim, text):
    """While active, every assistant call gets `--append-system-prompt <text>` before its prompt. The driver's own
    argv builder is wrapped, not copied, so the isolation flags stay the driver's."""
    if not text:
        yield
        return
    original = sim.assistant_argv

    def with_oracle(*args, **kwargs):
        argv = original(*args, **kwargs)
        at = argv.index("--")
        return argv[:at] + ["--append-system-prompt", text] + argv[at:]

    sim.assistant_argv = with_oracle
    try:
        yield
    finally:
        sim.assistant_argv = original


# ------------------------------------------------------------------ the voice on lead-facing turns

TELL_CUE = re.compile(r"\b(?:i(?:ve| have) (?:decided|settled on|gone with|chosen|picked|assumed)"
                      r"|i(?:ll| will) (?:go with|assume|pick|choose|settle on)|we(?:ll| will) go with|lets go with"
                      r"|going with|the answer is|the right (?:answer|call|choice) is|you should|you need to"
                      r"|the decision is)\b")
TOP_ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s")
TABLE_RULE = re.compile(r"^\|[\s:|-]+\|?\s*$")


def lead_codes(text):
    """Codes, IDs and builder plumbing a lead would read, by `say.LEAD_PATTERNS`, overlapping matches counted once."""
    spans = sorted((m.start(), m.end()) for p in say.LEAD_PATTERNS.values() for m in p.finditer(text))
    count, end = 0, -1
    for start, stop in spans:
        if start >= end:
            count += 1
        end = max(end, stop)
    return count


def things_offered(text, probe):
    """How many things one turn puts to the lead: its top-level list items and table rows, or its questions,
    whichever is more."""
    items, header_seen = 0, False
    for line in text.splitlines():
        if line.startswith("|"):
            if TABLE_RULE.match(line):
                continue
            if not header_seen:
                header_seen = True  # the first row of a table is its header
                continue
            items += 1
            continue
        header_seen = False
        items += bool(TOP_ITEM.match(line))
    questions = sum(1 for sentence, _, _ in probe.units(text) if probe.is_question(sentence))
    return max(items, questions)


def told_not_asked(text, probe, sim):
    """A mechanical stand-in for the full run's judge measure: the turn settles something ("I've gone with", "the
    answer is", "you should") and asks nothing at all."""
    asks = "?" in text or any(probe.is_question(s) for s, _, _ in probe.units(text))
    return not asks and bool(TELL_CUE.search(sim.normalize(text).replace("'", "")))


def voice_loaded(run, probe):
    """The share of sessions whose voice file was read before their first question to the lead (START step 0)."""
    tools = probe.assistant_tool_text(run)
    sessions = {}
    for entry in (e for e in run.transcript.spoken() if e["speaker"] == "assistant"):
        state = sessions.setdefault(entry.get("session"), {"read": False, "asked": False})
        if state["asked"]:
            continue
        if VOICE_FILE in tools.get(entry["turn"], ""):
            state["read"] = True
        if "?" in entry["text"]:
            state["asked"] = True
    if not sessions:
        return 0.0
    return sum(1 for s in sessions.values() if s["read"]) / len(sessions)


def voice_measures(run, probe, sim):
    turns = [e for e in run.transcript.spoken() if e["speaker"] == "assistant"]
    n = len(turns)
    codes = [lead_codes(e["text"]) for e in turns]
    return [
        measure("voice: codes and IDs per turn", round(sum(codes) / n, 3) if n else 0.0, better=LOWER),
        measure("voice: score (turns with no code, of 100)", round(100 * sum(1 for c in codes if not c) / n) if n else 0,
                100),
        measure("voice: turns that told rather than asked", sum(told_not_asked(e["text"], probe, sim) for e in turns),
                n, LOWER),
        measure(f"voice: turns offering more than {say.LEAD_LIMIT} things",
                sum(things_offered(e["text"], probe) > say.LEAD_LIMIT for e in turns), n, LOWER),
        measure("voice: voice-loading step ran (share of sessions)", round(voice_loaded(run, probe), 3), 1),
    ]


# ------------------------------------------------------------------ the scaled checks

def register(probe):
    """Add the scaled checks to probe.CHECKS. Each returns (passed, summary, detail, measure)."""
    sim, check = probe.sim, probe.check

    def share_line(what, value, of, need):
        return f"{what}: {value} of {of} ({probe.pct(value / of if of else 0)}; need at least {probe.pct(need)})"

    @check("gaps-raised", "at_least")
    def gaps_raised(run, criterion):
        """The U items, which the lead was never told, that the assistant raises as an issue before any lead turn
        names them: FLAGGED as flagged-share reads it (a real question, a flag cue on its line, or a new unknown or
        risk holding it). A gap's keywords name the document facts it rests on, so reading a document back (LISTED)
        never counts; seeing what the facts imply and saying so does."""
        spoken = run.transcript.spoken()
        final, start = probe.flag_spots(sim.vault_pages(run.vault)), probe.flag_spots(sim.vault_pages(run.snapshot))
        items = run.persona.get("unaware") or []
        value, detail = 0, []
        for item in items:
            row = probe.item_flags(item, spoken, final, start)
            turns = [t for t in (row["hit"]["turn"] if row["status"] == "flagged" else None,
                                 asked_in_line(item, spoken, probe, sim)) if t]
            raised = min(turns) if turns else None
            lead = probe.first_turn(spoken, "lead", item["keywords"])
            first = raised is not None and (lead is None or raised < lead)
            value += first
            how = "" if row["status"] == "flagged" or not raised else f" A question on its line at T{raised}."
            detail.append(probe.flag_line(row) + how + (" RAISED FIRST" if first else
                                                        f" (lead first at T{lead})" if lead and raised else ""))
        passed = bool(items) and value / len(items) >= criterion["at_least"]
        return (passed, share_line("gaps the lead hadn't noticed, raised first", value, len(items), criterion["at_least"]),
                detail, measure("gaps raised first", value, len(items)))

    @check("positions-surfaced", "at_least")
    def positions_surfaced(run, criterion):
        """Stakeholder positions of any kind (a fact the lead gives only when asked about its subject counts), each
        surfaced in full: the disagreement named, who holds it named, and recorded as open."""
        final, start = probe.flag_spots(sim.vault_pages(run.vault)), probe.flag_spots(sim.vault_pages(run.snapshot))
        items = probe.brief_items(run.persona, ["stakeholder-conflict"])
        rows = [(i, probe.conflict_parts(i, run.transcript.spoken(), final, start)) for i in items]
        full = sum(1 for _, p in rows if p["named"] and p["side"] and p["recorded"])
        heard = sum(1 for _, p in rows if p["named"])
        passed = bool(rows) and full / len(rows) >= criterion["at_least"]
        summary = share_line("stakeholder positions surfaced in full", full, len(rows), criterion["at_least"]) + \
            f"; disagreement named for {heard}"
        detail = [f"- {i['id']}: named {p['named'] and 'T%d' % p['named'] or 'no'}, side "
                  f"{p['side'] and 'T%d' % p['side'] or 'no'}, recorded {'yes' if p['recorded'] else 'no'}" for i, p in rows]
        return passed, summary, detail, measure("positions surfaced in full", full, len(rows))

    @check("ready-decided", "at_least")
    def ready_decided(run, criterion):
        """The persona's decisions with an `item:` on the snapshot: the ready ones decided with a yes, and the
        blocked ones (`blocked: true`) left undecided. Decided is the item's state in the final vault; with a yes is
        bounded by the decisions the driver pinned to a turn after a yes on that item's page."""
        decisions = [d for d in run.persona.get("decisions") or [] if d.get("item")]
        ready = [d for d in decisions if not d.get("blocked")]
        blocked = [d for d in decisions if d.get("blocked")]
        states = {d["item"]: item_state(run.vault, d["item"], sim) for d in decisions}
        decided_ready = [d for d in ready if states[d["item"]] == "decided"]
        yes_by_file = {}
        for d in run.decisions:
            yes_by_file[d["file"]] = yes_by_file.get(d["file"], 0) + bool(d["with_yes"])
        files = {}
        for d in decided_ready:
            files.setdefault(item_file(run.vault, d["item"], sim), []).append(d)
        value = sum(min(len(ds), yes_by_file.get(rel, 0)) for rel, ds in files.items())
        bad = sum(1 for d in blocked if states[d["item"]] == "decided")
        passed = bool(ready) and value / len(ready) >= criterion["at_least"] and bad == 0
        summary = (share_line("ready items decided after the lead's yes", value, len(ready), criterion["at_least"])
                   + f"; blocked items decided: {bad} of {len(blocked)} (need 0)")
        detail = [f"- {d['id']} {d['item']} ({'blocked' if d.get('blocked') else 'ready'}): {states[d['item']] or 'not found'}"
                  for d in decisions]
        return passed, summary, detail, measure("ready items decided with a yes", value, len(ready))

    @check("unsure-proposed", "at_least")
    def unsure_proposed(run, criterion):
        """The open questions the lead knows of (facts with `open_question: true`), each named in an assistant turn
        that proposes who to ask or by when and asks. The unsure-owner check's unconfirmed writes ride along: any
        fails the run."""
        items = [k for k in run.persona.get("knows") or [] if k.get("open_question")]
        spoken = [e for e in run.transcript.spoken() if e["speaker"] == "assistant"]
        rows = []
        for item in items:
            turn = next((e["turn"] for e in spoken if sim.mentions(e["text"], item["keywords"])
                         and proposes_then_asks(e["text"], probe)), None)
            rows.append((item, turn))
        value = sum(1 for _, turn in rows if turn)
        _, owner_summary, owner_detail = probe.CHECKS["unsure-owner-asked"][0](run, {"at_most": 0})
        found = re.search(r"without the lead's confirmation: (\d+)", owner_summary)
        unconfirmed = int(found.group(1)) if found else 0
        passed = bool(items) and value / len(items) >= criterion["at_least"] and unconfirmed == 0
        summary = (share_line("open questions given a proposed owner or date and asked", value, len(items),
                              criterion["at_least"]) + f"; owners or dates written unconfirmed: {unconfirmed} (need 0)")
        detail = [f"- {i['id']}: {'T%d' % t if t else 'never proposed'}" for i, t in rows] + owner_detail
        return passed, summary, detail, measure("open questions proposed and asked", value, len(items))


def proposes_then_asks(text, probe):
    """A proposal of who to ask or by when, asked about later in the same turn. A session that names several loose
    ends, proposes a role and a date for them, gives its reason and asks once at the end did the behavior; the
    unsure-owner check's 200-character window scored that 0 of 6 on the 2026-10-16 dev baseline (a sensor miss, not
    a skill one). "Due to" is a cause, not a date, so it doesn't count once the window is gone."""
    if "|due|" not in probe.PROPOSAL_CUE:
        raise ValueError("probe.PROPOSAL_CUE no longer lists |due|, so 'due to' would count as a proposal")
    cue = re.compile(probe.PROPOSAL_CUE.replace("|due|", "|due(?! to)|"), re.I)
    return any("?" in text[m.end():] for m in cue.finditer(text))


def asked_in_line(item, spoken, probe, sim):
    """The first assistant turn whose line (a list line, or a paragraph's line of prose) names the item and asks a
    real question about it: "Go-live lands in the freeze. How does that fit?" raises the freeze even though the
    question sentence doesn't repeat the word. A confirmation tag ("right?") is not a question, as in flagged-share."""
    for entry in (e for e in spoken if e["speaker"] == "assistant"):
        for line in entry["text"].splitlines():
            if sim.mentions(line, item["keywords"]) and any(
                    probe.is_question(s) for s in probe.SENTENCE_END.split(line.strip()) if s.strip()):
                return entry["turn"]
    return None


def vela_vault(root):
    """The vault as vela's own parser reads it (parse.parse_page, then model.build), without its config: the probe
    reads states the way the plan's gates do, not by a regex of its own that could drift from the format."""
    paths, others = cli.vault_files(root)
    pages = [parse.parse_page(p.relative_to(root).as_posix(), p.read_text(encoding="utf-8")) for p in paths]
    return model.build(pages, {}, others)


def _located(parsed, item_id):
    """(page path, state or None) for a heading item (its **State:** fact) or a page (its `state:` front matter);
    None when the vault does not hold the ID."""
    item = parsed.item(item_id)
    if item is not None:
        return item.page.path, item.fact("State").lower() or None
    pages = parsed.by_id.get(item_id)
    if not pages:
        return None
    state = pages[0].meta.get("state")
    return pages[0].path, str(state).strip().lower() if state else None


def item_states(vault, ids):
    """id -> its state, or None when the vault does not hold it or gives it none. The one state reader of the probe
    loop: decided-items (probe.py, read after every turn) and ready-decided (here, the final vault) both call it."""
    ids = list(ids)
    if not ids:
        return {}
    parsed = vela_vault(vault)
    return {i: (found[1] if (found := _located(parsed, i)) else None) for i in ids}


def item_state(vault, item_id, sim=None):
    return item_states(vault, [item_id])[item_id]


def item_file(vault, item_id, sim=None):
    found = _located(vela_vault(vault), item_id)
    return found[0] if found else None


# ------------------------------------------------------------------ mean, spread and the rule

def summarize(records):
    """{measure name: {values, mean, spread, of, better}} over the runs that finished without a tool failure."""
    out = {}
    for record in records:
        if record.get("failure"):
            continue
        for m in record.get("measures") or []:
            row = out.setdefault(m["name"], {"values": [], "of": m.get("of"), "better": m["better"]})
            row["values"].append(m["value"])
            if row["of"] != m.get("of"):
                row["of"] = None  # out of a different number each run (such as turns), so said without one
    for row in out.values():
        values = row["values"]
        row["mean"] = round(statistics.fmean(values), 3)
        row["spread"] = round(statistics.stdev(values), 3) if len(values) > 1 else 0.0
    return out


def summary_lines(summary, oracle=False):
    if not summary:
        return ["summary: no run finished, so there is nothing to average"]
    runs = max(len(r["values"]) for r in summary.values())
    head = (f"summary over {runs} run(s), mean ± spread (sample standard deviation)"
            + ("; ORACLE run: this is the reachable ceiling, not a skill score" if oracle else ""))
    lines = [head]
    for name, row in summary.items():
        of = f" of {row['of']}" if row["of"] not in (None, 0) else ""
        lines.append(f"  {name}: {row['mean']:g}{of} ± {row['spread']:g}  ({', '.join(f'{v:g}' for v in row['values'])}; "
                     f"{row['better']} is better)")
    lines.append("  a change is real only when its mean moves by more than the larger of the two spreads")
    return lines


def compare(before, after):
    """Per measure both summaries hold: the move, the threshold, and whether it is a real gain, a real loss or noise."""
    rows = []
    for name, b in before.items():
        a = after.get(name)
        if a is None:
            continue
        delta = round(a["mean"] - b["mean"], 3)
        threshold = max(a["spread"], b["spread"])
        signed = delta if b["better"] == HIGHER else -delta
        verdict = "gain" if signed > threshold else "loss" if -signed > threshold else "noise"
        rows.append({"name": name, "before": b["mean"], "after": a["mean"], "delta": delta, "threshold": threshold,
                     "verdict": verdict, "voice": name.startswith("voice:")})
    return rows
