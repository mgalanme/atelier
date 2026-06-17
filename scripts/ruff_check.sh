#!/usr/bin/env bash
# WHAT: lints and formats every Python file in the project.
# WHY:  run before every commit, not after a failed one, to keep diffs clean.
# HOW:  run from the project root: ./scripts/ruff_check.sh
set -euo pipefail

ruff check . --fix
ruff format .
