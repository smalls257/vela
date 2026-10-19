"""A person's capture must be words they typed (`vela/said.py`): the Silent Fallback in the consent path was that
`vela record add` defaulted the origin to the lead, so the model's own sentence passed as their yes."""
import json
import os
import subprocess
import sys

import pytest

from conftest import REPO, run
from sharing import make_vault
from test_close_gate_core import RECORD, judged
from test_record_add import add, record_of, started, typed
from vela import guard, said, say
from vela.edge import saidlog

PLUGIN = REPO / "plugin"
LAUNCHER = PLUGIN / "scripts" / "vela"
CAPTURE = "The team chose Tauri with Rust for the desktop app."


def fire_hook(folder, prompt, session="sess-1"):
    payload = {"hook_event_name": "UserPromptSubmit", "session_id": session, "cwd": str(folder), "prompt": prompt}
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", "said"], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return done.stdout


# ---- the hook is the edge: it writes the log and says nothing to the model ----

def test_the_plugin_registers_the_hook_on_user_prompt_submit():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert hooks["UserPromptSubmit"][0]["hooks"][0]["command"].endswith("hook said")


def test_the_hook_logs_the_message_with_a_timestamp_and_prints_nothing(tmp_path):
    vault = make_vault(tmp_path)
    assert fire_hook(vault, "Yes, go with Tauri.\nAnd keep the key behind an interface.") == ""
    log = vault / ".vela" / "said" / "sess-1.log"
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["text"] == "Yes, go with Tauri.\nAnd keep the key behind an interface."
    assert entry["at"].endswith("Z")


def test_the_log_is_never_staged_and_other_folders_are_left_alone(tmp_path):
    vault = make_vault(tmp_path)
    fire_hook(vault, "hello")
    assert guard.never_rule(".vela/said/sess-1.log") is not None
    elsewhere = tmp_path / "not-a-vault"
    elsewhere.mkdir()
    fire_hook(elsewhere, "hello")
    assert not (elsewhere / ".vela").exists()


# ---- the pure match: an excerpt of one message, nothing else ----

MESSAGES = ["Yes, I'd go with Tauri. It keeps the bundle small!", "Let's park the mobile app for now."]


@pytest.mark.parametrize("words", [
    "Yes, I'd go with Tauri.",
    '"yes i’d go with tauri"',  # case, curly quote, punctuation
    "It keeps   the bundle small",
    "park the mobile app",
    '"Park the mobile app." says park mobile',  # the quoted span is what the gates read
])
def test_an_exact_excerpt_of_one_message_passes(words):
    assert said.typed(words, MESSAGES)


@pytest.mark.parametrize("words", [
    CAPTURE,
    "Go with Tauri since it keeps the bundle small",  # a paraphrase
    "Yes, I'd go with Tauri and Rust.",  # an invented word
    "small. Let's park the mobile app",  # spans two messages
    "yes it",  # not contiguous
    "",
    "...",
])
def test_paraphrase_invented_or_empty_words_are_refused(words):
    assert not said.typed(words, MESSAGES)


def test_a_part_of_a_word_is_not_an_excerpt():
    assert not said.typed("go with Taur", MESSAGES)


# ---- record add ----

def test_the_models_sentence_as_the_leads_yes_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    typed(vault, "Yes, I'd go with Tauri.")
    before = record_of(vault).read_text(encoding="utf-8")
    code, out = add(vault, "--origin", "@priya", "--tag", "decision", CAPTURE, "--for-lead")
    assert code == 3
    assert out.strip() == "Those aren't words the person typed. Quote what they said, or record it as your own note."
    assert say.leak_in(out) is None
    assert record_of(vault).read_text(encoding="utf-8") == before


def test_a_refused_default_origin_capture_is_refused_the_same_way(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    typed(vault, "Yes, I'd go with Tauri.")
    assert run("whoami", "--vault", str(vault), "--set", "Priya-K")[0] == 0
    assert add(vault, "--tag", "decision", CAPTURE)[0] == 3


def test_the_models_own_words_keep_their_home(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    typed(vault, "Yes, I'd go with Tauri.")
    assert add(vault, "--origin", "claude", "--tag", "thought", CAPTURE) == (0, "^c01\n")
    assert add(vault, "--origin", "claude, from @priya", "--tag", "thought", CAPTURE)[0] == 0


def test_a_typed_excerpt_is_written_as_the_persons_own_words(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    typed(vault, "Yes, I'd go with Tauri. It keeps the bundle small!")
    assert add(vault, "--origin", "@priya", "--tag", "decision", '"I\'d go with Tauri."') == (0, "^c01\n")
    assert "(@priya) \"I'd go with Tauri.\"" in record_of(vault).read_text(encoding="utf-8")


# ---- no log: written unverified, said so, and never counted silently ----

def unverified_yes(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert not (vault / ".vela" / "said").exists()
    code, out = add(vault, "--origin", "@priya", "--tag", "decision", "Yes, decide it as read.", "--for-lead")
    assert code == 0, out
    return vault, out


def test_with_no_log_the_capture_is_written_unverified_and_the_line_says_so(tmp_path, monkeypatch):
    vault, out = unverified_yes(tmp_path, monkeypatch)
    assert "(@priya, unverified) Yes, decide it as read. ^c01" in record_of(vault).read_text(encoding="utf-8")
    assert "unverified" in out and say.leak_in(out) is None


def test_the_close_gate_lists_the_unverified_yes_and_does_not_count_it():
    captures = ["- [thought] (@lead, unverified) \"Yes, decide it as read.\" ^c04"]
    problems, consent = judged(captures, [f"| CON-003 | assumption | decided | [[{RECORD}#^c04]] |"])
    assert not consent and len(problems) == 1
    assert problems[0].plain == 'I couldn\'t check that you said "Yes, decide it as read." on Consent records. Did you say it?'
    assert say.leak_in(problems[0].plain) is None


def test_the_close_gate_counts_it_once_the_lead_has_confirmed(tmp_path, monkeypatch):
    vault, _ = unverified_yes(tmp_path, monkeypatch)
    assert run("record", "confirm", "--vault", str(vault), "^c01")[0] == 0
    line = next(l for l in record_of(vault).read_text(encoding="utf-8").splitlines() if l.endswith("^c01"))
    problems, consent = judged([line], [f"| CON-003 | assumption | decided | [[{RECORD}#^c01]] |"])
    assert not problems and consent


def test_confirming_a_capture_that_is_not_unverified_changes_nothing(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    add(vault, "--origin", "claude", "--tag", "idea", "one")
    before = record_of(vault).read_text(encoding="utf-8")
    assert run("record", "confirm", "--vault", str(vault), "1")[0] == 1
    assert record_of(vault).read_text(encoding="utf-8") == before


def test_a_removal_yes_that_is_unverified_does_not_count():
    from vela import closegate
    rows = closegate.change_rows(
        "## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n| K1 | x | removed | [[r#^c01]] |\n")
    said_by = closegate.captures("- [thought] (@lead, unverified) \"Yes, remove it.\" ^c01\n")
    assert not closegate.removal_agreed("K1", rows, said_by)


def test_the_stored_log_reads_back_through_the_edge(tmp_path):
    saidlog.append(tmp_path, "a b/c", "2026-10-14T09:00:00Z", "hello there")
    assert said.messages(saidlog.read_all(tmp_path)) == ["hello there"]
    assert saidlog.read_all(tmp_path / "empty") is None


# ---- the simulator's sessions run Claude Code with the plugin, so the hook fires there ----

def test_a_stub_session_fills_the_log_and_a_fake_yes_is_refused(tmp_path, monkeypatch):
    """tests/sim/stub/claude fires the plugin's own UserPromptSubmit hooks, as Claude Code does under --plugin-dir."""
    vault = started(tmp_path, monkeypatch)
    adds = [["--vault", str(vault), "--origin", "@priya", "--tag", "decision", "Yes, go with Tauri."],
            ["--vault", str(vault), "--origin", "@priya", "--tag", "decision", CAPTURE]]
    env = {**os.environ, "SIM_STUB_RECORD": json.dumps(adds)}
    stub = REPO / "tests" / "sim" / "stub" / "claude"
    done = subprocess.run([sys.executable, str(stub), "-p", "--plugin-dir", str(PLUGIN), "--", "Yes, go with Tauri."],
                          cwd=vault, env=env, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert said.messages(saidlog.read_all(vault)) == ["Yes, go with Tauri."]
    assert "record add exit 0" in done.stdout and "record add exit 3" in done.stdout
    text = record_of(vault).read_text(encoding="utf-8")
    assert "(@priya) Yes, go with Tauri. ^c01" in text and "Tauri with Rust" not in text


def test_an_unverified_yes_does_not_send_a_review():
    from vela.decisions import consent
    capture = said_capture("- [decision] (@lead, unverified) Yes, send it. ^c01")
    refusal = consent.from_the_lead(capture, "lead")
    assert refusal is not None and "couldn't check that you typed that yes" in refusal.plain
    assert say.leak_in(refusal.plain) is None


def said_capture(line):
    from vela import closegate
    return next(iter(closegate.captures(line).values()))
