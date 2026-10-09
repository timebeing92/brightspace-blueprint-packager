#!/usr/bin/env bash
# Double-clickable launcher for the Blueprint Packager (macOS).
# Finder opens this in Terminal; it then runs blueprint_packager.sh from this folder.
exec bash "$(dirname "$0")/blueprint_packager.sh" "$@"
