# Blueprint implementation log

Current status: implementation and follow-up SME/ID authoring revision complete;
**184 tests pass**. This is an uncommitted, unreleased candidate based on v0.2.2.
The latest document revision has local validation; the earlier Google evidence
retains its original artifact scope. See the latest entry below.

## 2026-10-09 — Start and baseline

- Operator approved the implementation plan and requested a repository log;
  delegation is explicitly authorized.
- Starting checkout clean at `ecee5cd` (v0.2.2). No pre-existing edits to preserve.
- Review baseline: 54 tests passed using existing pytest from another local
  environment; the Packager virtual environment lacks pytest. The AGENTS test
  path still refers to the former nested checkout. These will be corrected.
- Review vendor check: all 33 files match pin `2c967f9` and the local Workbench.
- Prior review evidence is retained at `/tmp/bpk-review-20261009`; it includes
  synthetic failure probes and the live UNE Google pageless round trip.
- Parallel bounded work assigned for verification, blank authoring, and the Wizard
  conversion. Primary agent owns shared integration and this log.
- No implementation evidence yet; no new tenant/import or release claim.

## Decisions in progress

- Use explicit text markers for authoring guidance and pending entry areas so
  their roles survive Google Docs conversion. Preserve all other authored text.
- Existing models already contain activity lists, and checklist patterns already
  distinguish multiple activities; extend and test those paths.
- Extend existing video block rendering with a copyable bracket syntax rather
  than introducing an unrelated media subsystem.

## 2026-10-09 — First integrated hardening batch

- Installed the declared development dependencies in the repository `.venv`;
  corrected the AGENTS test command to the standalone `tests` path.
- Reader now writes a per-paragraph source-accounting ledger. Unknown sections,
  extra table rows/cells, and unassigned content block builds. A missing overview
  produces diagnostics instead of an AttributeError. Explicit authoring guidance
  is classified and excluded; ordinary parenthetical prose stays content.
- Preserved the legacy `Course Content:` divider explicitly after baseline tests
  revealed that the normalizer still writes it. This is a compatibility rule,
  not a generic exemption for unrecognized text.
- Verifier fixes cover top-level Wizard QA, exact generated-chrome exclusions,
  missing reader/gate evidence, independent link label/target checks, and actual
  Workbench pin provenance. Check statuses distinguish not-run and inapplicable.
- Build inputs validate their owned envelope; extracted contracts are rejected.
  Draft fields require explicit preview mode, and readiness accompanies outputs.
- Internal checklist link targets are preserved. Video brackets parse into the
  existing media model; player URLs and visible placeholders are distinct.
- Integrated focused run: **82 passed in 18.41s** (pipeline, authoring boundaries,
  verification hardening). Additional template, adapter, runner and media checks
  remain in progress. This is local evidence only.
- Template decisions: minimal scaffold by default, optional sample rubrics/panels;
  no silent overwrites; configurable per-week activity counts. Arial replaces
  unavailable Lato for reliable Word/Google/renderer font fallback; colours stay.
- New portability finding: inherited Word List Bullet numbering was not seen by
  ingestion. Explicit native numbering in generated areas and inherited-style
  ingestion are being checked.
- Relationship reports and a preview-first, explicitly authorized rename command
  are being integrated. Narrative text remains outside structural rename scope.

## 2026-10-09 — Authoring integration and course corrections

- Generator accepts common assignment/discussion counts and per-week overrides,
  including zero. Minimal scaffold is the default; worked examples are explicit.
  Generated points rows and sample rubric references follow actual counts.
- Blank example renders to 12 clean pages (all inspected); a populated long-content
  stress document renders to 11 pages with rubric headers repeated. Long rows split;
  excessive keep-with-next chains were relaxed after a footer collision was found.
  Generated native LO bullets and inherited Word list numbering are supported.
- Added `from-wizard` conversion without upstream/vendor changes. Synthetic
  package -> Wizard -> authoring DOCX -> package -> Wizard comparison passes with
  two assignments, two discussions, 140 points, rubrics, placements, rich text,
  hyperlinks, and video. Source contracts are immutable and hashed; unsupported
  semantics stop conversion with a ledger. Dates, carried quizzes and nested
  modules remain explicitly unsupported in this adapter, not silently dropped.
- Adapter DOCX rendered and all four pages inspected after correcting an inherited
  Title border and an empty-cell paragraph that stranded a week heading.
- Read now emits readiness, source accounting and relationship reports. Exact
  activity rename previews show each structural reference; applying requires named
  authorization/reason and a new output copy. Other ZIP parts and narrative text
  are preserved; source remains untouched.
- Runner shows activity counts, readiness, term-aware safe output names, distinct
  verification statuses, and a reviewed editable calendar. CLI accepts calendar
  files and per-week scaffold counts. Explicit preview results never advise import.
- Missing rubric extraction is classified not-applicable only when no rubric was
  planned or packaged. Missing expected rubric evidence remains a failure.
- Upstream QA scans raw activity HTML: generated `data-blueprint-placeholder`
  metadata caused false placeholder-leakage errors. Renamed internal attributes
  to `data-blueprint-pending`; visible draft labels and readiness are unchanged.
  Actual TODO/TBD/placeholder prose still fails QA and remains visible in reports.
- Media verification now checks iframe title/destination/count and explicit video
  placeholders independently of body text. Vimeo privacy query values are kept;
  YouTube share-link start times are converted to documented player seconds.
- Full integration run: 140 passed, 1 failed on the above metadata false positive.
  Subsequent affected tests: 40 passed in 8.56s. Runner agent's final batch: 28
  passed in 9.57s. Final full suite follows independent acceptance review.
- Vendor recheck: 33 files, no drift from pin or current local Workbench. No vendor
  files changed. Live Google candidate QA and documentation refresh are underway.

## 2026-10-09 — Independent acceptance audit

- Reproduced and fixed a source-accounting hole in table labels: extra authored
  paragraphs or arbitrary suffixes were previously consumed as structure. Week
  labels now accept only the known short/full wording, front labels the known
  vocabulary, and pre-week labels the first declared object's exact title.
  Additional text remains unresolved and blocks packaging. The known legacy LO
  sublabel and explicit authoring guidance remain recognized.
- Structural rename now uses recorded object/relationship roles. A paragraph in
  an activity body that merely quotes `Assignment:`, `Gradebook item:` or
  `Used by:` is preserved. Internal-link keywords may vary in case, but the
  referenced title must match exactly. Exclusive-output cleanup cannot remove
  a file created by another writer during the initial existence-check race.
- Readiness walks content blocks even when a manually edited model omits `src`;
  missing provenance cannot conceal a pending entry. Null grading plans and
  missing/empty overview objects are rejected by the input contract.
- Focused audit/rename/pipeline validation: **51 passed in 12.43s**. Additional
  audit regressions and final full-suite validation are in progress.
- UNE live evidence so far: blank and populated drafts imported as native Docs,
  PAGELESS confirmed, exported as DOCX; intended native edits preserve headings,
  two native LO bullets, bold/italic/link runs, an added second Week 1 discussion,
  and completed/pending video markers. Normalized semantic comparisons match
  after excluding only provenance, list identifiers and guide style names.

## 2026-10-09 — Google exports through the package pipeline

- All three actual UNE Google exports build and verify locally with zero failed
  checks: minimal blank (13 passed, 3 inapplicable), populated draft (14 passed,
  1 inapplicable), and natively edited draft (14 passed, 1 inapplicable). Each
  remains `draft`; successful structural verification does not mark it ready.
  Details and SHA-256 values: `/tmp/bpk-implementation-20261009/google/package-results.json`.
- Ran the edited Google DOCX through the real guided runner in noninteractive
  preview mode using isolated remembered-state storage. Read -> build -> verify
  succeeds, the results card says draft preview, and next steps ask the author
  to resolve readiness findings. Run transcript:
  `/tmp/bpk-implementation-20261009/google/populated-edited-runner.log`.
- Full suite at this checkpoint: **150 passed in 34.05s**. No vendor drift across
  all 33 pinned files. A final run follows the last acceptance regressions.
- Compatibility check against the released v0.2.2 blank found two exact legacy
  guidance sentences that need scoped recognition. Recognized them only in
  their proper authoring regions; the same sentence inside a page remains
  content. Added exact old front-matter prompts to readiness. Its incomplete
  `https://` syllabus URL remains an error until supplied by the author.

## 2026-10-09 — Final integrated authoring evidence

- A separate completed synthetic course was imported to UNE Google Docs, set to
  pageless, exported, and passed through the actual guided runner in ready mode:
  **14 checks passed, 1 inapplicable, 0 failed**, with no readiness findings.
  It contains 10 activities, nine grade items / 65 points, two rubrics, three
  checklists, five HTML pages, and two completed video blocks. Native Google
  edits and all four exported states match the intended course semantics.
- Retained account, document links, hashes, native-edit operations, export-layout
  findings and evidence limits are in
  [Google authoring QA](evidence/GOOGLE_AUTHORING_QA_2026-10-09.md).
  A compact durable copy of semantic and package results is in
  [Google package results](evidence/GOOGLE_PACKAGE_RESULTS_2026-10-09.json).
  Google conversion/API editing is verified; native canvas interaction and
  tenant video playback were not tested. Exported print pagination can differ.
- Independent acceptance review closed with **14 regression cases passed**:
  label-cell loss, quoted-directive preservation, exact-case link titles,
  missing-source-ID readiness/media, malformed required shapes and concurrent
  output preservation. No unresolved material finding within that review scope.
- Wizard conversion now accepts an absent rubric contract only when the hashed
  extraction inventory shows no rubric payload and activities have no rubric
  associations. Missing expected rubric data still blocks. The real rubric-free
  package -> Wizard -> authoring -> package -> Wizard cycle passes.
- Wizard DOCX/report publication is exclusive unless force was requested;
  deterministic concurrent-output tests preserve the other writer's artifacts.
  Final focused adapter suite: **16 passed in 5.21s**. All four adapter DOCX pages
  were rendered and inspected after final heading/pagination adjustments.
- README, authoring guide, capabilities, roadmap and changelog now describe the
  unreleased candidate and its actual supported subset. Old model JSON must be
  regenerated by reading the DOCX to obtain the source-accounting evidence.

## 2026-10-09 — Handoff

- Final required suite:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q`
  — **163 passed in 37.26s**. `git diff --check` is clean. The 33 vendored
  files equal both the recorded Workbench pin and the current upstream checkout.
- Final UX correction: numeric activity counts in authoring guidance become
  stale after native editing. Replaced them with count-free add/remove guidance
  valid for zero, one or multiple blocks. The checked-in eight-week example was
  regenerated with the same course identity and remains 12 pages; all eight
  affected week pages were inspected, and the other pages are pixel-identical
  to the prior render. Its content model is unchanged apart from provenance and
  guidance accounting. The final focused blank suite has 15 passing tests.
- The tested Google copies retain the earlier numeric guidance, as explicitly
  recorded in the Google QA note. Their content semantics and package evidence
  remain valid. The final count-free document adjustment was verified locally.
- Review surfaces: [blank DOCX](examples/blank_blueprint__8_weeks.docx),
  [authoring guide](AUTHORING_GUIDE.md),
  [Wizard conversion limits](WIZARD_AUTHORING_CONVERSION.md), and
  [Google QA](evidence/GOOGLE_AUTHORING_QA_2026-10-09.md).
- Remaining evidence boundaries: no new Brightspace import/re-export or playback
  round, no native Windows run, and no Google canvas/screen-reader inspection.
  Wizard conversion refuses its documented unsupported shapes. Older model JSON
  must be re-read from DOCX. Google export may change print pagination.
- No commit, push, release, upstream mutation, or tenant action was performed.
  The approved implementation is complete and ready for operator review.
- Final checked-in blank read: 8 weeks, 2 course pages, 0 rubrics, 58 joins,
  0 errors; draft with 125 pending fields. Its 16 existing
  `GRADED_WITHOUT_RUBRIC` warnings correspond to the minimal scaffold's 16
  grade-linked activities without sample rubrics; the author must supply or
  deliberately omit rubrics as appropriate.

## 2026-10-09 — Follow-up authoring UX and SME/ID review

- Operator identified bracketed writing prompts, compressed copyable examples,
  and insufficient opening directions. Requested a broader SME/ID review and
  explicit permission to defer optional design tokens and object connections for
  manual completion in Brightspace. Findings and remaining design decisions are
  recorded in [the design review](DESIGN_REVIEW_2026-10-09.md).
- Replaced generated bracketed writing prompts with ordinary prompt sentences.
  Added whole-sentence replacement instructions and an example; readable
  `Author note:` guidance; purpose/task/success-criteria cues; and explicit
  document-only fields. Older bracket forms remain supported. Ordinary prose
  similar to a prompt remains authored content.
- Added a reserved `Authoring reference` frame with separate multiline examples
  for activities, expandable panels, callouts, videos and internal links. Its
  contents are explicitly accounted for and excluded from learner output.
  A copy-and-edit workflow test moves the real examples into a weekly cell,
  adds a second assignment and panel, then builds and verifies the preview.
- Added the operator's optional/manual-completion note to the opening and
  reference section. The authoring guide explains how to remove grading/rubric
  declarations and reciprocal references, retain ungraded activities/unattached
  rubrics, and record deferred work in Extraction Notes. Declared connections
  still require exact valid targets.
- Independent SME and ID reviews informed the design report. The immediate
  revision improves guidance and choice; outcome mapping, assessment decision
  states, less repeated relationship data, readable recovery reports and new-user
  observation remain recommendations, not implemented claims.
- Course correction from rendering: added guidance initially produced orphaned
  checklist text and spacer pages. Removed the spacer after weekly tables and
  excess space before weekly frame headings; kept writing paragraphs readable.
  Final candidate is 15 pages, with one blank week per page and three organized
  reference pages. Each page was visually inspected using the bundled
  LibreOffice render. This is not a native Word/Google layout certification.
- Course correction from the full suite: the runner's raw text scan counted
  reference examples as actual activities. It now counts interpreted course
  objects. The existing title/count regression passes. The pre-run Ready card
  now says Review run settings.
- A broader diagnostic review traced a points-disagreement warning through the
  builder and existing regression: the builder already blocks without a recorded
  determination. Corrected the misleading read-time message and clarified the
  registry's missing-points policy; no grading gate behavior was changed.
- Validation: full suite **184 passed in 37.64s** before the final diagnostic
  wording adjustment; final post-adjustment suite recorded below. Vendor check:
  all 33 files equal the pinned commit and current upstream checkout.
- Additional synthetic manual-connection probe: removed grading declarations,
  matching grading rows and reciprocal rubric attachments, then performed a
  normal build and verification. **13 checks passed, 2 not applicable, 0 failed**;
  three activities remained ungraded and two rubrics remained unattached with
  explicit warnings. No manual Brightspace setup or tenant import was performed.
- Saved a separate [UX review DOCX](examples/blank_blueprint__8_weeks__ux_review.docx)
  because the earlier example appeared open in Word. The earlier document and
  its lock file were left untouched during this revision. Final source read:
  8 weeks, 8 assignments, 8 discussions, 58 joins, complete source accounting,
  0 errors. The blank intentionally remains a draft. Artifact hash and probe
  summary: [local UX evidence](evidence/AUTHORING_UX_RESULTS_2026-10-09.json).
- Evidence limits: no fresh Google round trip for this prompt/reference revision,
  no new-user usability study, no native screen-reader check, and no new tenant
  import or playback evidence. No commit, push or release.
- Final post-adjustment gate:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q`
  — **184 passed in 41.65s**. `git diff --check` is clean; capability and evidence
  JSON parse successfully. All 15 rendered pages passed visual inspection.
