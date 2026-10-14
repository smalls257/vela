#!/usr/bin/env python3
"""Build the offline viewer for the reference fixture.

The viewer is `vela view`. This wrapper keeps the old entry point.
Usage: python3 examples/build-viewer.py
Output: examples/unified-booking-viewer.html
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
VELA = HERE.parent / "plugin" / "scripts" / "vela"

sys.exit(subprocess.call([sys.executable, str(VELA), "view", "--vault", str(HERE / "unified-booking"),
                          "--out", str(HERE / "unified-booking-viewer.html")]))
