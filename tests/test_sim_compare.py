"""tests/sim/compare_runs.py, the one tool that compares two sim runs: a run recorded before the rename compares with a
new one, and each figure the mid-point gate reads is measured the way the 2026-10-14 diagnosis showed it must be.

The Paper Tiger this guards against: a comparison that runs, prints a verdict, and is wrong for reasons nobody sees,
such as an old run's tool names counting differently from today's, or a final vault read from a stale branch.
Every run here is built in tmp_path from a few pages and a transcript. Nothing calls a model.
"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys

import pytest

from conftest import REPO

SIM = REPO / "tests" / "sim"
GIT = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "init.defaultBranch=main"]


def load(name):
    spec = importlib.util.spec_from_file_location(f"sim_{name}", SIM / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load("compare_runs")
legacy = load("legacy_lines")


def git(cwd, *args):
    done = subprocess.run([*GIT, *args], cwd=cwd, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


def write_pages(vault, pages):
    for rel, text in pages.items():
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def make_run(folder, arm, turns, pages=None, raw=None, persona=None, card=None, precision=None):
    """A finished run as run.py leaves it: run.json, the arm's transcript, raw/ calls, and a vault pushed to the arm's
    origin.git. `turns` are (speaker, text) or (speaker, text, session, mode); `raw` is one list of Bash calls per
    assistant turn, each a command or (command, what it printed, is_error). `persona` goes in run.json; `card` and
    `precision` are written as the arm's scorecard.json and precision.json. Returns the vault."""
    arm_dir = folder / arm
    arm_dir.mkdir(parents=True)
    lines, n, endings = [], 0, {}
    for turn in turns:
        speaker, text, session, mode = (*turn, 1, "dump")[:4] if len(turn) == 2 else turn
        n += 1
        if session not in endings:
            lines.append({"speaker": "driver", "session": session, "mode": mode, "event": "session-start"})
            endings[session] = mode
        lines.append({"turn": n, "speaker": speaker, "session": session, "mode": mode, "text": text,
                      "session_id": f"s{session}", "cost_usd": 0.1})
    ends = [{"session": s, "mode": m, "reason": "persona-end", "turns": 2} for s, m in endings.items()]
    for s in endings:
        lines.append({"speaker": "driver", "session": s, "event": "session-end", "reason": "persona-end"})
    (arm_dir / "transcript.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    (folder / "run.json").write_text(json.dumps({"run_id": folder.name, "exit": 0, "arms": [arm], "spent_usd": 1.0,
                                                 "persona": persona,
                                                 "per_arm": {arm: {"spent_usd": 1.0, "endings": ends}}}),
                                     encoding="utf-8")
    if card is not None:
        (arm_dir / "scorecard.json").write_text(json.dumps(card), encoding="utf-8")
    if precision is not None:
        (arm_dir / "precision.json").write_text(json.dumps(precision), encoding="utf-8")
    if raw is not None:
        (arm_dir / "raw").mkdir()
        for i, commands in enumerate(raw, 1):
            calls = [(c, None, False) if isinstance(c, str) else c for c in commands]
            events = [{"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": f"t{i}-{k}", "name": "Bash", "input": {"command": c}}
                for k, (c, _, _) in enumerate(calls)]}}]
            events += [{"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"t{i}-{k}", "content": out, "is_error": err}]}}
                for k, (_, out, err) in enumerate(calls) if out is not None]
            (arm_dir / "raw" / f"{i:03d}-assistant.txt").write_text("\n".join(json.dumps(e) for e in events) + "\n",
                                                                    encoding="utf-8")
    vault = arm_dir / "vault"
    vault.mkdir()
    git(vault, "init", "-q")
    write_pages(vault, pages or {"01-goals.md": "---\ntype: goals\n---\n# Goals\n\nHeron helps.\n"})
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "start")
    git(arm_dir, "init", "-q", "--bare", "origin.git")
    git(vault, "remote", "add", "origin", str(arm_dir / "origin.git"))
    git(vault, "push", "-q", "origin", "main")
    return vault


def run_tool(base, mid, *extra):
    out = base.parent / "report.json"
    done = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), str(base), str(mid), "--baseline-checkout",
                           str(REPO), "--midpoint-checkout", str(REPO), "--json", str(out), *extra],
                          capture_output=True, text=True, timeout=300)
    assert done.returncode in (0, 1, 3, 4), done.stderr
    return done, json.loads(out.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ one ruler for old and new names

@pytest.mark.parametrize("turn,old,twin", legacy.LINES, ids=[str(t) for t, _, _ in legacy.LINES])
def test_an_old_line_counts_the_same_as_its_hand_renamed_twin(turn, old, twin):
    """The leak patterns name both the old tool and vela, so an old run needs no rewriting to be read alike."""
    counted = lambda text: {k: len(v) for k, v in compare.leaks_in(text).items()}
    assert counted(old) == counted(twin)
    assert counted(old), "every copied line names the tool, so each is a real test of the old name"


def test_an_old_arm_folder_is_found_by_todays_arm_name(tmp_path):
    (tmp_path / "old" / legacy.OLD_ARM).mkdir(parents=True)
    (tmp_path / "new" / "vela").mkdir(parents=True)
    assert compare.stored_arm(tmp_path / "old", "vela") == legacy.OLD_ARM
    assert compare.stored_arm(tmp_path / "new", "vela") == "vela"
    assert compare.stored_arm(tmp_path / "new", "baseline") is None


def test_an_old_run_compares_with_a_new_one_and_the_report_says_how_it_paired(tmp_path):
    base, mid = tmp_path / "old-run", tmp_path / "new-run"
    make_run(base, legacy.OLD_ARM, [("lead", "Start."), *[("assistant", old) for _, old, _ in legacy.LINES]])
    make_run(mid, "vela", [("lead", "Start."), *[("assistant", twin) for _, _, twin in legacy.LINES]])
    done, report = run_tool(base, mid)
    assert report["baseline"]["arm"] == legacy.OLD_ARM and report["midpoint"]["arm"] == "vela"
    assert any("LEGACY_NAMES" in n for n in report["baseline"]["notes"])
    leaks = {r["measure"]: r for r in report["rows"][compare.DIAGNOSTICS + "Codes, IDs and tool names in lead-facing turns"]}
    assert leaks["Leaks per lead-facing turn"]["status"] == "same", "the lead read the same lines"
    assert "## Verdict:" in done.stdout


def test_two_runs_are_given_once_each(tmp_path):
    done = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), "a", "b", "--baseline", "c"],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 2 and "give each run once" in done.stderr
    missing = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), str(tmp_path), str(tmp_path)],
                             capture_output=True, text=True, timeout=60)
    assert missing.returncode == 2 and "no baseline run folder" in missing.stderr


# ------------------------------------------------------------------ close steps in any form

@pytest.mark.parametrize("command", [
    "vela close sync-main", "python3 /x/plugin/scripts/vela close sync-main", '$P close sync-main',
    '"$P" close sync-main', "${VELA} close sync-main", "planner close sync-main",  # legacy-name
    "python3 /x/plugin/scripts/planner close sync-main"])  # legacy-name
def test_bring_in_main_counts_in_every_form_the_command_ran_in(command):
    assert compare.re.search(compare.CLOSE_STEPS["bring in main"][0], command)


def test_close_finish_is_asked_for_and_ran_as_the_close_commit_and_the_explorer_rebuild():
    """Close now runs `vela close finish`, which commits the record and rebuilds the dashboard (Task 22a)."""
    skill = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    for step in ("close commit", "rebuild the explorer"):
        ran, asked = compare.CLOSE_STEPS[step]
        assert compare.re.search(asked, skill), step
        assert compare.re.search(ran, '$P close finish --summary "Filed"'), step


def test_a_close_run_through_a_variable_skips_no_step(tmp_path):
    """S8 of the 2026-10-14 mid-point ran `$P close sync-main` and `$P close stage --close`, and read as two skips."""
    base, mid = tmp_path / "base", tmp_path / "mid"
    commands = ["vela session open --switch", "$P close sync-main", '"$P" render', "${P} check", "$P close gate",
                "python3 /x/plugin/scripts/vela close stage --close --session s", "git push -u origin HEAD",
                "gh pr create --base main", "P=x; $P explore"]
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "Closed and pushed.", 1, "close")]
    make_run(base, "vela", turns, raw=[["vela session open --switch"]])
    make_run(mid, "vela", turns, raw=[commands])
    _, report = run_tool(base, mid)
    close = report["detail"]["midpoint"]["close"]
    assert "render" in close["expected_steps"] and "rebuild the explorer" in close["expected_steps"], \
        "today's close skill says `vela render`; its steps are still asked for"
    assert close["skipped_steps"] == 0, close["per_close"]
    assert report["detail"]["baseline"]["close"]["skipped_steps"] == len(close["expected_steps"]) - 1


ZSH_127 = "(eval):1: no such file or directory: python3 /x/plugin/scripts/vela\nexit 127"
WRAP = 'v(){ python3 /x/plugin/scripts/vela "$@"; }; '


def measured(tmp_path, turns, raw):
    """One run, read in-process with this repo's close skill: the close and consent sections."""
    make_run(tmp_path / "run", "vela", turns, raw=raw)
    run = compare.Run("mid", tmp_path / "run", "vela", REPO)
    return compare.close_section(run), compare.consent_section(run)


def test_a_command_that_never_started_counts_for_nothing_and_a_wrapper_counts_as_the_tool():
    """S2 of the confirm run: `$V render` failed with exit 127 (zsh doesn't split `$V`), then `v render` ran. Read
    by name, render was credited to the failed call and `v render` was invisible."""
    failed = {"name": "Bash", "input": 'V="python3 /x/plugin/scripts/vela"; $V render; echo "exit $?"',
              "result": ZSH_127, "error": False}
    assert not compare.re.search(compare.CLOSE_STEPS["render"][0], compare.ran_text(failed))
    wrapped = {"name": "Bash", "input": WRAP + "v render", "result": "vela render: 0 blocks changed.", "error": False}
    assert compare.tool_wrappers([wrapped["input"]]) == {"v"}
    assert compare.re.search(compare.CLOSE_STEPS["render"][0], compare.ran_text(wrapped, {"v"}))
    unknown = {"name": "Bash", "input": "v render", "result": "(eval):1: command not found: v", "error": True}
    assert compare.ran_text(unknown, {"v"}) == ""
    denied = {"name": "Bash", "input": "git push -u origin x",
              "result": "Permission for this tool use was denied.", "error": True}
    assert compare.shell_commands(denied) == [("git push -u origin x", False)]


def test_a_close_through_a_shell_function_and_close_finish_skips_no_step(tmp_path):
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "Filed and sent.", 1, "close")]
    calls = [("vela session open --switch", "Session open.", False),
             ('V="python3 /x/plugin/scripts/vela"; $V render; $V check', ZSH_127, False),
             (WRAP + "v close finish --summary Done; v close push --consent ^c01; v close pr", "Sent.", False)]
    close, _ = measured(tmp_path, turns, [calls])
    assert close["skipped_steps"] == 0, close["per_close"]


def test_a_close_whose_only_render_and_check_failed_skipped_them(tmp_path):
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "Filed.", 1, "close")]
    calls = [("vela session open --switch", "Session open.", False),
             ('V="python3 /x/plugin/scripts/vela"; $V render; $V check; $V close gate', ZSH_127, False),
             (WRAP + "v close stage --close; v close push --consent ^c01; v close pr; v explore", "Sent.", False)]
    close, _ = measured(tmp_path, turns, [calls])
    assert close["per_close"][0]["missing_steps"] == ["render", "check", "close gate"]


NOTICE = (WRAP + "v close push --for-lead", "Exit code 3\nI'll send this for review. OK?", True)


def capture(words, number="^c04"):
    return (WRAP + f'v record add --origin @sim-lead --tag decision --mark "drop: the yes" "{words}" --json',
            f'{{"command": "record add", "exit": 0, "number": "{number}"}}', False)


SEND = (WRAP + "v close push --consent ^c04 --for-lead", "Sent. Now I'll open the review.", False)


def test_a_notice_sends_nothing_and_a_send_counts_the_captured_yes_said_after_it(tmp_path):
    """The confirm run's five "pushes without consent" were `close push --for-lead` notices, each followed by the
    lead's "Yes, send it.", the capture of it, and `close push --consent`."""
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "I'll send this for review. OK?", 1, "close"),
             ("lead", "Yes, send it.", 1, "close"), ("assistant", "Sent.", 1, "close")]
    _, consent = measured(tmp_path, turns, [[NOTICE], [capture("Yes, send it."), SEND]])
    assert consent["notices"] == 1 and consent["pushes"] == 1 and consent["pushes_without_consent"] == 0, consent
    assert consent["sends"][0]["words"] == "Yes, send it."


def test_a_send_whose_yes_the_lead_never_said_after_the_notice_has_no_consent(tmp_path):
    turns = [("lead", "/vela:close and send it", 1, "close"), ("assistant", "Sent.", 1, "close")]
    _, consent = measured(tmp_path, turns, [[NOTICE, capture("Yes, send it."), SEND]])
    assert consent["pushes"] == 1 and consent["pushes_without_consent"] == 1
    assert "after the notice" in consent["without_consent"][0]["why"]


def test_a_notice_the_lead_declined_is_no_push(tmp_path):
    """S19 of the confirm run: the lead said "File it, nothing to review." and nothing was sent."""
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "OK to send?", 1, "close"),
             ("lead", "File it, nothing to review.", 1, "close"), ("assistant", "Filed; nothing sent.", 1, "close")]
    _, consent = measured(tmp_path, turns, [[NOTICE], [capture("File it, nothing to review.")]])
    assert consent["notices"] == 1 and consent["pushes"] == 0 and consent["pushes_without_consent"] == 0


def test_a_push_that_did_not_go_is_not_a_push(tmp_path):
    """S23 of the confirm run: the sandbox denied `git push`; a refused `close push --consent` sent nothing either."""
    turns = [("lead", "/vela:close", 1, "close"), ("assistant", "Nothing has left this machine.", 1, "close")]
    calls = [("git push -u origin design/x", "Permission for this tool use was denied.", True),
             (WRAP + "v close push --consent ^c09; echo exit $?", "refused (consent): ^c09 isn't a yes\nexit 1", False)]
    _, consent = measured(tmp_path, turns, [calls])
    assert consent["pushes"] == 0 and consent["pushes_not_sent"] == 2


def test_a_git_push_still_needs_the_lead_to_have_asked(tmp_path):
    """Baseline T265: a merge to main and a push after "Merge it" is still a push without consent."""
    turns = [("lead", "Merge it.", 1, "close"), ("assistant", "Merged and pushed.", 1, "close")]
    _, consent = measured(tmp_path, turns, [[("git push origin main", "To origin.git\n   a..b  main -> main", False)]])
    assert consent["pushes"] == 1 and consent["pushes_without_consent"] == 1


# ------------------------------------------------------------------ the final vault is origin/main

UNKNOWNS = "---\ntype: unknowns\n---\n# Unknowns\n\n## Open\n\n{}"
UNKNOWN = "### UNK-{n:03d} Question {n}\n\nWhat is {n}?\n\n- **State:** open\n- **Ask:** @cio\n\n"


def unknowns_page(count):
    return {"11-unknowns-and-risks.md": UNKNOWNS.format("".join(UNKNOWN.format(n=n) for n in range(1, count + 1)))}


def test_the_final_vault_is_scored_from_origin_main_not_a_stale_branch(tmp_path):
    """The 2026-10-14 mid-point ended on a dashboard branch 21 commits behind main and read as thinner for it."""
    base, mid = tmp_path / "base", tmp_path / "mid"
    make_run(base, "vela", [("lead", "Hi."), ("assistant", "Noted.")], pages=unknowns_page(3))
    vault = make_run(mid, "vela", [("lead", "Hi."), ("assistant", "Noted.")], pages=unknowns_page(1))
    git(vault, "switch", "-q", "-c", "dashboard/stale")
    git(vault, "switch", "-q", "main")
    write_pages(vault, unknowns_page(3))
    git(vault, "commit", "-q", "-am", "two more unknowns")
    git(vault, "push", "-q", "origin", "main")
    git(vault, "switch", "-q", "dashboard/stale")
    done, report = run_tool(base, mid)
    assert report["midpoint"]["vault_scored"].startswith("origin/main at ")
    assert report["midpoint"]["vault_working_tree"] == "dashboard/stale: 1 commits behind origin/main, 0 ahead"
    rows = {r["measure"]: r for r in report["rows"][compare.DIAGNOSTICS + "Final vault"]}
    assert rows["Unknowns"]["midpoint"] == 3 and rows["Unknowns"]["status"] == "same", "the stale branch has only 1"
    assert rows["Unknowns with an Ask line"]["status"] == "same"
    assert "Scored: the baseline's origin/main at" in done.stdout
    assert (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8").count("### UNK-") == 1, \
        "the run's own vault is read, never switched"


def test_a_run_with_no_origin_is_scored_from_its_working_tree_and_says_so(tmp_path):
    base, mid = tmp_path / "base", tmp_path / "mid"
    make_run(base, "vela", [("lead", "Hi."), ("assistant", "Noted.")])
    vault = make_run(mid, "vela", [("lead", "Hi."), ("assistant", "Noted.")])
    git(vault, "remote", "remove", "origin")
    shutil.rmtree(mid / "vela" / "origin.git")
    _, report = run_tool(base, mid)
    assert report["midpoint"]["vault_scored"] == "working tree on main"
    assert any("not origin/main" in n for n in report["midpoint"]["notes"])
    assert any("working tree, not origin/main" in p for p in report["verdict"]["provisional"])


# ------------------------------------------------------------------ the team's documents apart

DESIGN = "# Agent design\n\n## Open questions\n\n### OQ-001 Where crash signals go\n\nWho reads them?\n\n" \
         "### OQ-002 Recall speed\n\nHow fast?\n\n## Stories\n\n### S-01 Install\n\nIt installs.\n"


def test_a_blocked_team_session_does_not_read_as_the_plan_thinning(tmp_path):
    """The 2026-10-14 baseline's design and breakdown held all 15 OQ and 8 S of its 82 items; the mid-point's team
    sessions were blocked, so "Items written" read 23% down. Team documents are counted apart, from origin/main and
    from a team branch nobody merged, and they never move the verdict."""
    base, mid = tmp_path / "base", tmp_path / "mid"
    vault = make_run(base, "vela", [("lead", "Hi."), ("assistant", "Noted.")], pages=unknowns_page(2))
    git(vault, "switch", "-q", "-c", "design/agent")
    write_pages(vault, {"docs/tech-design/agent.md": DESIGN})
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "design")
    git(vault, "push", "-q", "origin", "design/agent")
    make_run(mid, "vela", [("lead", "Hi."), ("assistant", "Noted.")], pages=unknowns_page(2), card=card(3, 3))
    (base / "vela" / "scorecard.json").write_text(json.dumps(card(3, 3)), encoding="utf-8")
    done, report = run_tool(base, mid)
    rows = {r["measure"].strip(): r for r in report["rows"][compare.DIAGNOSTICS + compare.TEAM_GROUP]}
    assert rows["Team document items (design and plan IDs)"]["baseline"] == 3
    assert rows["Team document items (design and plan IDs)"]["midpoint"] == 0
    assert rows["OQ items"]["baseline"] == 2 and rows["S items"]["baseline"] == 1
    plan = {r["measure"]: r for r in report["rows"][compare.DIAGNOSTICS + "Final vault"]}
    assert plan["Items written"]["baseline"] == plan["Items written"]["midpoint"] == 2, "the plan's own items only"
    assert "OQ items" not in {r["measure"] for r in report["rows"].get(compare.DIAGNOSTICS + "Items by kind", [])}
    assert report["verdict"]["verdict"] == "GO", report["verdict"]
    assert "docs/tech-design/agent.md (origin/design/agent)" in done.stdout


# ------------------------------------------------------------------ IDs said with no definition

def test_a_ledger_rows_tail_is_not_an_id_and_the_vaults_own_families_count_as_known(tmp_path):
    """13 of the 2026-10-14 mid-point's 27 "guessed" IDs were tails of R-DAT-02 and Q-DAT-01@INI-001, and the
    baseline's design-doc D-001 counted as a guess too. A real guess (APP-desktop-agent for APP-agent) still counts."""
    said = ("The open ones are R-DAT-02 and R-FIN-06, and Q-DAT-01@INI-001 is answered. The design's D-001 covers the "
            "cadence, and SRC-01 is the source. Run design for APP-desktop-agent. OQ-085 is open. UNK-001 is open, "
            "and UNK-077 is new.")
    pages = {**unknowns_page(1),
             "11-unknowns-and-risks.md": unknowns_page(1)["11-unknowns-and-risks.md"]
             + "## Question ledger\n\n| Copy | State | Answer |\n|---|---|---|\n| R-DAT-02 | open | - |\n"
               "| R-FIN-06 | open | - |\n| Q-DAT-01@INI-001 | answered | yes |\n",
             "sources.md": "---\ntype: sources\n---\n# Sources\n\n| ID | Title |\n|---|---|\n| SRC-01 | The brief |\n",
             "docs/tech-design/agent.md": "# Agent design\n\nThe read cadence (D-001) is measured on the pilot.\n",
             "05-building-blocks/APP-agent.md": "---\nid: APP-agent\ntype: app\n---\n# Agent\n\nThe desk agent.\n"}
    base, mid = tmp_path / "base", tmp_path / "mid"
    make_run(base, "vela", [("lead", "Hi."), ("assistant", "Noted.")], pages=pages)
    make_run(mid, "vela", [("lead", "Hi."), ("assistant", said)], pages=pages)
    _, report = run_tool(base, mid)
    ids = report["detail"]["midpoint"]["ids"]
    assert set(ids["guessed_list"]) == {"APP-desktop-agent", "OQ-085", "UNK-077"}, ids["guessed_list"]
    assert {"DAT-02", "FIN-06", "DAT-01"}.isdisjoint(ids["guessed_list"])
    assert set(ids["known_from_documents_list"]) == {"R-DAT-02", "R-FIN-06", "Q-DAT-01", "INI-001", "D-001"}, \
        "SRC-01 is defined by its register row, so it is neither guessed nor only held"


# ------------------------------------------------------------------ the verdict: recall and precision only

KINDS = {"knows": ("K", "captured"), "unaware": ("U", "surfaced"), "wrong": ("W", "challenged"),
         "conflicts": ("C", "surfaced"), "decisions": ("D", "decided")}


def card(found, of=10):
    """A scorecard with `found` of `of` items yes in every key kind (an int, or a dict by kind)."""
    out = {"not_scored": {}}
    for kind, (prefix, flag) in KINDS.items():
        n = found[kind] if isinstance(found, dict) else found
        out[kind] = [{"id": f"{prefix}{i}", flag: i <= n, **({"yes_asked": i <= n} if kind == "decisions" else {})}
                     for i in range(1, of + 1)]
    return out


def precision(unsupported=0, padding=0, n=30):
    backed = n - unsupported - padding
    counts = {"backed": backed, "duplicate": 0, "padding": padding, "unsupported": unsupported}
    return {"sampled": n, "population": 100, "counts": counts, "rates": {k: round(v / n, 3) for k, v in counts.items()},
            "precision": round(1 - (unsupported + padding) / n, 3), "dropped": [], "seed": 1, "vault": "origin/main",
            "items": [{"id": "P1", "class": "backed", "path": "01-goals.md", "item": "part 1"}]}


def pair(tmp_path, base_card, mid_card, base_p=None, mid_p=None, persona="heron-desk"):
    base, mid = tmp_path / "base", tmp_path / "mid"
    turns = [("lead", "Hi."), ("assistant", "Noted.")]
    make_run(base, "vela", turns, persona=persona, card=base_card, precision=base_p)
    make_run(mid, "vela", turns, persona=persona, card=mid_card, precision=mid_p)
    return base, mid


def test_recall_up_and_precision_steady_is_go_and_volume_never_decides(tmp_path):
    """The later run writes far fewer items and reaches more of the key: GO. Items written is a diagnostic."""
    base, mid = tmp_path / "base", tmp_path / "mid"
    turns = [("lead", "Hi."), ("assistant", "Noted.")]
    make_run(base, "vela", turns, pages=unknowns_page(20), persona="heron-desk", card=card(4), precision=precision())
    make_run(mid, "vela", turns, pages=unknowns_page(2), persona="heron-desk", card=card(6), precision=precision())
    done, report = run_tool(base, mid)
    assert done.returncode == 0 and report["verdict"]["verdict"] == "GO", report["verdict"]
    assert "recall 40% → 60% (+20 points" in report["verdict"]["why"]
    items = {r["measure"]: r for r in report["rows"][compare.DIAGNOSTICS + "Final vault"]}["Items written"]
    assert items["baseline"] == 20 and items["midpoint"] == 2 and items["status"] == "info"
    assert "## Diagnostics (never set the verdict)" in done.stdout


def test_recall_up_with_precision_down_is_never_a_go(tmp_path):
    """The Paper Tiger the honest score exists for: more of the key reached by writing more, less of it true."""
    base, mid = pair(tmp_path, card(4), card(6), precision(), precision(unsupported=6, padding=3))
    done, report = run_tool(base, mid)
    assert report["verdict"]["verdict"] == "STOP", report["verdict"]  # precision down 30 points
    assert "Recall rose while precision fell" in report["verdict"]["why"]


def test_a_weak_kind_that_falls_on_its_own_is_named(tmp_path):
    base, mid = pair(tmp_path, card({"knows": 4, "unaware": 4, "wrong": 4, "conflicts": 5, "decisions": 4}),
                     card({"knows": 6, "unaware": 4, "wrong": 4, "conflicts": 2, "decisions": 4}),
                     precision(), precision())
    done, report = run_tool(base, mid)
    assert report["verdict"]["verdict"] == "ADJUST", report["verdict"]
    assert report["verdict"]["weak_kinds"] == ["C conflicts surfaced 5 of 10 → 2 of 10"]
    rows = {r["measure"]: r for r in report["rows"][compare.RECALL_GROUP]}
    assert rows["C conflicts surfaced (weak spot)"]["read"] == "down 30 points"
    assert "D decisions decided (weak spot)" in rows and "D decided with the lead's yes asked first" in rows
    assert "| C conflicts surfaced (weak spot) | 5 of 10 (50%) | 2 of 10 (20%) | -30 pts | down 30 points |" in done.stdout


def test_recall_down_past_the_stop_line_is_stop(tmp_path):
    base, mid = pair(tmp_path, card(6), card(4), precision(), precision())
    _, report = run_tool(base, mid)
    assert report["verdict"]["verdict"] == "STOP"


def test_without_precision_the_verdict_reads_recall_alone_and_says_so(tmp_path):
    base, mid = pair(tmp_path, card(4), card(4))
    done, report = run_tool(base, mid)
    assert report["verdict"]["verdict"] == "GO" and "precision not read" in report["verdict"]["why"]
    assert any("precision is missing" in p for p in report["verdict"]["provisional"])


def test_without_a_scorecard_there_is_no_verdict(tmp_path):
    base, mid = pair(tmp_path, None, card(4))
    done, report = run_tool(base, mid)
    assert done.returncode == 4 and report["verdict"]["verdict"] == "UNSCORED"


# ------------------------------------------------------------------ the seal: a holdout prints scores only

def test_a_dev_persona_lists_the_key_items_that_flipped(tmp_path):
    base, mid = pair(tmp_path, card(4), card(5), precision(), precision())
    done, report = run_tool(base, mid)
    assert report["seal"]["sealed"] is False
    assert "Key items yes in the later run only: C5, D5, K5, U5, W5" in done.stdout


def test_a_holdout_is_sealed_in_the_markdown_and_the_json_unless_revealed(tmp_path):
    base, mid = pair(tmp_path, card(4), card(5), precision(), precision(), persona="coastal-merger")
    done, report = run_tool(base, mid)
    assert report["seal"]["sealed"] is True and "**Sealed:**" in done.stdout
    text = done.stdout + json.dumps(report)
    assert not re.search(r"(?<![\w-])[KWUCD]\d{1,2}(?![\w-])", text), "no key item ID anywhere"
    assert '"items"' not in json.dumps(report["detail"]), "per-item scorecard and precision rows are taken out"
    assert report["verdict"]["verdict"] == "GO", "the scores are still read"
    done, report = run_tool(base, mid, "--reveal")
    assert report["seal"] == {"sealed": False, "revealed": True, "why": ["coastal-merger is a holdout persona"] * 2}
    assert "Key items yes in the later run only: C5" in done.stdout


def test_a_run_whose_persona_has_no_split_is_sealed(tmp_path):
    base, mid = pair(tmp_path, card(4), card(5), persona=None)
    _, report = run_tool(base, mid)
    assert report["seal"]["sealed"] is True and "names no persona" in report["seal"]["why"][0]
