"""Small plans for the sizing tests, built in tmp_path: apps, capabilities, releases, session stubs, a size choice."""
import pathlib
import shutil

from conftest import REPO
from vela import privaterecord

TEMPLATE = REPO / "plugin" / "template"


def from_template(tmp_path):
    root = pathlib.Path(tmp_path) / "plan"
    shutil.copytree(TEMPLATE, root)
    return root


def write_plan(root, apps=(), capabilities=(), releases=(), stubs=(), config=""):
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / ".vela.yaml").write_text("initiative: INI-001\ntitle: Scheduled jobs\n" + config, encoding="utf-8")
    blocks = root / "05-building-blocks"
    blocks.mkdir(exist_ok=True)
    for slug, change in apps:
        (blocks / f"{slug}-building-blocks.md").write_text(
            f"---\nid: APP-{slug}\ntype: app-building-blocks\ntitle: {slug.replace('-', ' ').title()}\n"
            f"state: inkling\nchange: {change}\nowner: \"@dana\"\nauthored: authored\n---\n"
            f"# {slug.replace('-', ' ').title()}\n\nDoes its job.\n", encoding="utf-8")
    caps = root / "capabilities"
    caps.mkdir(exist_ok=True)
    for n, change in enumerate(capabilities, 1):
        (caps / f"CAP-{n:03d}-capability-{n}.md").write_text(
            f"---\nid: CAP-{n:03d}\ntype: capability\ntitle: Capability {n}\norigin: proposed\nchange: {change}\n"
            f"state: inkling\nowner: \"@dana\"\nauthored: authored\n---\n\n# CAP-{n:03d} Capability {n}\n",
            encoding="utf-8")
    if releases:
        body = "".join(f"## Release {n}\n\n- **Target:** {target}\n- **State:** assumption\n\n"
                       for n, target in enumerate(releases, 1))
        (root / "04b-releases.md").write_text(
            "---\nid: releases\ntype: initiative-section\ntitle: Releases\nstate: assumption\nowner: \"@dana\"\n"
            "authored: mixed\n---\n\n# Releases\n\n" + body, encoding="utf-8")
    sessions = root / "sessions"
    sessions.mkdir(exist_ok=True)
    for stub in stubs:
        meta = {"type": "session", "date": stub["id"][:10], "modes": ["grill"], **stub}
        (sessions / f"{stub['id']}.md").write_text(privaterecord.render_stub(meta), encoding="utf-8")
    return root


def choose(band, because="[[2026-10-02-grill-a]] c14", date="2026-10-02"):
    return f'size:\n  band: {band}\n  because: "{because}"\n  date: "{date}"\n'


def sized(root):
    from vela import cli, sizing
    return sizing.of(cli.load_vault(pathlib.Path(root)))
