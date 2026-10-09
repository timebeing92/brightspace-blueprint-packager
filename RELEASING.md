# Releasing

A release is one tagged commit, one ZIP, and one manifest. The guided runner's
update check and the installer find it through GitHub Releases.

## Cut a release

1. Bump `__version__` in `blueprint_packager/__init__.py` and add the entry to
   `CHANGELOG.md`. If the Workbench pin moved, say so in the entry.
2. Run the suite: `pytest -q`.
3. Commit, then tag: `git tag v<version>` and `git push origin main v<version>`.
4. Build the bundle from the tagged commit (the builder refuses a dirty tree):

   ```bash
   python3 scripts/make_release_bundle.py
   ```

   This writes `dist/brightspace-blueprint-packager-v<version>.zip` and a
   `.sha256` sidecar. Inside the ZIP is one folder of the same name holding a
   clean `git archive` of the commit plus `release_manifest.json`: the
   version, the tag, the commit, the date, every file's SHA-256, and the
   Workbench commit the vendored engine is pinned at.
5. Publish:

   ```bash
   gh release create v<version> dist/brightspace-blueprint-packager-v<version>.zip \
       dist/brightspace-blueprint-packager-v<version>.zip.sha256 \
       --repo timebeing92/brightspace-blueprint-packager --title "v<version>" --notes-file RELEASE_NOTES.md
   ```

   The release notes can be the changelog entry. The ZIP must be the only
   `.zip` asset; the installer downloads the first one it finds.

## How the check and the installer find it

- `scripts/update_check.py` asks GitHub for the latest release (`gh api`, or
  a `GITHUB_TOKEN`), caches the answer for a day in `.update_check.json`,
  compares the tag with `__version__`, and prints a notice once per newer
  version with the one command to update.
- `launcher/install_release.py --latest` downloads that release's ZIP
  (`gh release download`, or the asset URL with the token), refuses unsafe
  member names, unpacks to a staging folder, verifies every hash against the
  manifest, moves the folder beside the current install, carries
  `.last_run.json` over, and writes `.blueprint-packager-current` atomically
  so the launchers start the new version. The previous version stays.
- `--restart` starts the new version straight away; the guided runner offers
  that when it shows the notice.

## Checks before publishing

- `python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench` says
  "no drift"; if the pin should move, re-pin first and note it in the changelog.
- `bash blueprint_packager.sh --doctor` in a fresh clone of the tag passes.
- Unzip the bundle somewhere empty, double-click the launcher, and run a dry
  run on `docs/examples/blank_blueprint__8_weeks.docx`.
