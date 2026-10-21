"""Vela is MIT licensed, and the license travels with what the marketplace installs (plugin/), not only the repo."""
import json

from conftest import REPO


def test_the_plugin_ships_the_same_license_as_the_repo():
    assert (REPO / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    assert (REPO / "plugin" / "LICENSE").read_bytes() == (REPO / "LICENSE").read_bytes()


def test_the_manifests_say_mit():
    plugin = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert plugin["license"] == "MIT" and market["plugins"][0]["license"] == "MIT"
