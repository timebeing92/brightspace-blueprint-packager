# Changelog

## 0.3.1 — not yet released

The first public-repository release: a license, release access without an
account, and a producer identity that cannot borrow another repository's
commit. No change to what the tool reads or builds; the vendored Workbench
stays at `1f48e07`.

- License: GNU Affero General Public License v3.0 or later (`LICENSE`), with
  commercial terms available by agreement (`COMMERCIAL.md`), the pairing the
  sibling public bundles use; `LICENSE_POSTURE.md` records the selection. The
  vendored Workbench files are distributed here under the same terms by their
  author. v0.3.0's ZIP predates the license files; this release's carries them.
- Anonymous release access: the runner's update check and
  `launcher/install_release.py --latest` read the public release and download
  its asset without credentials; a signed-in `gh` or a `GITHUB_TOKEN` is used
  when present and only raises the rate limit (`scripts/update_check.py`,
  `launcher/install_release.py`). A rate-limited answer (HTTP 403 or 429) is
  reported as unavailable with the one line that explains it. The one-command
  installers fetch the latest release anonymously with curl or PowerShell when
  `gh` is not signed in, check the download against its published SHA-256,
  and clone `main` only when no release can be reached;
  `BPK_INSTALL_NO_START=1` installs without starting the runner.
- Producer identity: `blueprint_packager/identity.py` reads the commit, tag
  and verified-tag flag from `release_manifest.json` when running from an
  installed release (`identity_state: release`); from a checkout it asks git
  only when the repository it finds is this tool's own (`git`); a copy inside
  another repository (a release unpacked in a course build) no longer reports
  that repository's commit and is `unknown`. The smoke test checks that a
  built package's run identity names the release commit.

## 0.3.0 — 2026-10-13

The authoring and verification candidate of 2026-10-09, the Blueprint Wizard
compatibility work of 2026-10-13 and the release-readiness work below, released
together. The vendored Workbench is pinned at `1f48e07`, the accepted
heading-ownership merge that Bundle v1.4.0 was cut from. Local and synthetic
evidence only: no tenant import or re-export round has been run for 0.3.0, so
the shapes new since 0.2.2 are supported locally and are not tenant-verified
(see "Evidence" below).

### Updating from 0.2.2

- Install beside the old version as usual (`python3 launcher/install_release.py
  --latest`, or the runner's offer when it shows the notice). Remembered
  answers are carried over; the old folder stays and forwards to the new one.
- Build from the blueprint again. The guided runner always re-reads the
  document; on the command line, run `bpk.py read` on each DOCX before
  `build`. A course model cached by 0.2.2 has no source-accounting ledger, and
  `build` refuses it with "Re-read the DOCX". Re-reading never changes the
  source file.
- Tested as it happens: `tests/test_release_readiness.py` archives the v0.2.2
  tag with the builder, installs it, runs it once so it remembers answers,
  installs this version beside it, runs this version from the carried answers,
  and shows the old cached model refused and the re-read model building.

### Release readiness

- Installer: installing a version that is already in place checks every file
  the manifest lists against the installed folder instead of trusting the old
  receipt alone. A missing or changed release file is refused by name;
  `--repair` restores it from the verified archive. `.venv`, remembered
  answers, the update-check cache, logs and the receipt are never touched
  (`launcher/install_release.py`).
- Release builder: `--ref` names the commit to archive and `--tag` the release
  tag, which must exist, point at that commit and be named `v<version>` for
  that commit's tree. The version and the vendor pin in the manifest are read
  from the archived commit, never from the working tree. A tagged build
  refuses a dirty worktree; `--allow-dirty` only ever builds an unreleased ZIP
  of the committed tree. The manifest records `tag` (null when unreleased) and
  a `build` block with the ref, whether the tag was verified and whether the
  worktree was dirty (`scripts/make_release_bundle.py`).
- CI (`.github/workflows/ci.yml`): the suite on Linux at Python 3.11, 3.12,
  3.13 and 3.14, on Windows at 3.11 and 3.14, and on macOS at 3.11; and on all
  three platforms the release ZIP of the commit built, installed, reinstalled,
  tampered with and repaired, then started through the real launchers
  (`blueprint_packager.sh`, `blueprint_packager.ps1`, `Blueprint Packager.bat`)
  with the venv created, the packages installed and the doctor run. The 3.11
  floor declared in `pyproject.toml` is now exercised; before this release the
  suite had only been run on 3.14.
- Published-asset smoke test (`scripts/smoke_test_release.py`): downloads the
  release's ZIP and sidecar, requires exactly one ZIP asset, checks the hash
  and the manifest against the tag, installs with the installer and reinstalls
  with the shipped one, starts the launcher, writes and reads a blank, reads,
  builds and verifies a ready synthetic course, runs the Wizard conversion
  cycle from the installed copy, runs the shipped suite there, and writes a
  report. The 0.3.0 run is recorded under `docs/evidence/`.
- The runner's update card says to build from the blueprint again after
  updating, and its output no longer stops on a glyph the console or pipe
  cannot encode (a Windows pipe in cp1252 prints "?" instead).
- Found by the matrix on its first run: Windows has no time-zone database of
  its own, so every build with a term calendar failed there with "No time
  zone found with key America/New_York". `tzdata` is now a dependency
  (`requirements.txt`, `pyproject.toml`), the launcher installs it, and the
  doctor reports it missing when zone data cannot be loaded. Also found: the
  0.2.2 runner dropped backslashes from a path given on the command line on
  Windows (treating it as dragged-in text); 0.3.0's path handling already
  corrected that, and the update test gives the old runner forward slashes.
- The release builder archives bytes as stored (`core.autocrlf=false`), and a
  `.gitattributes` keeps every checkout at LF, so the vendored and release
  manifests' hashes hold on Windows too; verbatim records keep their bytes.

### Evidence

Local synthetic tests on the CI matrix above and the smoke test of the
published asset. The historical L4 tenant evidence (Import receipts 10 to 13)
applies to the 0.2.x-era packages and shapes it names. The shapes new since
0.2.2 (multiple activities per week, video markers, readiness gates, Wizard
conversion, the bracket vocabulary) have not been through a tenant import and
re-export; a new receipt is needed before claiming more. The retained
conversion backlog is `docs/CONVERSION_BACKLOG_2026-10-13.md`.

### After publication

- Published 2026-10-14T01:21Z (the evening of 2026-10-13 locally) as
  [v0.3.0](https://github.com/timebeing92/brightspace-blueprint-packager/releases/tag/v0.3.0):
  `brightspace-blueprint-packager-v0.3.0.zip`, 780,217 bytes, SHA-256
  `c1f94ac611f202ddaa8dadae8f81948ac4da59188a7565371c06110a19d8161b`, built
  from the verified tag at `824fc1f`. The smoke test of the published asset
  passed from the download (`docs/evidence/RELEASE_SMOKE_v0.3.0.md`): hash,
  manifest, install, reinstall, launcher and doctor, blank, ready course built
  and verified, Wizard cycle, shipped suite 205 passed and 1 skipped.
- The repository is public since 2026-10-13. Release assets download without
  an account, and the installers say so. The runner's update check and
  `launcher/install_release.py --latest` still go through `gh` or a
  `GITHUB_TOKEN` and report "no GitHub access" without one; reading the
  public release anonymously is the next change. The evidence note of the
  Google authoring round no longer links the owner's QA documents.
- Found by the smoke test's own second run: its default work folder sat
  inside this checkout, where the shipped update test saw this repository's
  tags through the install folder and ran against a `git archive` of the
  wrong tree. The default is now a temporary folder outside any checkout, the
  report records no local path, and the update test skips unless the
  repository it finds is its own, so a release unpacked inside another
  repository (a course build, for example) no longer runs it.

### Blueprint Wizard compatibility (2026-10-13)

Applied on top of the candidate; the vendored Workbench was then re-pinned at
the accepted producer, `1f48e07`.

- `from-wizard` no longer crashes on an extracted table inside a week cell
  (`_Cell.add_table` takes no width); only the rows the extraction counted as
  header rows are shaded, repeated and bold, so a table with `header_rows: 0`
  gets no invented header.
- Extracted panel labels are normalised to the shared bracket vocabulary
  (`vocabulary.bracket_keyword` / `bracket_opener`): the callout family is
  `[callout attrs]`, `Timeline` is `[timeline]`, every other label is
  `[box attrs: Label]`; attributed `Project callout` and `Panel` labels convert
  instead of being refused. `[box: Label]` is documented as accepted with the
  label ignored.
- A heading the extraction left inside its panel is written once: the adapter
  honours `heading_owner: "panel"` on structure segments and inspects resources
  sections (`panel_owns_label`, mirroring the Workbench helper), with a
  `heading_owned_by_panel` ledger entry.
- Docs: the design note and renderer comment no longer say editor fields are
  plain by default (`fragment_styles` has defaulted to `"template"` since
  2026-10-08); the authoring guide explains the box label and heading
  ownership.

### Authoring and verification candidate (2026-10-09)

- Follow-up SME/ID usability revision: ordinary writing prompts, readable author
  notes, a first-page replacement example and handoff sequence, and a separate
  authoring reference with genuinely multiline copyable examples. Existing
  bracket forms remain supported. Document-only fields, optional areas and the
  limits of technical readiness are stated explicitly. Designers and SMEs can
  defer optional styling and connections for manual completion in Brightspace;
  the guide explains how to remove unused references before packaging.
  Runner counts exclude the reference examples. Points warnings and capability
  documentation now describe the existing build-time determination gate accurately.

- Source-accounting ledgers for direct reads; unknown, unplaced, or unsupported
  authored content is blocking. Native images and authored module/link bodies
  receive explicit diagnostics instead of disappearing. Malformed documents
  produce useful errors. Current input contracts are checked before building;
  re-read existing DOCX files to replace older cached models.
- Verification checks actual Wizard QA findings, represents unavailable evidence
  accurately, compares internal-link display text and destinations, retains
  checklist link targets, and records the vendored Workbench pin separately from
  the Packager checkout commit.
- Minimal blank and optional worked-example forms; zero or multiple assignments
  and discussions per week; common counts and weekly overrides; clearer overview
  and learning-objective writing areas. Guidance and pending content have explicit
  markers, normal writing typography, repeated grading/rubric headers, and revised
  table continuation behaviour. Existing blank files are protected and explicit
  overwrite creates a backup.
- Draft readiness reports and explicit preview builds. Normal builds require
  completed fields or supported recorded retention choices. Read also writes
  relationship reports. Exact structural activity renames can be previewed and
  applied to a new copy with an authorizer, reason, and change ledger.
- Video brackets and placeholders, compatible with the existing long form.
  Supported YouTube/Vimeo URLs become responsive players; unsupported valid
  destinations require an explicit link fallback. Missing or malformed video
  URLs do not become empty iframes. Local tests do not prove tenant playback.
- Explicit `from-wizard` conversion of an immutable extraction bundle into native
  authoring DOCX. Source contracts, hashes, dispositions, and diagnostics travel
  in a sidecar; rubric-free bundles require explicit inventory evidence when
  Wizard omits their rubric contract. Exclusive publication protects concurrent
  output files. A supported synthetic course completes the full
  package → Wizard → authoring → package → Wizard cycle; unsupported semantics
  stop conversion. Direct Wizard review-DOCX interoperability is not claimed.
- Guided-runner title/count improvements, reviewed editable week boundaries,
  clearer draft/ready choices, and revised path handling. Native Windows UI
  execution remains a separate evidence requirement.
- Updated authoring guide, roadmap, capability records, and test instructions.

## 0.2.2 — 2026-10-09

- The blank blueprint's panels and links are coloured the way Blueprint Wizard colours them in an export blueprint, so the two documents look alike: dropdowns lavender, callouts blue, the gold callout in the composite's warm colours, internal links underlined in link blue; the key at the top shows each in its colour. Week 1's overview now carries all four examples: a dropdown, a blue callout, a gold callout, and a link. The opening guide is rewritten in plain, specific language: what the document is, what to do in order, how to read what is already on the page, four rules that save a round of fixes, and the key.

## 0.2.1 — 2026-10-09

- The blank blueprint is presented for the person who will write in it: a short guide and a key at the top (kept as front-matter text, never built), worked examples of a dropdown, a gold callout, and an internal link inside Week 1's overview, breathing room inside every table, shaded label rows that never split from their content, prompts in grey italics and structure keywords in navy, Lato at 11 points with 1.15 line spacing, one-inch margins. It still reads back with zero errors and builds as it stands. No change to how a blueprint is read or built.

## 0.2.0 — 2026-10-08, night

- The guided runner: `Blueprint Packager.command` (macOS), `Blueprint Packager.bat` (Windows), `blueprint_packager.sh` and `.ps1`, which find Python 3.11+, make a private `.venv` with a question first, and start `scripts/packager_tui.py`. Phases with a line of context each: splash (the wizard delivers the package into a monitor, drawn from the README's grid), the workshop (Python, packages, the vendored engine's hashes, a quiet update check), the task menu (first time here, build, dry run, verify, re-sync, updates), the commission (drag-and-drop paths with a look inside, settings made from a few questions or taken from a file, answers remembered, a card editable by number), the build (live stages, verification as a checklist, the first failure stops with its log), and the results (ZIP with hash, pages-refresh ZIP, object map, verification count, and what to do next). `--yes` repeats the last build without prompts; `--plain` for text only; `--doctor`.
- One-command installers for macOS/Linux and Windows that fetch the latest release through `gh` (the repository is private) or clone `main`, write a pointer, and start the runner.
- `scripts/update_check.py`: a once-a-day release check through `gh` or a token, cached, never longer than two seconds, with the one command to update; `launcher/install_release.py` installs a verified release beside the current one and switches the pointer atomically.
- `scripts/make_release_bundle.py` and `RELEASING.md`: a release ZIP from a clean `git archive` with `release_manifest.json` (version, commit, date, every file's hash, the vendored Workbench pin) and a `.sha256` sidecar.
- `INSTALL_AND_TROUBLESHOOT.md`. Tests for the workshop checks, settings generation, the week table, the update check, the release manifest, the installer, and a scripted end-to-end run of the runner.

## 0.1.1 — 2026-10-08, evening

- README rewritten for readers who arrive without context: who it is for, the idea in one picture, quick start, how it works, what a build produces, importing and updating, writing a blueprint, styling, evidence and provenance, repository map. A pixel-art illustration (`docs/assets/blueprint-packager.svg`, drawn from a text grid by `scripts/render_readme_art.py`) in the manner of the Blueprint Wizard runner's splash.
- Vendored Workbench re-pinned from `9d3a620` to `2c967f9`, the main after PR #5 and the bundle refresh: the readers the verify step runs now carry the merged wizard (one-to-one headings, model /5, bracket panels and links, page chrome). The `/4` schema is vendored beside `/5`. Tests read the pin from the manifest instead of naming a commit.

## 0.1.0 — 2026-10-08 — own repository

- Split from the MBA 620 course repository's `tools/blueprint-packager` with its history (`brightspace-blueprint-packager`).
- The Workbench scripts and schemas the tool imports or runs are vendored at `9d3a620` with a manifest and `scripts/check_vendor_drift.py`; one helper, `blueprint_packager/workbench.py`, resolves which copy a run uses (explicit path, vendored mirror, or the fork layout) and every receipt and verification report records it.
- The records packet travels in `docs/records/`; the sandbox receipts in `docs/IMPORT_RECEIPTS.md`.
- `requirements.txt`, `pyproject.toml`, `.gitignore`; version 0.1.0. 41 tests.

## Unreleased — 2026-10-08

Changes on the owner's second round of answers (response sheet Part 3 and the Page Kit items).

- Callout tones: `[callout tone=gold]`, `[callout tone=grey]`, or `[callout color=#hex]` as bracket attributes; the composite template defines the palette (`callout_tones`) and a muted orange-gold tone for "keep this in mind" snippets. Unknown tones are reported and fall back.
- Normalizer `wrap` operation: bracket lines written around a range of kept paragraphs, so a course map can put authored text in a callout without touching the words. The `bullet` operation never double-bullets a paragraph that is already a list item.
- Editor fields carry the composite template's modest inline style set by default (`fragment_styles: "template"`); `plain` remains available. The composite's dropdown marker is an arrow in line with the heading; the template gained a skip link, print rules, and a token set (`tokens`, plus `theme.pagekit.json` in Page Kit's theme shape); video iframes load lazily.
- Early page checks in the reader, with paragraph ids: `HEADING_LEVEL_JUMP`, `TABLE_HEADER_MISSING` (one-cell box tables exempt), `LINK_TEXT_BARE`. Warnings, never blocking.
- The object map lists every external link by page and activity (`external_links`).
- Every built page's source opens with a provenance comment: tool version, package title, blueprint file and hash, template (13c, owner's go).
- A description no longer starts with a heading that repeats the activity's title; the title is the object's own and the wizard writes it back as the activity line, so both directions agree (item 31, "it should split"). The verifier counts the title as present.
- Composite template pass 2 on the owner's notes: course label above the title (`package.course_label`), air under the header rule, root 18.5px with line-height 1.6, dropdown summaries tinted and a touch larger with the arrow marker in line.
- Composite template pass 3: dropdowns as white cards with a soft shadow and no left bar, focus ring for keyboard focus only, back-to-top not bold (also in the classic template). The pages-only refresh is confirmed in the sandbox.
- Tests: 39.

- `rebase-map`: a paragraph that is new in a later export and sits between two mapped stretches joins the content stretch that ends just before it (same cell or body, never across a mapped line), and the report lists it under "Placed by inference, confirm" with `placed_by_inference` in the JSON. Only `content`, `intro`, `notes`, and `retired` lists grow. A new paragraph with no mapped content neighbour in its container still stops the run. Owner's rule (response sheet item 20). Tests: 35.

## Unreleased — 2026-10-08

- `bpk.py blank`: a blank blueprint in the current convention (frame at Heading 1, content from Heading 2), with front matter, points table, a welcome page, a module row before Week 1, every week's six rows with the lines each needs, a `Checklist:` row pre-filled with `Items: From this week's activities` (owner's decision, item 19), two standard rubrics, and notes. Reads back with zero errors and builds a package as it stands. Two tests.

## Unreleased — 2026-10-07

Changes made on the owner's response-sheet answers.

- Heading convention is one to one. The frame is Heading 1, the page heading line is the page's h1, and content Heading N is hN from Heading 2 down. The reader detects a legacy frame at Heading 2, reads it with an offset, and reports `FRAME_LEVEL_LEGACY`. The normalizer applies the frame shift when writing, so course maps keep speaking in the source document's terms. Template heading maps are identity maps; the classic template styles h5 and h6.
- Fidelity report and normalizer result record the heading convention used.
- Tests: 28 (three new: the shift from an older source, the legacy offset, one-to-one rendering of the same page from both frames).

Changes made on the first sandbox round (import, inspection, and re-export of the MBA 620 package).

- Editor fields (assignment and discussion descriptions) are plain semantic HTML with no inline styles by default; the tenant's stylesheet applies. `fragment_styles: "template"` in the build settings restores a template's inline styles. The object map records the rendering mode.
- A heading's text after a soft line break is wrapped in `<small>` so an author's two-line step title reads as title and subtitle.
- Normalizer `bullet` operation: make paragraphs list items with the list definition of another paragraph (`{"ids": [...], "like": "p00450"}`). Structure only; words unchanged; recorded in the ledger.
- Verifier: compares date stamps as instants (a re-export drops `.000Z`); compares grade item names with quotes straightened and reports the straightening as a note (Brightspace does this on import); carries notes into the report. The companion renderer tolerates a rubric weight it cannot parse.
- New page template `composite-navy`, now the default: BUMK 515's skeleton, MBA 630's palette (`#174b5c` brand, `#103945` headings, all text pairs above 4.5:1), BUMG 660's heading weight, no hero cards or shadows. `bumk515-classic` stays selectable.
- Evidence: the tool's first L4, Receipt 10 in the import test log.
- Tests: 31.

## Unreleased — 2026-10-06, afternoon

Changes made while applying the owner's first decisions to MBA 620.

- `rebase-map`: carry a course map from one export of a blueprint to a later one, with a change report. A paragraph added outside every mapped range is never placed silently.
- Titles: a directive value can copy a paragraph that stays in place, so an activity is named by its own heading. Rubric `Used by` lines can follow the same heading.
- Points: the activity body is read first and the points table is the fallback. A disagreement must be decided in the map and is recorded. The reader reports a remaining disagreement as a warning, and the grade item follows the activity.
- Gradebook names: `grade_item_names` in the build settings, `activity_title` by default, `points_table` as the alternative.
- Authorized additions: the one operation that adds words. Each needs an authorizer and a source, and the fidelity proof counts its words apart from authored text.
- Verification: `--workbench-scripts` and `--label` read the package with another Workbench checkout as a recorded second opinion. Reader processes no longer write bytecode. Reports name the checkout, commit, and reader file hashes.
- Sixteen tests on synthetic fixtures.

Later the same day, from the owner's review notes:

- Authorized edits: the course map can drop paragraphs or replace one exact stretch of text, each entry naming its authorizer and reason. A rubric can be cloned with named cell edits. The fidelity proof gained a check that authored wording differs only by these entries.
- Titles inherit their week when the heading lacks it.
- Checklists can be built from a week's activities (`Items: From this week's activities`), worded by patterns in the build settings, with listed items added as extras.
- Dates: a term calendar and due-day rules in the build settings, resolved through the time zone database. Due dates on assignment folders and their content links, end dates on checklist items, and a due date on a carried quiz. A warning when an activity's own text names a different day.
- Link cleanup: named query parameters dropped from addresses in the package only, with a before-and-after list in the object map.
- Points: a build stops when an activity and its points table row disagree and no determination is recorded.
- Verification: a check that every planned date is in the package, checklist read-back against what the build planned, and the Workbench page compiler's page gate run on the package's pages (one h1, alt text, iframe titles, no scripts).
- Twenty-two tests on synthetic fixtures.

Evening, from the owner's notes on the wizard losses:

- Bracket forms for hand authoring: `[dropdown: Title]` … `[/dropdown]`, `[callout]`, `[timeline]`, and `[link to page|assignment|discussion|quiz|checklist: Title | words]`. Provisional.
- A module row before Week 1 holds its own pages, links, and activities; placement follows position. MBA 620 regrouped and rebuilt to the identical package.
- Activity keys are claimed before any description is rendered, so a description can link to an activity that comes later.
- An authoring guide and a promotion manifest.
- Twenty-five tests.

## 0.1.0.dev0 — 2026-10-06

First working version, built against the MBA 620 Fall B 2026 blueprint.

- Word ingest with stable paragraph ids, suggestion views, list formats, and links.
- Structure-only normalizer driven by a course map, with a per-paragraph ledger.
- Fidelity proof computed from the written file.
- Structure vocabulary 0.1 with section-scoped keywords.
- Deterministic reader, join resolution from both sides, structured diagnostics.
- Page and editor-field rendering in the BUMK 515 template.
- Package builder on the Workbench component and rubric libraries, with six local extensions.
- Pre-import verification by conformance gate, activity and structure extractors, and a Blueprint Wizard read-back.
- Ten tests on synthetic fixtures.
