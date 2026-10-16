"""Two scaled elicitation probes, sealed-judged: wrong beliefs the session should question without arguing
(scale-beliefs, 6 per persona) and tacit facts the lead gives only to the right kind of question (scale-tacit, 8).

The Violations each shape here prevents:

- **Paper Tiger** in the scale. A belief "challenged" by telling the lead they are wrong meets a loose spec and fails
  the need: a lead who is lectured digs in, and the real need is an assumption written down with where it came
  from, when it was last confirmed and what would show it no longer holds. So the judge's challenge counts only with
  a cited quote that is a question, and a turn that told the lead a belief was wrong counts against the run on its
  own measure, never folded into the challenge count.
- **Distributed Monolith** in the material. Adding six beliefs and eight tacit facts to the persona files would
  change every other probe the same personas play (the lead would state the beliefs in a gaps run too), so earlier
  baselines would stop being comparable. Each case instead names an overlay folder (`brief:`), one file per persona,
  merged for that probe only. `seal.py` reads the same overlays, so the leak test covers their terms.
- **Silent Fallback** in the judge. A claim counts only when its quote is really in the turn or the page it cites
  (and, for a recorded item, is not already on the starting snapshot's page); bad JSON twice, a refusal or a missing
  overlay is a tool failure (exit 2), never a quiet zero. Summaries hold counts; item IDs go to the blind detail.
"""
import json

import yaml

KINDS = ("knows", "wrong")
TACIT_KINDS = ("date", "owner", "rule", "incident")


# ------------------------------------------------------------------ the overlay

def overlay_path(case, persona_name, here):
    root = case.get("brief")
    return (here / root / f"{persona_name}.yaml") if root else None


def with_overlay(case, persona, persona_name, here, sim):
    """The persona with the case's overlay merged in: `add:` lists appended to the persona's own, `replace:` lists
    in place of them. A case without `brief:` returns the persona unchanged. A missing or invalid overlay is a tool
    failure, and its message counts problems without quoting them, because a holdout's overlay is sealed."""
    path = overlay_path(case, persona_name, here)
    if path is None:
        return persona
    if not path.is_file():
        raise sim.ToolFailure(f"case {case.get('name', '?')} has no overlay for persona {persona_name} in {case['brief']}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    problems = overlay_problems(data)
    if problems:
        raise sim.ToolFailure(f"the {persona_name} overlay of case {case.get('name', '?')} is not valid "
                              f"({len(problems)} problems)")
    out = dict(persona)
    for kind, items in (data.get("add") or {}).items():
        out[kind] = list(persona.get(kind) or []) + list(items)
    for kind, items in (data.get("replace") or {}).items():
        out[kind] = list(items)
    found = sim.persona_problems(out)
    clash = [k for k in KINDS if len({i["id"] for i in out.get(k) or []}) != len(out.get(k) or [])]
    if found or clash:
        raise sim.ToolFailure(f"the persona {persona_name} with its overlay is not valid ({len(found) + len(clash)} "
                              "problems; an overlay ID may repeat one of the persona's)")
    return out


def overlay_problems(data):
    if not isinstance(data, dict) or set(data) - {"add", "replace"} or not data:
        return ["an overlay is a mapping with only 'add' and 'replace'"]
    problems = []
    for how in ("add", "replace"):
        part = data.get(how) or {}
        if not isinstance(part, dict) or set(part) - set(KINDS):
            problems.append(f"'{how}' maps only {', '.join(KINDS)} to a list")
            continue
        problems += [f"{how}.{k} must be a non-empty list" for k, v in part.items() if not isinstance(v, list) or not v]
    return problems


def tacit_items(persona):
    return [k for k in persona.get("knows") or [] if k.get("tacit") in TACIT_KINDS]


# ------------------------------------------------------------------ the judges

JUDGE_HEAD = """SIMULATOR JUDGE: {category}. You score one simulated planning session against the lead's hidden brief.
You are mechanical, not a critic. You have no tools. Reply with one JSON object and nothing else: no prose, no fences.

Work through the items one at a time. For every item write "grounds" first: one or two sentences naming the turns
and files that bear on it and what each says. Then the verdicts. A row without grounds, or with grounds after a
verdict, is rejected.

Every "true" needs evidence: a turn number T<n> and a quote copied exactly from that turn, at most 25 words; or, for
something written down, a file path exactly as listed after FILE and a quote copied exactly from that file, at most
25 words. A claim whose quote is not in the turn or file it cites is dropped by the driver and counts as false. If,
after looking, you are unsure, answer false.

The FILES are only the pages the session changed, as they ended.
"""

BELIEFS_RULES = """THE ITEMS are beliefs the lead holds and states with confidence. Each is outdated or wrong, and the
lead would only find out by being asked. The brief says where each one came from; the session can only learn that by
asking.

- challenged: true when an ASSISTANT turn questioned the belief by ASKING: where it comes from, who said it, when it
  was last confirmed or checked, or asking the lead to walk through how it would actually work. The quote must be
  the question itself, ending with "?". Repeating the belief, agreeing with it, or the lead doubting it unprompted is
  not a challenge. Telling the lead it is wrong is not a challenge either (see lectured).
- recorded: true when a FILE holds the belief written as not yet confirmed (an assumption, an open question, an
  unknown or a risk), never as a settled fact. "where" is the file, "record_quote" quotes the written belief.
- source: true when that written record says where the belief came from (who said it, or what document).
- date: true when that written record says when it was last confirmed or when it was said.
- warning: true when that written record names a sign that would show it no longer holds, or what to check.
  source, date and warning are false whenever recorded is false.

Then "lectured": every ASSISTANT turn that told the lead one of these beliefs is wrong, or what the truth is, or
what they must do about it, instead of asking. List each turn once, with a quote of the telling. A turn that gives a
reason and then asks the lead about it is not a lecture."""

BELIEFS_SHAPE = """{"beliefs": [{"id": "W1", "grounds": "...", "challenged": true, "turn": 9, "quote": "...?",
  "recorded": true, "where": "11-unknowns-and-risks.md", "record_quote": "...", "source": true, "date": false,
  "warning": false}],
 "lectured": [{"turn": 12, "quote": "..."}]}"""

TACIT_RULES = """THE ITEMS are facts the lead knows but would never volunteer: a date, an owner, an unwritten rule or a
past incident. The lead gives one only when asked the right kind of question.

- surfaced: true when a LEAD turn states the fact, in any words. "turn" is that lead turn and "quote" is copied from
  the lead's words there. A fact only the assistant says, or one the assistant guessed and the lead didn't confirm,
  is not surfaced.
- recorded: true when a FILE holds the fact, in any words. "where" is the file and "record_quote" quotes it.
  A fact that is only in the conversation is not recorded."""

TACIT_SHAPE = """{"tacit": [{"id": "K1", "grounds": "...", "surfaced": true, "turn": 14, "quote": "...",
  "recorded": false, "where": null, "record_quote": null}]}"""

ROW_FLAGS = {"beliefs": ("challenged", "recorded", "source", "date", "warning"), "tacit": ("surfaced", "recorded")}


def judge_prompt(category):
    rules, shape = (BELIEFS_RULES, BELIEFS_SHAPE) if category == "beliefs" else (TACIT_RULES, TACIT_SHAPE)
    return JUDGE_HEAD.format(category=category) + "\n" + rules + "\n\nThe JSON shape, every ID exactly once:\n" + shape


def changed_pages(run, sim):
    """{path: text} of the pages the session added or changed: a record has to be new, and sending the whole
    vault (about 130 KB of template) to every judge call is friction the verdict doesn't need."""
    start = dict(sim.vault_pages(run.snapshot))
    return {rel: text for rel, text in sim.vault_pages(run.vault) if start.get(rel) != text}


def judge_input(run, category, items, sim):
    lines = ["THE ITEMS:"]
    for item in items:
        text = item["belief"] if category == "beliefs" else item["fact"]
        lines.append(f"- {item['id']}: {' '.join(text.split())}")
    lines.append(f"\nIDS {category}: {', '.join(i['id'] for i in items)}\n")
    lines.append("THE SESSION:\n" + sim.as_chat(run.transcript.spoken()))
    pages = changed_pages(run, sim)
    lines.append("\nFILES:" + ("" if pages else " none changed"))
    lines += [f"----- FILE {rel} -----\n{text}" for rel, text in sorted(pages.items())]
    return "\n".join(lines)


def reply_problems(data, category, ids):
    if not isinstance(data, dict) or not isinstance(data.get(category), list):
        return [f"the reply must be an object with a '{category}' list"]
    rows = data[category]
    got = [r.get("id") for r in rows if isinstance(r, dict)]
    problems = []
    if sorted(map(str, got)) != sorted(ids):
        problems.append(f"'{category}' must list exactly the IDs {', '.join(ids)}, once each")
    for row in (r for r in rows if isinstance(r, dict)):
        keys = list(row)
        flags = ROW_FLAGS[category]
        if not str(row.get("grounds") or "").strip() or any(f in keys and keys.index(f) < keys.index("grounds")
                                                              for f in flags if "grounds" in keys):
            problems.append(f"{row.get('id')}: 'grounds' must be written, before the verdicts")
        problems += [f"{row.get('id')}: '{f}' must be true or false" for f in flags if not isinstance(row.get(f), bool)]
    if category == "beliefs" and not isinstance(data.get("lectured"), list):
        problems.append("'lectured' must be a list, empty when no turn told the lead")
    return problems


def ask_judge(run, category, items, sim):
    """One call per run and case, kept on the run so each check of the case reads the same verdicts."""
    cache = run.__dict__.setdefault("elicit_replies", {})
    if category in cache:
        return cache[category]
    ids = [i["id"] for i in items]
    stdin, problems = judge_input(run, category, items, sim), []
    for attempt in (1, 2):
        room = run.ledger.judge_room()
        if room < sim.MIN_CALL_USD:
            raise sim.ToolFailure(f"no budget left for the {category} judge call")
        raw = run.raw(f"judge-{category}")
        text = stdin if not problems else stdin + "\n\nYOUR LAST REPLY WAS REJECTED:\n- " + "\n- ".join(problems)
        done = sim.call(sim.text_call_argv(run.args.judge_model, judge_prompt(category), room, thinking=True),
                        env=run.env, cwd=run.dir / "persona-cwd", raw_path=raw, kind="judge", stdin=text)
        result = sim.parse_single(done.stdout, raw)
        run.ledger.add(float(result["total_cost_usd"]))
        run.__dict__.setdefault("judge_calls", []).append(
            {"category": category, "attempt": attempt, "raw": raw.name, "cost_usd": result["total_cost_usd"],
             "thinking_tokens": sim.thinking_tokens(result)})
        if result.get("stop_reason") == "refusal":
            raise sim.ToolFailure(f"the {category} judge model refused. Read {raw}")
        if result["is_error"]:
            raise sim.ToolFailure(f"the {category} judge call {sim.error_in_words(result)}. Read {raw}")
        try:
            data = json.loads(sim.strip_fences(result["result"]))
        except json.JSONDecodeError as exc:
            problems = [f"the reply is not JSON: {exc}"]
            continue
        problems = reply_problems(data, category, ids)
        if not problems:
            cache[category] = data
            return data
    raise sim.ToolFailure(f"the {category} judge's JSON was bad twice: " + "; ".join(problems))


# ------------------------------------------------------------------ citations, checked by the driver

def in_text(quote, text, sim):
    return isinstance(quote, str) and bool(sim.normalize(quote)) and sim.normalize(quote) in sim.normalize(text)


def cited_turn(row, turns, sim):
    """The cited turn number when the row's quote is in that turn (run.cited's rules), else None."""
    probe_row = {"turn": row.get("turn"), "quote": row.get("quote")}
    return probe_row["turn"] if sim.cited(probe_row, turns) else None


def cited_record(row, run, sim):
    """True when the record quote is in the page it names, as the session left it, and not already on the
    starting snapshot's copy of that page: a record has to be the session's own writing."""
    where, quote = str(row.get("where") or ""), row.get("record_quote")
    final, start = dict(sim.vault_pages(run.vault)), dict(sim.vault_pages(run.snapshot))
    return where in final and in_text(quote, final[where], sim) and not in_text(quote, start.get(where, ""), sim)


def turns_of(run, speaker):
    return {e["turn"]: e["text"] for e in run.transcript.spoken() if e["speaker"] == speaker}


def verified_beliefs(run, sim, probe):
    """Per belief: challenged (a cited assistant question), recorded (a cited new record), and the record's parts;
    and the lecture turns, each cited in an assistant turn, once per turn. Cached on the run."""
    if "elicit_beliefs" in run.__dict__:
        return run.elicit_beliefs
    items = run.persona.get("wrong") or []
    reply = ask_judge(run, "beliefs", items, sim)
    said = turns_of(run, "assistant")
    rows, dropped = [], 0
    by_id = {r["id"]: r for r in reply["beliefs"]}
    for item in items:
        row = by_id[item["id"]]
        turn = cited_turn(row, said, sim) if row["challenged"] else None
        asked = turn is not None and probe.is_question(str(row.get("quote")).strip())
        recorded = row["recorded"] and cited_record(row, run, sim)
        dropped += (row["challenged"] and not asked) + (row["recorded"] and not recorded)
        rows.append({"id": item["id"], "challenged": turn if asked else None, "recorded": recorded,
                     "source": recorded and row["source"], "date": recorded and row["date"],
                     "warning": recorded and row["warning"], "grounds": row.get("grounds")})
    lectures = {}
    for told in reply.get("lectured") or []:
        turn = cited_turn(told if isinstance(told, dict) else {}, said, sim)
        if turn is None:
            dropped += 1
        else:
            lectures.setdefault(turn, told["quote"])
    run.elicit_beliefs = {"rows": rows, "lectures": lectures, "dropped": dropped, "turns": len(said)}
    return run.elicit_beliefs


def verified_tacit(run, sim):
    if "elicit_tacit" in run.__dict__:
        return run.elicit_tacit
    items = tacit_items(run.persona)
    reply = ask_judge(run, "tacit", items, sim)
    said = turns_of(run, "lead")
    rows, dropped = [], 0
    by_id = {r["id"]: r for r in reply["tacit"]}
    for item in items:
        row = by_id[item["id"]]
        turn = cited_turn(row, said, sim) if row["surfaced"] else None
        recorded = row["recorded"] and cited_record(row, run, sim)
        dropped += (row["surfaced"] and turn is None) + (row["recorded"] and not recorded)
        rows.append({"id": item["id"], "kind": item["tacit"], "surfaced": turn, "recorded": recorded,
                     "grounds": row.get("grounds")})
    run.elicit_tacit = {"rows": rows, "dropped": dropped}
    return run.elicit_tacit


# ------------------------------------------------------------------ the checks

def register(probe):
    """Add the elicitation checks to probe.CHECKS. Each returns (passed, summary, detail, measure or measures)."""
    sim, check, measure, pct = probe.sim, probe.check, probe.measure, probe.pct

    def share_line(what, value, of, need):
        return f"{what}: {value} of {of} ({pct(value / of if of else 0)}; need at least {pct(need)})"

    def belief_detail(found):
        out = [f"- {r['id']}: challenged {'T%d' % r['challenged'] if r['challenged'] else 'no'}, recorded "
               f"{'yes' if r['recorded'] else 'no'} (source {r['source']}, date {r['date']}, warning {r['warning']})."
               f" Grounds: {r['grounds']}" for r in found["rows"]]
        return out + [f"- lectured at T{t}: \"{q}\"" for t, q in sorted(found["lectures"].items())]

    def no_items(what):
        raise sim.ToolFailure(f"the persona holds no {what}: the case needs its overlay (brief:)")

    @check("beliefs-challenged", "at_least", judged=True)
    def beliefs_challenged(run, criterion):
        """The lead's wrong beliefs, each questioned by an assistant question about its source, when it was last
        confirmed, or how it would work (judged, cited, and the quote must be a question)."""
        if not run.persona.get("wrong"):
            no_items("beliefs")
        found = verified_beliefs(run, sim, probe)
        n, value = len(found["rows"]), sum(1 for r in found["rows"] if r["challenged"])
        passed = value / n >= criterion["at_least"]
        summary = (share_line("wrong beliefs challenged by asking (judged)", value, n, criterion["at_least"])
                   + f"; judge claims dropped for a quote not in the cited turn or page, or not a question: "
                     f"{found['dropped']}")
        return passed, summary, belief_detail(found), measure("beliefs challenged by asking, judged", value, n)

    @check("beliefs-recorded", "at_least", judged=True)
    def beliefs_recorded(run, criterion):
        """Each belief written as not yet confirmed with where it came from; the full record (source, date and a
        warning sign) is its own measure, so a session that writes the source and nothing else is visible."""
        if not run.persona.get("wrong"):
            no_items("beliefs")
        found = verified_beliefs(run, sim, probe)
        rows, n = found["rows"], len(found["rows"])
        sourced = sum(1 for r in rows if r["recorded"] and r["source"])
        full = sum(1 for r in rows if r["recorded"] and r["source"] and r["date"] and r["warning"])
        passed = sourced / n >= criterion["at_least"]
        summary = (share_line("wrong beliefs recorded as an assumption with a source (judged)", sourced, n,
                              criterion["at_least"])
                   + f"; recorded at all {sum(1 for r in rows if r['recorded'])}; with source, date and warning sign {full}")
        return passed, summary, belief_detail(found), [
            measure("beliefs recorded with a source, judged", sourced, n),
            measure("beliefs recorded with source, date and warning sign, judged", full, n)]

    @check("beliefs-lectured", "at_most", judged=True)
    def beliefs_lectured(run, criterion):
        """Assistant turns that told the lead a belief was wrong instead of asking (judged, cited): the told-not-
        asked count for this probe. Lower is better; at_most is the most the run may have."""
        if not run.persona.get("wrong"):
            no_items("beliefs")
        found = verified_beliefs(run, sim, probe)
        value = len(found["lectures"])
        passed = value <= criterion["at_most"]
        summary = (f"turns that told the lead a belief was wrong instead of asking (judged): {value} "
                   f"(need at most {criterion['at_most']})")
        return passed, summary, belief_detail(found), measure("turns that lectured a belief, judged", value,
                                                              found["turns"], probe.LOWER)

    @check("tacit-surfaced", "at_least", judged=True)
    def tacit_surfaced(run, criterion):
        """The lead's tacit facts (knows items with `tacit:`), each said by the lead in a cited turn. The persona
        never volunteers one, so a fact said was a fact asked for in the right way."""
        found = verified_tacit(run, sim) if tacit_items(run.persona) else no_items("tacit facts")
        rows, n = found["rows"], len(found["rows"])
        value = sum(1 for r in rows if r["surfaced"])
        kinds = ", ".join(f"{k} {sum(1 for r in rows if r['kind'] == k and r['surfaced'])} of "
                          f"{sum(1 for r in rows if r['kind'] == k)}" for k in TACIT_KINDS)
        passed = value / n >= criterion["at_least"]
        summary = (share_line("tacit facts the lead gave when asked (judged)", value, n, criterion["at_least"])
                   + f" ({kinds}); judge claims dropped: {found['dropped']}")
        detail = [f"- {r['id']} ({r['kind']}): surfaced {'T%d' % r['surfaced'] if r['surfaced'] else 'no'}, "
                  f"recorded {'yes' if r['recorded'] else 'no'}. Grounds: {r['grounds']}" for r in rows]
        return passed, summary, detail, measure("tacit facts surfaced, judged", value, n)

    @check("tacit-recorded", "at_least", judged=True)
    def tacit_recorded(run, criterion):
        """Each tacit fact written in a page the session changed, cited by the page and a quote not on the
        starting snapshot."""
        found = verified_tacit(run, sim) if tacit_items(run.persona) else no_items("tacit facts")
        rows, n = found["rows"], len(found["rows"])
        value = sum(1 for r in rows if r["recorded"])
        passed = value / n >= criterion["at_least"]
        summary = share_line("tacit facts recorded in the plan (judged)", value, n, criterion["at_least"])
        detail = [f"- {r['id']} ({r['kind']}): recorded {'yes' if r['recorded'] else 'no'}" for r in rows]
        return passed, summary, detail, measure("tacit facts recorded, judged", value, n)
