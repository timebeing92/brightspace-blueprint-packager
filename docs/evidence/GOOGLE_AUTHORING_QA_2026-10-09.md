# Google authoring round-trip QA — 2026-10-09

## Scope and method

Live testing ran in Google Drive and Google Docs through the Drive connector,
in a working folder. Three clearly labelled synthetic native Google Docs were
created there. The older review document was preserved. No sharing permissions were changed and no Brightspace tenant was
accessed.

Each DOCX was imported with the Drive connector's `native_google_docs` conversion.
A full file-backed trusted read identified tab `t.0`, its revision, structure and
control inventory before mutation. No protected controls were detected;
authoritative dropdown metadata was unavailable. Revision-guarded Docs API edits
set `documentStyle.documentFormat.documentMode` to `PAGELESS`, and a subsequent
read confirmed that value. Native DOCX export was then downloaded and read by the
Packager. Signed download URLs are not retained in this report.

This is live Google conversion, document mode and native API editing evidence.
It is **not** a Google Docs canvas/UI inspection or a manual mouse-and-keyboard
editing test. Exported DOCX pages were rendered with the bundled LibreOffice
renderer and inspected separately.

## Retained Google copies

| Copy | Native document | Final state |
| --- | --- | --- |
| Eight-week minimal blank | SYNTHETIC QA — Blueprint blank — pageless round trip | Pageless; unresolved authoring fields retained |
| Three-week populated stress case | SYNTHETIC QA — Multiple activities and native editing | Pageless; native content/style edits retained; draft |
| Completed synthetic course | SYNTHETIC QA — Completed blueprint — ready round trip | Pageless; readiness `ready`, no findings |

The copies are retained in Google Drive, unshared; their links are not recorded here.

All test artifacts below are under
`/tmp/bpk-implementation-20261009/google/` on the test machine. These scratch
artifacts are not checked into the repository. The Google copies and this report
provide the retained review references.

## Results

| Export | Activities per week (assignments, discussions) | Grade points / rubrics | Pending content / videos | Model result |
| --- | --- | --- | --- | --- |
| `minimal-pageless.docx` | Eight weeks of (1, 1) | 0 / 0 | 45 content placeholders; no videos | Exact normalized equality with generated blank; draft |
| `populated-pageless.docx` | (2, 1), (2, 3), (0, 1) | 65 / 2 | 23 content placeholders; one pending video | Exact normalized equality with populated source; draft |
| `populated-edited.docx` | (2, 2), (2, 3), (0, 1) | 65 / 2 | 22 content placeholders; one pending and one completed video | Exact equality with the independently enumerated intended edits; draft |
| `ready-pageless.docx` | (2, 2), (2, 3), (0, 1) | 65 / 2 | No content placeholders; two completed videos | Exact normalized equality with completed source; ready |

Every export had zero reader errors, zero join errors, and complete source
paragraph accounting. The blank retained all 52 authoring-guidance dispositions;
each three-week variant retained 24. None became learner content blocks.
Placeholder and scaffold findings survived Google conversion: the first three
exports correctly remained drafts. The completed source and its export both had
an empty readiness findings list.

The semantic comparison excluded source filename/hash, paragraph provenance
`src`, source-accounting/diagnostic records, native list IDs, and quickstart
`title_lines[].style` metadata. It retained text, semantic heading levels, list
kind/level/order, run bold/italic/href, activity identity and relationships,
points, rubric grids, checklist instructions, panels, and video fields. Source
accounting, diagnostics and readiness were checked separately. The actual
baseline differences were source identity plus Google replacing quickstart
`List Bullet` style names with an empty style name; native list semantics were
preserved.

Evidence: `compare_models.py`, `semantic-comparison.json`,
`ready-comparison.json`, `qa-summary.json`, the `*.model.json` files, and trusted
read directories `minimal-import-read`, `populated-import-read`,
`populated-text-edit-read`, `populated-final-read`, and `ready-import-read`.
Pageless readbacks are in `mode-readbacks.json`,
`populated-final-read/document-result.json`, and `ready-mode-readback.json`.

### Native Google edits exercised

The populated Google Doc was changed using Docs batch-update requests against
fresh revisions and observed table-cell ranges:

1. Renamed the Week 1 heading and its page-heading value.
2. Inserted a content heading and applied native Heading 2.
3. Applied bold, italic, and an HTTPS hyperlink to the same body-text run.
4. Replaced an objective placeholder with two objective paragraphs and applied
   native bullets. Both exported as semantic unordered list items.
5. Appended a complete ungraded discussion block in the Week 1 discussion cell,
   with an exact forum and body. This increased that week to two discussions
   while keeping the nine graded activities and 65-point grading plan unchanged.
6. Added `[video: Synthetic clip | https://www.youtube.com/watch?v=aqz-KE-bpKQ]`
   while retaining the existing `[video placeholder: Week 1 introduction]`.
   Both exported as their distinct expected video model blocks.

The completed synthetic source was a separate local copy of this edited export.
Known placeholder paragraphs received explicit synthetic text; activity titles,
their grade-plan/gradebook/rubric references, week topics and criterion names
were completed consistently. The pending video received a supported YouTube
URL. All 67 changed paragraphs are listed in
`synthetic-completion-ledger.json`; `complete_synthetic.py` records the exact
mapping. No real course wording was used or changed.

## Render and layout findings

Full-page PNG inspection covered all 12 pages of `minimal-pageless-render`, all
11 pages of `populated-edited-render`, and all 11 pages of
`ready-pageless-render`. No clipped or overlapping text was found. Normal black
writing areas, native bullets, the existing palette, panels and rubric columns
remained readable. Grade-plan and rubric header-row flags survived export;
repeated rubric headers were visible across pages 9–11 in the stress cases.
Long rubric rows continued across pages without losing text.

Google export changes paragraph spacing and pagination. In the blank export,
the Course Introduction starts on page 2 and continues on page 3; Extraction
Notes occupies a sparse final page. The stress/ready exports similarly split
the introductory resource block across pages 2–3. In the ready case the Week 2
discussion label and guidance end page 6, with the activity starting on page 7.
These are visible print-layout limitations after Google export, with no semantic
loss. Pageless mode is confirmed by API readback; these exported paginated
renders do not establish the appearance of the native pageless canvas.

The deliberately appended native activity exposed a stale guidance count:
“1 discussion block(s)” remained while the cell contained two. The retained
Google copies and exports preserve this tested wording. The final generator
and checked-in eight-week example now use count-free guidance for every activity
row, including initially empty ones: “Add or remove complete Assignment:
blocks; update the grading plan and rubric references” (and the corresponding
Discussion form). This remains true when activities are added or removed.

This guidance-only correction was checked locally without repeating Google
cycles. The final example retains the same course identity and 12-page layout;
all eight affected week pages were visually inspected. Unaffected pages were
pixel-identical to the earlier reviewed render, and parsed course content was
identical after excluding source identity and its guidance-accounting text.
The 15 focused blank-authoring tests passed. Final local render evidence:
`/tmp/bpk-implementation-20261009/blank-template/count-free-final-render/`.

## Local package verification

A compact durable record is checked into
[GOOGLE_PACKAGE_RESULTS_2026-10-09.json](GOOGLE_PACKAGE_RESULTS_2026-10-09.json).

The root implementation run fed all three draft exports through the real local
pipeline with explicit draft-preview authorization. `package-results.json`
records zero failed checks: the blank had 13 passed / 3 not applicable, and both
populated drafts had 14 passed / 1 not applicable. The edited draft also passed
the actual guided runner and was reported as a draft preview.

The completed `ready-pageless.docx` passed the actual guided runner with
**14 passed / 1 not applicable**, zero model errors, a ready receipt, and two
video destinations checked. The runner read back the built package through the
independent Workbench/Blueprint Wizard readers, checked nine grade items
totalling 65 points, two rubrics, ten activities, three checklists, and five HTML
pages. Evidence: `ready-pageless-runner.log` and
`ready-pageless-runner/build/verification_report.md`.

Ready ZIP SHA-256:
`4016be0de0d8583d337161ee9f04c338733463d0368a5bfa0639da6dfaccef27`.

These are local package and read-back checks. No Brightspace import, live
tenant behavior, Google canvas inspection, screen-reader test, or video
playback test was performed. The synthetic repeated rubric prose tests
structure and long-row layout; it is not a teaching rubric recommendation.

## Export identity

| File | SHA-256 |
| --- | --- |
| `minimal-pageless.docx` | `48f1d98dc1b5451d98bc7feebc71b6085eecff5d6903c034bc190e052096362c` |
| `populated-pageless.docx` | `c1db086a9041a95cb496046a60b9527fa15d70f8e0c70228a2a53df6f19f103a` |
| `populated-edited.docx` | `2b7afcf14d7e59e4d3a94d1300504350f01f30ee115fdbf72dcdae55fd289096` |
| `ready-source.docx` | `95eba7bd54921d053ca77b77003b5542fb365ac3722b255bbee73f61900d6f9f` |
| `ready-pageless.docx` | `46215befd531889d724b88f18e76398d3f05b759d1286358ce7bd6874c1818be` |
