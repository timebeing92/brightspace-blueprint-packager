#!/usr/bin/env bash
# One-command installer for the Blueprint Packager (macOS / Linux).
#
#   bash install_blueprint_packager.sh            # into ./blueprint-packager/
#   bash install_blueprint_packager.sh ~/tools    # into a folder of your choice
#
# The repository is public. This fetches the latest release through the `gh`
# command when it is signed in, otherwise anonymously with curl (checking the
# published SHA-256), and clones `main` with git only when no release can be
# reached. BPK_INSTALL_NO_START=1 installs without starting the runner.
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
ZIP_URL=""
SHA_URL=""
if have_gh; then
  TAG="$(gh release view --repo "$REPO" --json tagName -q .tagName 2>/dev/null || true)"
fi
if [ -z "$TAG" ] && command -v curl >/dev/null 2>&1; then
  # the public release, read anonymously (one field per line in GitHub's answer)
  LATEST="$(curl -fsSL -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null || true)"
  TAG="$(printf '%s\n' "$LATEST" | grep -o '"tag_name": *"[^"]*"' | head -n1 | sed 's/.*"\([^"]*\)"$/\1/')"
  ZIP_URL="$(printf '%s\n' "$LATEST" | grep -o '"browser_download_url": *"[^"]*\.zip"' | head -n1 | sed 's/.*"\(https[^"]*\)"$/\1/')"
  SHA_URL="$(printf '%s\n' "$LATEST" | grep -o '"browser_download_url": *"[^"]*\.zip\.sha256"' | head -n1 | sed 's/.*"\(https[^"]*\)"$/\1/')"
  [ -n "$ZIP_URL" ] || TAG=""
fi

if [ -n "$TAG" ]; then
  echo "== downloading release $TAG"
  TMP="$(mktemp -d)"
  if have_gh; then
    gh release download "$TAG" --repo "$REPO" --pattern '*.zip' --pattern '*.zip.sha256' --dir "$TMP" --clobber
  else
    curl -fsSL -o "$TMP/${ZIP_URL##*/}" "$ZIP_URL"
    [ -z "$SHA_URL" ] || curl -fsSL -o "$TMP/${SHA_URL##*/}" "$SHA_URL"
  fi
  ZIP="$(ls "$TMP"/*.zip | head -n1)"
  if [ -f "$ZIP.sha256" ]; then
    if command -v shasum >/dev/null 2>&1; then CHECK="shasum -a 256 -c"; else CHECK="sha256sum -c"; fi
    (cd "$TMP" && $CHECK "$(basename "$ZIP").sha256" >/dev/null) || { echo "The download does not match its published SHA-256; stopping." >&2; exit 1; }
    echo "   SHA-256 matches the published sidecar"
  fi
  # read the whole listing: closing the pipe early would send unzip a SIGPIPE, which pipefail reports
  TOP="$(unzip -Z1 "$ZIP" | cut -d/ -f1 | sort -u | head -n1)"
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
    echo "== no release could be reached (no gh signed in, and no curl or no network); cloning main"
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

if [ "${BPK_INSTALL_NO_START:-}" = "1" ]; then
  exit 0
elif [ -t 0 ]; then
  exec bash "$INSTALLED/blueprint_packager.sh"
elif (exec < /dev/tty) 2>/dev/null; then
  exec bash "$INSTALLED/blueprint_packager.sh" < /dev/tty
else
  echo "No terminal is attached; run the launcher above when you are at one."
fi
