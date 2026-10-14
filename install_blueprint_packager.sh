#!/usr/bin/env bash
# One-command installer for the Blueprint Packager (macOS / Linux).
#
#   bash install_blueprint_packager.sh            # into ./blueprint-packager/
#   bash install_blueprint_packager.sh ~/tools    # into a folder of your choice
#
# The repository is public. With the `gh` command signed in (`gh auth login`)
# this fetches the latest release; without it, git clones `main`.
# It fetches the latest release (or main when no release exists yet) into
# <folder>/brightspace-blueprint-packager-v<version>/, writes the pointer the
# launchers use, and starts the runner. Re-running installs a newer release
# beside the old one; nothing is deleted.
set -euo pipefail

REPO="timebeing92/brightspace-blueprint-packager"
TARGET_DIR="${1:-blueprint-packager}"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"
ROOT="$(pwd)"

have_gh() { command -v gh >/dev/null 2>&1 && gh auth status --hostname github.com >/dev/null 2>&1; }

TAG=""
if have_gh; then
  TAG="$(gh release view --repo "$REPO" --json tagName -q .tagName 2>/dev/null || true)"
fi

if [ -n "$TAG" ] && have_gh; then
  echo "== downloading release $TAG"
  TMP="$(mktemp -d)"
  gh release download "$TAG" --repo "$REPO" --pattern '*.zip' --dir "$TMP" --clobber
  ZIP="$(ls "$TMP"/*.zip | head -n1)"
  TOP="$(unzip -Z1 "$ZIP" | head -n1 | cut -d/ -f1)"
  if [ -d "$ROOT/$TOP" ]; then
    echo "   $TOP is already installed."
  else
    unzip -q "$ZIP" -d "$ROOT"
    echo "   unpacked $TOP"
  fi
  rm -rf "$TMP"
  printf '%s\n' "$TOP" > "$ROOT/.blueprint-packager-current"
  INSTALLED="$ROOT/$TOP"
else
  if ! command -v git >/dev/null 2>&1; then
    echo "git is required for this install path (or sign in with gh to download a release)." >&2
    exit 1
  fi
  NAME="brightspace-blueprint-packager-main"
  if [ -d "$ROOT/$NAME/.git" ]; then
    echo "== $NAME is present; pulling main"
    git -C "$ROOT/$NAME" pull --ff-only
  else
    echo "== no release found or no gh; cloning main (no gh signed in to fetch the release)"
    if have_gh; then gh repo clone "$REPO" "$ROOT/$NAME"
    else git clone "https://github.com/$REPO.git" "$ROOT/$NAME" || {
      echo "The clone was refused: check the network, or sign in with 'gh auth login' and rerun." >&2
      exit 1; }
    fi
  fi
  printf '%s\n' "$NAME" > "$ROOT/.blueprint-packager-current"
  INSTALLED="$ROOT/$NAME"
fi

{
  printf 'installed_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'folder=%s\n' "$INSTALLED"
  printf 'release=%s\n' "${TAG:-main}"
} > "$ROOT/INSTALL_RECEIPT.txt"

echo
echo "Installed into: $INSTALLED"
echo "Receipt:        $ROOT/INSTALL_RECEIPT.txt"
echo "Start it later with:  bash \"$INSTALLED/blueprint_packager.sh\""
echo

if [ -t 0 ]; then
  exec bash "$INSTALLED/blueprint_packager.sh"
elif (exec < /dev/tty) 2>/dev/null; then
  exec bash "$INSTALLED/blueprint_packager.sh" < /dev/tty
else
  echo "No terminal is attached; run the launcher above when you are at one."
fi
