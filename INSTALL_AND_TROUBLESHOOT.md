# Install and troubleshoot

How the Blueprint Packager gets onto a machine, what the launcher does on
first run, and what to do when something does not start. The guided runner
itself is described in the README under "Guided install and run".

## Ways to install

| Way | When | What you get |
|---|---|---|
| `bash install_blueprint_packager.sh` (macOS, Linux) or the `.ps1` (Windows) | `gh` signed in (`gh auth login`) for the latest release; without `gh`, git clones `main` | the latest release in `./blueprint-packager/<version folder>/`, a pointer file beside it, and the runner started |
| A release ZIP from GitHub Releases, unzipped anywhere | you were given the ZIP | one folder, `brightspace-blueprint-packager-v<version>/`, with the launchers at its top |
| `git clone` of the repository | you develop on it or want `main` | the working tree; `bash blueprint_packager.sh` starts the runner from it |

The repository is public (since 2026-10-13). A release ZIP from GitHub
Releases works without any account at all; everything the packager needs is
inside the folder, including the engine files it builds with (see the README,
"The vendored engine"). The runner's update check and
`launcher/install_release.py --latest` still go through `gh` or a
`GITHUB_TOKEN` and say so when neither is there; reading the public release
without one is a planned change.

## What the launcher does on first run

1. Finds Python 3.11 or later (`python3.14`, `python3.13`, `python3.12`,
   `python3.11`, `python3`, or `$PYTHON`; on Windows the `py` launcher
   first). If none is found it offers to install one: Homebrew on macOS,
   apt or dnf on Linux, winget on Windows, each with a question first.
2. Offers to create a private `.venv` inside the folder and install
   `requirements.txt` into it. Saying no runs with the system Python instead;
   the runner then says which package is missing.
3. Starts `scripts/packager_tui.py`, passing any arguments through.

When a newer version has been installed beside this one by the updater, the
launcher says so and starts that one instead. `--here` or `BPK_NO_FORWARD=1`
keeps the folder you clicked.

## Updating

The runner says once a day when a newer release exists and offers to install
it beside this one and restart (`python3 launcher/install_release.py --latest`
does the same). The new folder gets its own `.venv` on first start; remembered
answers are carried over; nothing is deleted.

After an update, build from the blueprint again. The runner always re-reads
the document. On the command line, run `bpk.py read` on each DOCX before
`build`: a course model cached by an older version is refused with "Re-read
the DOCX", and re-reading never changes the source file.

Installing a version that is already in place does not just trust the old
receipt: every release file is checked against the manifest. If one is
missing or changed the install is refused and names it; add `--repair` to
restore those files from the verified archive. `.venv`, `.last_run.json`,
`.update_check.json`, `logs/` and the receipt are never touched.

## When it does not start

**"Python 3.11 or later was not found."** Install Python from
https://www.python.org/downloads/ (on Windows tick "Add python.exe to PATH"),
open a new terminal window so PATH refreshes, and run the launcher again. Or
point at one you already have: `PYTHON=/path/to/python3 bash blueprint_packager.sh`.

**macOS says the .command file is from an unidentified developer.** Right-click
`Blueprint Packager.command` and choose Open, once. Or run
`bash blueprint_packager.sh` in Terminal.

**Windows says scripts are disabled.** Use `Blueprint Packager.bat`, which runs
PowerShell with `-ExecutionPolicy Bypass` for this file only.

**"Python packages  missing tzdata"** (usually Windows). Dates in a term
calendar need the IANA time-zone database, which Windows does not ship; the
`tzdata` package supplies it and is in `requirements.txt`. Install it into
the environment the runner uses: `.venv\Scripts\python -m pip install tzdata`
(or rerun the launcher, which installs `requirements.txt`).

**pip fails inside the .venv** (a proxy, an old pip). Run
`.venv/bin/python -m pip install --upgrade pip` then
`.venv/bin/python -m pip install -r requirements.txt` and start again. The
workshop phase also offers the install with a question.

**"Vendored engine: N missing, M changed."** A file under
`vendor/coursecraft_workbench/` differs from the manifest. The runner still
works, but a build's receipt will not match a release. Reinstall the release
ZIP, or if you develop on the repository, run
`python3 scripts/check_vendor_drift.py /path/to/coursecraft_workbench` to see
the difference. Never edit those files in place.

**"… is installed, but N release file(s) are missing and M changed … rerun
with --repair."** A file the release owns differs from the manifest (edited,
deleted, or half-copied). Run the same install command with `--repair`; it
restores only those files from the verified archive and leaves your `.venv`,
remembered answers and logs alone. The receipt records what was repaired.

**"Update check skipped: no GitHub access."** The once-a-day release check
needs `gh auth login` or a `GITHUB_TOKEN`. It is only a notice; nothing else
needs it. `--no-update-check` or `BPK_NO_UPDATE_CHECK=1` turns it off.

**A build stopped at "Read the blueprint" with exit 1.** The reader found
problems in the blueprint and listed them above the card. Each names the
paragraph. Fix them in the document and run again; the answers are
remembered. `docs/AUTHORING_GUIDE.md` has the rules.

**A build stopped at "Verify the package".** The package was written but a
read-back check failed; `verification_report.md` in the build folder names
it. Send the report and the run log (under `logs/`) when asking for help.

**Nothing is drawn, or the colours are wrong.** Run with `--plain`. The same
information is printed as text. `NO_COLOR` in the environment does the same.

## Checking the setup without running anything

```bash
bash blueprint_packager.sh --doctor
```

Prints the Python version, the packages, the vendored engine's integrity, and
the version, and exits 0 when all is well.

## Where things are kept

| Path | What |
|---|---|
| `.venv/` | the private Python environment (git-ignored) |
| `.last_run.json` | remembered answers; delete it to start fresh |
| `.update_check.json` | the release check's one-day cache |
| `logs/` | one log per run |
| `.blueprint-packager-current` (beside the install folder) | which version the launchers start |
