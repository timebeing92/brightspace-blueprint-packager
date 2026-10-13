# Releasing

A release is one tagged commit, one ZIP, and one manifest. The guided runner's
update check and the installer find it through GitHub Releases. Nothing below
is run by CI on its own; the owner cuts the release.

## Cut a release

1. Bump `__version__` in `blueprint_packager/__init__.py` and write the entry in
   `CHANGELOG.md`: what changed, whether the Workbench pin moved, and what
   evidence the release has and has not (a tenant round is never implied).
   Update the status line in `README.md` and the release block in
   `CAPABILITIES.json`.
2. Run the suite: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q`.
   The update test archives the previous release's tag, so the tags must be in
   the checkout (`git fetch --tags`).
3. Commit and push, then wait for CI (`.github/workflows/ci.yml`) to pass on
   that commit: the suite at Python 3.11 through 3.14 on Linux, at 3.11 and
   3.14 on Windows and at 3.11 on macOS; and the release ZIP of the commit
   built, installed, reinstalled, tampered with and repaired, then started
   through the real launchers on all three platforms.
4. Tag the passed commit and push the tag:

   ```bash
   git tag -a v<version> -m "Blueprint Packager v<version>"
   git push origin v<version>
   ```

5. Build from the tag, naming it. The builder archives the tag's commit, reads
   the version and the vendor pin from that commit (never from the working
   tree), refuses a dirty worktree, and refuses a tag that is missing, points
   elsewhere, or is not `v<version>` of that tree:

   ```bash
   python3 scripts/make_release_bundle.py --ref v<version> --tag v<version>
   ```

   This writes `dist/brightspace-blueprint-packager-v<version>.zip` and a
   `.sha256` sidecar. Inside the ZIP is one folder of the same name holding a
   clean `git archive` of the commit plus `release_manifest.json`: the version,
   the tag, the commit, the date, every file's SHA-256, the Workbench commit the
   vendored engine is pinned at, and a `build` block saying the tag was verified.
   Never pass `--allow-dirty` here; it only ever builds an unreleased ZIP of the
   committed tree, with `"tag": null`.
6. Publish the ZIP and its sidecar as the only assets. The installer and the
   shell installers take the first `.zip` they find, so there must be exactly
   one:

   ```bash
   gh release create v<version> dist/brightspace-blueprint-packager-v<version>.zip \
       dist/brightspace-blueprint-packager-v<version>.zip.sha256 \
       --repo timebeing92/brightspace-blueprint-packager --title "v<version>" --notes-file RELEASE_NOTES.md
   ```

   The release notes can be the changelog entry.
7. Smoke-test the published asset, from the download, in an empty folder:

   ```bash
   python3 scripts/smoke_test_release.py --tag v<version> --report docs/evidence/RELEASE_SMOKE_v<version>.json
   ```

   It requires exactly one ZIP asset, checks the sidecar hash and the manifest
   against the tag, installs with the installer and reinstalls with the shipped
   one, starts the launcher (venv created, packages installed, doctor passed),
   writes and reads a blank, reads, builds and verifies a ready synthetic
   course, runs the Wizard conversion cycle from the installed copy, and runs
   the shipped suite there. Commit the JSON and Markdown report with a short
   post-release line in the changelog; the tag stays where it is.
8. Record the release wherever the ecosystem keeps its registry, if that is in
   scope for the release.

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
- Installing a version that is already in place checks every file the
  manifest lists against the installed folder; a missing or changed release
  file is refused by name, and `--repair` restores it from the verified
  archive. `.venv`, remembered answers, the update-check cache, logs and the
  receipt are never touched.
- `--restart` starts the new version straight away; the guided runner offers
  that when it shows the notice.

## Checks before publishing

- CI is green on the commit to be tagged (step 3).
- `python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench` says
  "no drift"; if the pin should move, re-pin first and note it in the changelog.
- The changelog entry says what the release's evidence is and is not.
