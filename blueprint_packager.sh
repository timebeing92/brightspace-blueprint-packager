#!/usr/bin/env bash
# One-terminal launcher for the Blueprint Packager (macOS / Linux):
#     bash blueprint_packager.sh            # the guided runner
#     bash blueprint_packager.sh --doctor   # check the setup only
#     bash blueprint_packager.sh --plain    # no colour, art, or animation
#
# Finds Python 3.11+, creates a private .venv inside this folder on first run
# (asking first), installs requirements.txt into it, then starts the runner.
# Arguments pass straight through. Follows the Blueprint Wizard runner's
# blueprint_wizard.sh (brightspace-blueprint-runner, commit 85cef27).
set -euo pipefail

# No cd: the runner resolves its own files absolutely, and staying in the
# caller's directory lets relative paths on the command line work as typed.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSUME_YES=0
PLAIN=0
FORWARD=1
for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=1 ;;
    --plain) PLAIN=1 ;;
    --here) FORWARD=0 ;;
  esac
done

# A newer version installed beside this one (launcher/install_release.py writes
# the pointer) takes over, unless --here or BPK_NO_FORWARD=1 says to stay.
POINTER="$(dirname "$HERE")/.blueprint-packager-current"
if [ "$FORWARD" -eq 1 ] && [ -z "${BPK_NO_FORWARD:-}" ] && [ -f "$POINTER" ]; then
  CURRENT="$(dirname "$HERE")/$(head -n1 "$POINTER" | tr -d '[:space:]')"
  if [ -n "$(head -n1 "$POINTER" | tr -d '[:space:]')" ] && [ "$CURRENT" != "$HERE" ] && [ -f "$CURRENT/blueprint_packager.sh" ]; then
    echo "  Starting the current version in $(basename "$CURRENT") (pass --here to stay with this one)."
    export BPK_NO_FORWARD=1
    exec bash "$CURRENT/blueprint_packager.sh" "$@"
  fi
fi

python_ok() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

find_python() {
  local candidates=()
  if [ -n "${PYTHON:-}" ]; then candidates+=("$PYTHON"); fi
  candidates+=(python3.14 python3.13 python3.12 python3.11 python3)
  for py in "${candidates[@]}"; do
    if command -v "$py" >/dev/null 2>&1 && python_ok "$py"; then
      command -v "$py"
      return 0
    fi
  done
  return 1
}

ask_yes() {
  local prompt="$1" default="${2:-n}" reply
  if [ "$ASSUME_YES" -eq 1 ]; then return 0; fi
  if [ "$default" = "y" ]; then read -r -p "$prompt [Y/n] " reply; reply="${reply:-y}"
  else read -r -p "$prompt [y/N] " reply; reply="${reply:-n}"; fi
  case "$reply" in y|Y|yes|YES|Yes) return 0 ;; *) return 1 ;; esac
}

install_python() {
  echo "Python 3.11 or later was not found."
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        if ask_yes "Install Python with Homebrew now?" "y"; then brew install python@3.12; return 0; fi
      else
        echo "Homebrew was not found. Install Python 3.11+ from https://www.python.org/downloads/ and rerun this launcher."
      fi ;;
    Linux)
      if command -v apt-get >/dev/null 2>&1; then
        if ask_yes "Install Python, venv, and pip with apt now? This may ask for your sudo password." "y"; then
          sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip; return 0; fi
      elif command -v dnf >/dev/null 2>&1; then
        if ask_yes "Install Python with dnf now? This may ask for your sudo password." "y"; then sudo dnf install -y python3 python3-pip; return 0; fi
      else
        echo "No supported package manager was found. Install Python 3.11+ and rerun this launcher."
      fi ;;
    *) echo "Install Python 3.11+ for this platform and rerun this launcher." ;;
  esac
  return 1
}

if ! PY="$(find_python)"; then
  install_python || { echo "Cannot continue without Python 3.11 or later." >&2; exit 1; }
  PY="$(find_python)" || { echo "Python 3.11+ is still not on PATH. Set PYTHON=/path/to/python3 and rerun." >&2; exit 1; }
fi

VENV="$HERE/.venv"
VENV_PY="$VENV/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "First run: the packager keeps its Python packages in a private folder, $VENV."
  if ask_yes "Create it and install the packages from requirements.txt now?" "y"; then
    "$PY" -m venv "$VENV"
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet -r "$HERE/requirements.txt"
  else
    echo "Running with $PY instead; the runner will say if a package is missing."
    VENV_PY="$PY"
  fi
fi

exec "$VENV_PY" "$HERE/scripts/packager_tui.py" "$@"
