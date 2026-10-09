# Guided installer and runner: the specification

Written 2026-10-08 as the brief for building the Blueprint Packager's guided
installer/runner, so the intent survives the session that produced it. The
owner's ask, verbatim:

> create a vendored package - something that will install dependencies and
> the capabilities on a users machine, in a TUI, with clear and reasonable
> steps and choices, and light context for each step

> and pin it to the repo in releases? something that will auto check for new
> releases on start up?

> feel free to make improvements to functionality, flow, UX/UI etc

## The model to mirror

The owner's Blueprint Wizard runner (`brightspace-blueprint-runner`) sets the
conventions: a double-clickable launcher, a bootstrap that makes the
environment, a pixel-art splash, phased steps with a `· n of N ·` marker and
one line of context each, drag-and-drop path entry with a peek at the file, a
summary card editable by number, live dimmed output with per-step times, a
results card, remembered answers, a log per run, clean Ctrl-C, `--plain`,
`NO_COLOR`, and non-TTY behaviour, a cached non-blocking update check, and a
release bundle with a manifest. Code may be adapted from the runner with a
header naming the file and commit it came from; the runner is the owner's.
No AI attribution anywhere.

## 1. Launchers

| File | Purpose |
|---|---|
| `Blueprint Packager.command` | macOS double-click; execs the `.sh`. |
| `blueprint_packager.sh` | macOS/Linux: find Python 3.11+, create `.venv` if missing, install `requirements.txt` with a permission prompt the first time, run the TUI, pass arguments through. |
| `blueprint_packager.ps1` | Windows equivalent. |
| `install_blueprint_packager.sh`, `.ps1` | Download or clone the latest release into `./blueprint-packager/` and start it. |

The repository is private on GitHub (`timebeing92/brightspace-blueprint-packager`),
so the installer and the update check work through the `gh` CLI when it is
authenticated, or a `GITHUB_TOKEN`, and otherwise explain what to do. A plain
`git clone` by a logged-in user also works.

## 2. The TUI

`scripts/packager_tui.py` with `scripts/ui.py` and `scripts/art.py`. The
splash is drawn from `docs/assets/blueprint-packager-art.txt`, the same grid
the README's SVG uses (`scripts/render_readme_art.py` holds the palette).

Phases, each with a one-line context sentence and a `· n of N ·` marker:

1. **Splash.** Any key skips; auto-skipped when piped, with `--plain`, or
   under `NO_COLOR`.
2. **The workshop.** Python 3.11+, `.venv`, the packages in
   `requirements.txt`, and the vendored engine's integrity: every file in
   `vendor/coursecraft_workbench/MANIFEST.json` present with its hash. This
   is "the capabilities installed". Offer to repair the environment
   (re-install packages) when something is missing. The vendored files are
   never modified by the TUI, only reported. Then the non-blocking update
   check.
3. **The task.** A numbered choice with a sentence each:
   - start a blank blueprint (`bpk.py blank`);
   - read a blueprint and report (`bpk.py read`);
   - build a package from a blueprint (read → build → verify in one go, the
     common path);
   - verify an existing build folder;
   - re-sync a course map after the document changed (`rebase-map`);
   - check for updates / show version.
   Drag-and-drop path entry with a peek: for a blueprint, the title line and
   the number of weeks a quick read finds; for a build folder, the package
   name and hash from the receipt.
4. **The commission.** The inputs the chosen task needs, with defaults
   remembered in `.last_run.json` (git-ignored). For the build path: the
   blueprint; where to write; a build settings file, or "make one for me",
   which asks the few things a settings file needs: package title; course
   label such as "MBA 620 · Marketing"; manifest identifier; template
   (composite-navy or bumk515-classic); an optional term calendar as time
   zone, the first week's start date, and a week count, from which the week
   table is derived as consecutive seven-day weeks, with due-day rules
   defaulting to Sunday for assignments and responses and Friday for initial
   posts, all editable later. It writes `build_settings.json` beside the
   output in the exact shape the builder accepts (`blueprint_packager/build.py`,
   `calendar.py`; the tests' SETTINGS is the minimum). A summary card
   editable by number before running.
5. **The build.** The `bpk.py` stages as subprocesses with live, dimmed
   output and per-stage elapsed time; stop at the first failing stage and
   show its last lines and the log path.
6. **Results.** What was written: the ZIP with its SHA-256 and size, the
   pages-refresh ZIP, the object map, the verification report with its pass
   count; the three facts about importing (import once into an empty course;
   importing again duplicates everything but pages; page text can be
   refreshed through Manage Files with `course_pages_refresh.zip`); offer to
   open the folder. Every run writes a log under `logs/` (git-ignored).
   Ctrl-C cancels cleanly.

## 3. Update check on start-up

`scripts/update_check.py`: query GitHub Releases for the repository through
`gh api` when `gh` is authenticated, else `GITHUB_TOKEN`, else skip with one
dim line; cache the answer for 24 hours in `.update_check.json` (git-ignored);
compare the latest tag with `blueprint_packager.__version__`; when newer,
print a notice with the one command to update. `--no-update-check` and
`BPK_NO_UPDATE_CHECK=1` disable it. Never block the TUI for more than two
seconds. `launcher/install_release.py`: download the latest release asset,
verify its manifest hashes, install beside the current version, switch
atomically, restart; offered from the update notice and from the
check-for-updates task.

## 4. Releases

`scripts/make_release_bundle.py`: build
`dist/brightspace-blueprint-packager-v<version>.zip` from a clean
`git archive` of HEAD plus `release_manifest.json` (version, commit, date,
every file's SHA-256, the vendored Workbench pin from the vendor manifest);
`dist/` git-ignored. `RELEASING.md`: bump `__version__`, changelog, tag
`v<version>`, run the bundle script, `gh release create v<version> dist/<zip>
--notes-file …`; how the update check and installer find the release.

## 5. Docs and records

README: a section "Guided install and run" near the top (download and start
on macOS, Windows, Linux; what the phases do; the update check; `--plain`),
and Repository map rows for the new files. `INSTALL_AND_TROUBLESHOOT.md` in
the runner's manner. `CHANGELOG.md` entry; `__version__` to 0.2.0;
`.gitignore` additions.

## 6. Tests

Non-interactive, in `tests/`: the workshop's checks (Python version parse,
manifest integrity on the real vendor directory, a tampered copy detected in
a temp dir); settings generation (the written file loads and the builder
accepts it on the synthetic fixture); the week-table derivation; update-check
parsing against a mocked API response and the cache; release-bundle manifest
completeness on a temp archive; a scripted end-to-end TUI run of the build
task on the synthetic blueprint with answers fed through stdin in `--plain`
mode.

## Addendum: latitude to improve

The runner's phases are the floor, not the ceiling. Improvements the builder
may take, each noted in the report: a "first time here?" path that goes
workshop → blank blueprint → opens the Word file; a dry run that reads and
reports without building; remembering the last blueprint and offering "build
it again"; the verification checks shown as a live checklist rather than raw
output; a clear next-step card after each task ("now fill in Week 1's rows",
"now import the ZIP once into an empty course"); a build settings file
accepted by drag-and-drop; a `--yes` flag that accepts all remembered
defaults for repeat builds; sensible colour and spacing. Every improvement in
the same calm register as the rest of the tool: no exclamation marks, no
jokes in the diagnostics; the whimsy belongs to the splash.

## After the build lands

The owner publishes the first release (`v0.2.0`) with the bundle as its
asset, so the installer and the update check have something to find. Later
releases follow `RELEASING.md`.
