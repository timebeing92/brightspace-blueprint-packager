## Downstream packager / blueprint-parser inventory (read-only survey, 2026-10-06)

Nothing was created or modified. All paths are under `~/Documents` unless absolute. "UP" = `~/Documents/D2l & Coursebuilding Tools /coursecraft_workbench`.

### Headline

Only three downstream implementations emit course-content packages (pages + activities), and they form one lineage:

1. **DSW 821** standalone builder (Apr 2026): the only true "flat blueprint DOCX to full course package".
2. Upstream `d2l_package_lib.py` was generalized from it on 2026-06-12 (`UP/scripts/d2l_package_lib.py:4-17`).
3. **MBA 630** full-course assembler and **RCORP** module-page packager (Aug 2026) build on or beside that library.

Everything else is quiz-only, rubric-only, or has no fork-only packager. `RCORP Grant Project` was not on your list; I found it through `UP/docs/IMPORT_TEST_LOG.md` Receipt 9.

### 1. DSW 821: `DSW_821_coursecraft_workbench/scripts/build_dsw821_summer_a_starter.py`

- **Size / date:** 1,821 lines, 2026-04-28, fork-only, no upstream library dependency.
- **Input:** `workspace/reference/blueprints/DSW 821 Blueprint - Summer A New Build .docx` (line 19), converted with macOS `textutil` (lines 63-70).
- **Parsing:** `extract_week_blocks` (lines 244-281) splits on `Week N` headings and the CGPS section markers (`Overview:`, `Learning Objectives:`, `Assignment(s) and Instructions:`, `Discussion Board Prompts:`, `Lecture topics`, `Assigned Reading and Multimedia:`).
- **Limit:** assignment, discussion and rubric metadata (titles, points, rubric text, markers) is hard-coded in the script (lines 573-942). The calendar is hard-coded too (`build_calendar`, line 952).
- **Output:** 16 weekly modules, one overview/learning-materials HTML topic per week, a course-resources page, `grades_d2l.xml`, `rubrics_d2l.xml`, `dropbox_d2l.xml` with rubric association and grade join (lines 1379-1420), `discussion_d2l_1.xml`, `checklist_d2l.xml`, a copied Academic Integrity quiz, and a manifest with quicklinks (line 1517 onward). `main` is at 1798-1817.
- **Pages:** plain `<section><h2>` with inline CSS (`build_html_page`, line 318); no accordions.
- **Import evidence: yes.**
  - `UP/scripts/d2l_package_lib.py:4-17` says the generated package "imported into Brightspace successfully" and its base code reappears in the 2026 re-export.
  - My own check: the live export `workspace/exports/unpacked/D2LExport_118102_DSW-821-Template_20265433/` carries the generator's code base `7A912B2F-4C15-4F4A-8E6E-4A0AF5D9821A-9000NN` (149 hits in `imsmanifest.xml`, 26 in `dropbox_d2l.xml`, 16 in `discussion_d2l_1.xml`) and its `course_files\week-NN\week-NN-overview-and-learning-materials.html` paths.
  - The DSW repo's own docs never say "imported".
- **Generated package:** deleted 2026-05-04 (`workspace/generated/import-ready-components/README.md`; `plans/dsw821_summer_a_starter_package_plan.md` marked superseded). Only `workspace/generated/prototypes/dsw821_summer_a_starter/html/week-01..16` remains.

### 2. MBA 630: `MBA_630_Financial_Management_Course_Build/scripts/build_mba630_fall_a_2026_package.py`

- **Size / date:** 1,329 lines, 2026-08-27, fork-only.
- **Relationship to upstream:** a wrapper. It imports `build_component_package` and `deterministic_zip` from the upstream path, hard-coded as an absolute path (lines 44-47, 1162-1165), and `rubric_package_lib` (line 830). The fork has no local copy of `build_course_component_package.py`, `build_rubric_package.py` or `check_package_conformance.py`.
- **Input is not a single flat blueprint.** It reads:
  - a spec JSON, `workspace/design/brightspace_packages/mba_630_full_course/mba630_fall_a_2026_package_spec.json` (schema `mba630.integrated_brightspace_package/1`: calendar, 5 quizzes, 5 discussions, 4 assignments, rubric sources, 8 checklists);
  - a hard-coded `TOPICS` / `MODULE_ITEMS` / `MODULE_TITLES` topology (lines 53-225);
  - pre-rendered HTML topics and native-object fragments;
  - rubric Markdown tables (`rubric_tables`, lines 477-507).
- **Page generation:** separate Ruby builders (`build_health_rebuild_frontend.rb` 794 lines, `build_trailworks_frontend.rb` 963, `build_atlantic_frontend.rb` 584, `build_northpoint_frontend.rb` 918, plus `scripts/lib/*.rb`). They run per-page canonical Markdown under `workspace/design/weekly_blueprint/…` through pandoc (line 184) and Nokogiri, with `workspace/design/scenario/frontend/assets/mba630-course.css`.
- **Additions beyond the upstream library:** analytic weighted rubrics (`write_rich_rubrics`, 827), discussion-rubric attach (859), quiz copy and dating (881), question-library merge (898), gradebook merge (909), quiz manifest resources (982), quicklink rewriting in HTML (1018), checklist descriptions (443), Creator+ payloads at root `practice/` (1064).
- **Output:** `workspace/generated/import-ready/mba_630_fall_a_2026_2026-08-25_{static,creatorplus}/`. Manifest resource types: 8 contentmodule, 43 content, 26 contentlink, d2ldiscussion, d2ldropbox, d2lgrades, d2lrubrics, d2lchecklist, 5 d2lquiz, d2lquestionlibrary. `validation_report.md` counts 4 assignments, 5 discussion topics, 6 rubrics, 14 grade items, 8 checklists and 52 quiz questions.
- **Earlier iterations:** `build_mba630_week_01_package.py` (888 lines), `build_mba630_weeks_01_02_package.py` (356), `build_mba630_native_quiz_packages.py` (504), with outputs in `workspace/generated/import-ready-components/{mba_630_week_01_2026-08-18, mba_630_weeks_01_02_2026-08-18, quizzes/}`. Validator: `validate_mba630_fall_a_2026_package.py` (807).
- **Import evidence: yes.**
  - `plans/2026-08-25-integrated-creatorplus-course-package.md:75` says the Aug 25 Creator+ build "was imported and tested".
  - `docs/project/CREATORPLUS_PRACTICE_PACKAGE_ARCHITECTURE_AND_UPSTREAM_NOTES.md:32-33,75` says the same.
  - My own check: the final tenant export `workspace/exports/raw/D2LExport_102527_BUFI-510-TEMPLATE_20269120 (1).zip` contains `MBA630-FALLA-2026-RUBRIC-990001..6` and 77 `MBA630-FALLA-2026-20260825…` manifest codes.
- **Post-import defects on record:**
  - Quicklink org-unit placeholders in static HTML did not resolve and were repaired by Manage Files overwrite (`plans/2026-08-26-week-01-02-link-repair.md`, `plans/2026-08-26-imported-html-link-audit.md`).
  - Creator+ JSON had to move to root `practice/`; the earlier local PASS is called "a false clean result" (plan line 84).
  - No formal `diff_packages` round-trip receipt exists. The builder's own receipt still reads `live_brightspace_operations: not_performed` (line 1267).

### 3. RCORP: `RCORP Grant Project/workspace/reference/rcorp/module_2/`

- **Scripts:** `build_topic_pages.mjs` (909 lines, 2026-08-17; page content and CSS embedded in the script) and `build_review_package.py` (428 lines; standalone ElementTree manifest writer, absolute project path at line 22).
- **Output:** `workspace/generated/brightspace/rcorp/packages/module-2-review-prototype-2026-08-17/`: one module, 7 HTML topics, 2 Creator+ JSON payloads, an empty quiz shell. No assignments, discussions or rubrics.
- **Import evidence:** operator-reported only, with no re-export (`UP/docs/IMPORT_TEST_LOG.md` Receipt 9).
- **Blueprints:** flat Markdown blueprints exist (`docs/blueprints/0N_*.md`), but `docs/_build_assets/build_flat_blueprints.py` (603 lines) only renders them to DOCX. It does not parse them into package data.
- **Upstream handoff:** `workspace/generated/upstream-coursecraft/coursecraft-module-page-assembly-candidate-2026-08-17/` (`candidate/scripts/render_module_pages.mjs`, `build_module_page_package.py`, `docs/01`-`09`). Inference: this is the origin of upstream `page_kit.py`, `build_page.py` and `build_page_package.py`, all dated 2026-08-17.

### 4. Other directories

| Directory | Fork-only scripts | Shared packaging scripts vs upstream | Generated packages | Import evidence |
|---|---|---|---|---|
| `CHEM_1035_15W_…_Course_Build` | 15 `quiz_*.py` (e.g. `quiz_import_workshop.py`, 948 lines, 2026-10-01), all quiz-only | component, rubric, conformance identical; `build_quiz_package_from_workbook.py` ahead (1,262 vs 1,234 lines) | `import-ready-components/quizzes/` only (chem1020 suites, `nine_types_*`, 2026-09-29) | Yes, quizzes only: `docs/IMPORT_TEST_LOG.md` Receipts 10-12, sandbox 44786 |
| `CHEM_1030_1031_…` | none in `scripts/`; `workspace/scratch/chem1030-week01-build/make_inputs.py` (222 lines) turns reviewed week HTML and snippets into a contract for the upstream builder | stale older copies | `bundles/chem1030-week01/` (Jun 17: content, dropbox, discussion, grades, checklist) | Unknown; round trip is listed as a future step in `plans/2026-06-17_orgo_workbench_buildout.md:22` |
| `BUMG 660_brightspace-d2l-workbench` and `MGT_660_…share_bundle` (script copies) | `build_bumg_660_rubrics_only_first_pass_package.py` (1,115), three `build_*_first_pass_quiz_package.py` (787-851), validators; content hard-coded | predates them (absent) | `import-ready-components/{quizzes,rubrics,checklists}` | Yes for rubrics and quizzes, per `UP/docs/IMPORT_TEST_LOG.md` Receipts 1-2 ("field-proven") |
| `EDU_695`, `Companion_Animal_Death_Doula` | none | identical | README only | n/a |
| `EDU_707`, `OCHEM1_…` | none | stale older copies (e.g. `check_package_conformance.py` 167 vs 205 lines) | README only | n/a |
| `CHEM_1020_Workbench` | none | predates them (absent) | README only | n/a |
| `MBA_620_…` (this repo) | `build_mba620_week1_quiz_alignment_review.py` (review, not packaging) | component and rubric identical; conformance stale | not checked | n/a |
| `Brightspace_HTML_Styling_Guide_Workbench` | `build_html_workbench.py` (423; static preview navigator, explicitly not import evidence), `serve_creatorplus_surrogate.py` | identical | no packages | n/a |

Not packagers: `GitHub/brightspace_UI_core` (a clone of D2L's `@brightspace-ui/core`), `_archive_superseded` (Gen-1 starters and quiz extractor copies), `brightspace-rubric-package-starter` (rubric ancestor), `GitHub/mac-llm-brightspace-lab`, and the sibling bundles under `D2l & Coursebuilding Tools /`. The Blueprint Wizard (`brightspace-blueprint-runner`) runs export to blueprint, the opposite direction.

### 5. Template artifacts

No downstream packager lays blueprint content into an accordion or dropdown template. DSW and MBA 630 pages contain no `<details>`.

- **Upstream:** `UP/workspace/reference/templates/brightspace-course-pages/` (`week-overview.sample.html`, `lesson.template.html`, `page-kit.css`, snippets). `page_kit.py:746` has a `<details>` block.
- **Styling Guide Workbench:** `workspace/html/areas/02-toolbox-module/Overview Page Template (Responsive. WCAG 2 Standards).html`, `Call-Out and Drop Down.html`, `01-colleague-guide/styled-pages/overview-page-template.html`, `elements/brightspace-element-library.html`, and a vendored `brightspace-frontend-design-bundle`.
- **BUMG 660:** `workspace/Brightspace HTML Pages-templates-styling/` (Basic and BUMK 515 exemplar overview templates) and `workspace/generated/BUMG_660_Week_N_Overview_Stand_In.html`.
- **Loose files:** `Documents/Dropdown & Callout Library.html`, `Documents/BUMK 515 Overview.html`.
- **Template shell exports:** MBA 630 `workspace/exports/raw/20260825-171600__mba630-fall-a-shell-2026-08-25/`; DSW used a DSW-820 template export as shape evidence.

### 6. Backport / upstream discussion

- `MBA_630…/REUSE_RESIDUE_ROSTER.md`: C-001, C-002 and C-019 are implemented upstream. The full-package assembler (C-042) is "MBA-specific and downstream only". The cluster C-009/011/014-017/021/022 is "future consideration".
- `MBA_630…/plans/2026-09-02-coursecraft-reuse-implementation.md` and `…-adjacent-integration-closeout.md`.
- `UP/workspace/review/mba630_repository_reuse_fable_audit_2026-09-01/capability_inventory.tsv`: C-022 whole-course object contract = ADAPT, high priority; C-016 quicklink diagnostics = ADAPT; C-042 = DOWNSTREAM_ONLY, "extract only missing contracts/tests".
- RCORP candidate `docs/04_UPSTREAM_ADMISSION_AND_INTEGRATION.md`.
- `CHEM_1035…/plans/0041-quiz-upstream-consolidation-assessment.md` (quiz lane).
- `ECOSYSTEM.md` in the tools root, lines 123-148 (downstream review rules).

### Comparative table

| Implementation | Location | Input | Objects emitted | Tenant-proven? | Last touched | Status |
|---|---|---|---|---|---|---|
| DSW 821 starter builder | `DSW_821…/scripts/build_dsw821_summer_a_starter.py` | CGPS blueprint DOCX + hard-coded metadata | modules, HTML topics, dropbox, discussions, simple rubrics, grades, checklists, copied quiz | Yes (lib docstring; codes in export 118102) | 2026-04-28 | fork-only; generalized upstream |
| MBA 630 full-course assembler | `MBA_630…/scripts/build_mba630_fall_a_2026_package.py` + Ruby frontends | spec JSON + per-page Markdown + rubric Markdown + quiz packages | all of the above plus analytic rubrics attached, 5 quizzes and question library, Creator+ | Yes, with post-import link and Creator+ repairs (plan line 75; codes in export 102527) | 2026-08-27 | fork-only wrapper over upstream libs |
| RCORP module pages | `RCORP Grant Project/workspace/reference/rcorp/module_2/` | content embedded in `.mjs` | module, HTML topics, Creator+, empty quiz | Operator-reported only (Receipt 9) | 2026-08-17 | downstream; candidate handed upstream |
| CHEM 1030 week 1 | `CHEM_1030…/workspace/scratch/chem1030-week01-build/make_inputs.py` | reviewed HTML to contract | module, topics, dropbox, discussion, grades, checklist | Unknown | 2026-06-17 | upstream builder + scratch adapter |
| BUMG 660 rubric/quiz builders | `BUMG 660…/scripts/` | hard-coded / workbook | rubrics; quizzes; checklists | Yes (Receipts 1-2) | 2026-04-02 | superseded by upstream |
| CHEM 1035 quiz workshop | `CHEM_1035…/scripts/quiz_*.py` | review workbook | quizzes, question library | Yes (Receipts 10-12) | 2026-10-01 | fork-only, quiz lane |
| Upstream component builder (reference) | `UP/scripts/d2l_package_lib.py`, `page_kit.py` | JSON contract | modules, topics, dropbox, discussion, simple rubric, grades, checklist | Yes (Receipts 3-5, sandbox 44786, 2026-06-16) | 2026-09 | upstream |

### Ranked view (inference)

1. **MBA 630 assembler on upstream `d2l_package_lib` + `rubric_package_lib`** is the most complete and most recently proven object coverage: overview and resource pages, discussions, assignments, attached analytic rubrics, quizzes, grades, checklists, all present in a real course export. Its weakness for your purpose is the front end: topology is hard-coded and content comes from many per-page Markdown files, not one flat blueprint. It also has known post-import gaps (HTML quicklink placeholders, Creator+ path).
2. **DSW 821 builder** is the only one that actually parses a flat CGPS blueprint document into week sections and produced an imported 16-week course. Its activity and rubric metadata is hand-entered in code, rubrics are simple, and its XML emitters already live upstream. Its reusable asset is the parsing approach (`extract_week_blocks`, `extract_subblock`), not the serializer.
3. **Upstream contract builder + Page Kit** is the proven serializer, but nothing upstream or downstream normalizes a flat blueprint into its contract. That middle step is the missing piece; the closest starting points are DSW's parser and MBA 630's spec JSON (audit item C-022).

RCORP and CHEM 1030 are narrower page or week demonstrations. BUMG 660 and CHEM 1035 are rubric/quiz-only.
