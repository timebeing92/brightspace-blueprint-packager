# Changelog

## Unreleased — 2026-10-08

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
