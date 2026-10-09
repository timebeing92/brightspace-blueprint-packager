# Install and troubleshoot

How the Blueprint Packager gets onto a machine, what the launcher does on
first run, and what to do when something does not start. The guided runner
itself is described in the README under "Guided install and run".

## Ways to install

| Way | When | What you get |
|---|---|---|
| `bash install_blueprint_packager.sh` (macOS, Linux) or the `.ps1` (Windows) | you have GitHub access to the repository: `gh auth login`, or git with saved credentials | the latest release in `./blueprint-packager/<version folder>/`, a pointer file beside it, and the runner started |
| A release ZIP from GitHub Releases, unzipped anywhere | you were given the ZIP | one folder, `brightspace-blueprint-packager-v<version>/`, with the launchers at its top |
| `git clone` of the repository | you develop on it or want `main` | the working tree; `bash blueprint_packager.sh` starts the runner from it |

The repository is private. Without access the installer explains what to do;
a release ZIP handed to you works without any access at all. Everything the
packager needs is inside the folder, including the engine files it builds
with (see the README, "The vendored engine").

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
