#!/usr/bin/env python3
"""Build the offline viewer for the reference fixture.

The viewer is `planner view`. This wrapper keeps the old entry point.
Usage: python3 examples/build-viewer.py
Output: examples/unified-booking-viewer.html
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLANNER = HERE.parent / "plugin" / "scripts" / "planner"

sys.exit(subprocess.call([sys.executable, str(PLANNER), "view", "--vault", str(HERE / "unified-booking"),
                          "--out", str(HERE / "unified-booking-viewer.html")]))
