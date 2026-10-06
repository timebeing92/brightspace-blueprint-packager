# Changelog

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
