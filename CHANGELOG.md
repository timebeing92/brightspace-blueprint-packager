# Changelog

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
