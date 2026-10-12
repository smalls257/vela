#!/usr/bin/env bash
# Builds this case's workspace. plugin eval runs it only with --scaffold.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scaffold.py" epics-empty stub
