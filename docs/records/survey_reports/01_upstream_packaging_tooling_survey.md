# Upstream coursecraft workbench: blueprint → Brightspace package tooling survey

Roots (read-only; nothing was run that writes):
- `U` = `~/Documents/D2l & Coursebuilding Tools /coursecraft_workbench`
- `F` = `~/Documents/MBA_620_Marketing_Major_Edit_Fall2026`

**Bottom line:** upstream has verified builders for individual object bundles, but nothing that reads a blueprint (DOCX, Markdown or JSON) and produces a package or a builder contract. That middle step is manual or assistant-guided today.

## 1. Authored content → importable package

**`U/scripts/build_course_component_package.py`** (68 lines, thin CLI over `U/scripts/d2l_package_lib.py`, 788 lines)
- Args (`:34-42`): `--input` JSON contract (required), `--output-dir` (required), `--source-dir`, `--force`.
- Output: `package/`, `package.zip`, `component_mapping.md`, `component_package_receipt.json` (lib `:781-787`).
- Emits:
  - grade items (`grades_d2l.xml`, `:142`)
  - "simple" rubrics (`:203`)
  - dropbox folders with grade join, rubric association and `date_due` (`:275-306`)
  - discussion forum and topics, optionally graded (`:310-351`)
  - checklists with categories and dated items (`:354`)
  - modules containing `html_topic` items and quicklinks `dropbox_link`, `discussion_link`, `checklist_link`, `quiz_link` (`:54-59`, `:445-488`)
  - checksummed `support_assets` (`:603-638`)
- Limits read from code:
  - Modules are a flat list, one level; no nested submodules and no module description (`:445-488`).
  - Any other item type raises `Unsupported module item type` (`:488`), so no URL-link or file topics.
  - It does not build quizzes; `quiz_link` only points at an existing code via `resource_code` (`:473`).
  - Grade categories are always empty (`:170`) and `type_id` is fixed at 1 (`:189`).
  - Discussion topics get no rubric association; only dropbox folders do (`:298-301`).
  - `html_topic` needs `filename` plus exactly one of `html_content` or `html_file` (`:583-591`); HTML is copied as-is, with no CSS inlining.
- **Inference (not run): more than one forum looks broken.** `payload_files["d2ldiscussion"]` is a single dict key overwritten per forum (`:667`) and registered once as `res_d2ldiscussion` (`:428`); forum id is hard-coded `"610"` (`:312`). Every test and live receipt uses one forum with several topics. Real exports register one `d2ldiscussion` resource per file (`U/docs/project/BUMG_650_FULL_EXPORT_XML_ANATOMY_AND_MANIPULATION_NOTES.md:55`).

**Page Kit** — `U/scripts/build_page.py`, `page_kit.py`, `check_page_conformance.py`, `build_page_package.py`
- `build_page.py` args (`:16-21`): `--kit` (`coursecraft.page_kit/1`), `--composition` (`coursecraft.module_composition/1`), `--output-dir`, `--mode review|learner`, `--stylesheet`, `--force`.
- It compiles `coursecraft.page/1` JSON into HTML topics with the CSS inlined (`page_kit.py:829`); learner mode refuses while blockers remain.
- Block kinds: prose, outcomes, video, disclosure, route_list, resources, creatorplus_group, callout, review_note, review_questions, raw_html (`U/workspace/reference/schemas/page-kit/page_kit.schema.json`).
- `build_page_package.py` (`:146-152`) wraps a verified page build into a one-module component contract of `html_topic` items (`:121-141`). Docstring: "It never authors quizzes or other native objects."
- Status: "experimental Workbench capability" (`U/docs/project/PAGE_KIT_MODULE_ASSEMBLY_METHOD.md:3`).

**Rubrics**
- `build_rubric_package.py` (`:18-26`): `--input` (.md/.txt/.json), `--output-dir`, `--context-dir`, `--force`. Input is a flat Markdown pipe table per rubric (`## name`, `- Kind:`, criterion/weight/level columns) or JSON; examples in `U/tests/fixtures/rubric_package/input/`.
- `make_rubric_package.py` ("Rubric Weave", `:30-61`) accepts DOCX tables, Markdown, JSON, or eligible `coursecraft.rubrics/1`, with `--preflight`, `--allow-even-spacing`, `--allow-equal-weights`. Intake templates: `U/workspace/reference/templates/rubric-weave/v1/`.
- Both emit rubric-only packages. A template build "never attaches a rubric to an activity" (`U/docs/project/RUBRIC_PACKAGE_BUILD_AND_LINKING_NOTES.md:141-143`); attachments live in activity XML (`:200-216`).
- Supporting: `flat_markdown_to_json.py`, `validate_rubric_package.py`, `compare_rubric_reexport.py`, `extract_course_context.py`.

**Quizzes** — `build_quiz_package_from_workbook.py`
- Args (`:1185-1205`): source is a normalized workbook or `coursecraft.quiz/1` JSON; also `--quiz-title`, `--grade-item`, `--grade-out-of`, `--module`, `--library-only`, `--resource-code`, `--orgunitconfig`, `--settings`, `--zip-output`.
- Workbook shape: question sheets with `question_code`, `bank_id`, `target_question_type`, `question_text`, plus an optional `Quiz_Structure` sheet (`U/docs/VERIFIED_WORKFLOWS.md:452-455`).
- Generated types: multiple choice, true/false, all-or-nothing multi-select, written response (`:476`).
- `validate_quiz_package.py` (`:717-733`) checks the result; `quiz_draft_intake.py` is a fresh-question workbook intake.

**Gates and others**
- `check_package_conformance.py` (`:163-176`): pre-import check of manifest namespaces/prefixes and material types for any generated package, plus Creator+ joins.
- `diff_packages.py` (`:954-959`): "Round-trip diff for Brightspace quiz packages" — quiz-scoped. Component round trips were verified by re-running the extractors instead.
- `generate_creatorplus_practices.py` (`:512`): one spec JSON, seed-driven practice JSON plus wrappers; not a package builder.
- `course_qa_report.py`: QA over any export or generated bundle.
- `U/tools/` holds only `brightspace-quiz-review-extractor` (export → workbook).

## 2. Export → blueprint, and the blueprint model

- `build_blueprint_bundle.py` (args `:1615-1687`) orchestrates `export_inventory`, `manifest_probe`, `reconstruct_course_structure --extract-html`, `extract_course_activities`, `course_qa_report`, then writes `<label>__blueprint.{json,md,docx}`.
- `blueprint_to_docx.py` (`:719-720`) and `docx_structure_qa.py` (`:317-318`) are the only consumers of the JSON; `rubrics_to_docx.py` renders `coursecraft.rubrics/1`.
- Schema: `U/workspace/reference/schemas/blueprint/blueprint_schema.json`, id `coursecraft.blueprint/4`.
  - Required (`:7`): `["schema","course_title","front_matter","before_week_1","weeks"]`; optional `template_reference`, `course_number`, `term`, `unplaced_activities`, `diagnostics`.
  - `front_matter` (`:63`): `course_description`, `required_materials`, `course_learning_outcomes`, `course_introduction`.
  - Each week (`:77-87`): `title`, `overview`, `learning_objectives` (block arrays); `resources`, `assignments`, `discussions`, `checklist`, `other_sections` (arrays of `labeled_section` = `{label, blocks, source_page?, level?}`).
  - Block (`:23-26`): `{kind, level, runs:[{text, href}], blocks?, meta?}`, kind in `p, li, label, practice, visual, dropdown, embed, image, file, hidden, divider`.
- It is a review/render model, not a build model:
  - Points, gradebook item and rubric name are text label blocks such as `"Points: 10 pts"` (`build_blueprint_bundle.py:550-556`, `:621-646`), not typed fields.
  - Rubric bodies are not in it; they live in separate `coursecraft.rubrics/1`.
  - Numeric due dates are deliberately excluded (`U/docs/project/blueprint-extraction/HOW_EXTRACTION_MAPS_TO_BLUEPRINT.md:138-145`).
  - The doc says: "It is an *extraction + review* tool, not a generator" (`:5`).
- **No blueprint reader, normalizer or ingester exists.** Nothing parses a blueprint DOCX or Markdown into `coursecraft.blueprint/4` or any build contract. `docx_to_review_md.py` (`:523-524`) only converts DOCX to review Markdown. The one "ingest" hit is a catalog plan loading blueprint JSON into SQLite (`U/plans/2026-07-12_course_component_catalog_pipeline_plan.md:134`).

## 3. Component contract in detail

- There is no JSON Schema for the input contract. Only the receipt has one (`U/workspace/reference/schemas/course/component_package_receipt_schema.json`); the contract is defined by lib code and tests.
- Examples: `U/tests/test_d2l_component_package.py:24-98`, and the contract used in the live round trip, `U/workspace/scratch/roundtrip/inputs/components_contract.json`.

Compact form (from the test fixture):
```json
{"package":{"title":"Fixture Bundle","manifest_identifier":"D2L_FIXTURE_BUNDLE","base_resource_code":"FIXTURE-BASE-0000"},
 "grade_items":[{"key":"grade_essay","name":"Essay One","points":10}],
 "rubrics":[{"key":"rubric_essay","name":"Essay Rubric",
   "levels":[{"name":"Advanced","value":10},{"name":"Developing","value":7}],
   "criteria":[{"name":"Clarity","descriptions":["Clear and precise.","Sometimes unclear."]}]}],
 "dropbox_folders":[{"key":"folder_essay","name":"Essay One","points":10,"grade_item":"grade_essay",
   "rubric":"rubric_essay","instructions_html":"<p>…</p>","date_due":"2026-09-20T03:59:59"}],
 "discussions":[{"key":"forum_main","forum_title":"Course Discussions","topics":[
   {"key":"topic_week1","title":"Week 1 Discussion","description_html":"<p>…</p>","score_out_of":5,"grade_item":"grade_discussion"}]}],
 "checklists":[{"key":"checklist_week1","name":"Week 1 Checklist","categories":[{"name":"Tasks","items":[{"name":"Post intro","date_end":"2026-09-18T03:59:59"}]}]}],
 "modules":[{"title":"Week 1","items":[
   {"type":"html_topic","title":"Week 1 Overview","filename":"week1_overview.html","html_content":"<html>…</html>"},
   {"type":"dropbox_link","title":"Essay One","ref":"folder_essay","date_due":"2026-09-20T03:59:59"},
   {"type":"discussion_link","title":"Week 1 Discussion","ref":"topic_week1"},
   {"type":"checklist_link","title":"Week 1 Checklist","ref":"checklist_week1"}]}]}
```
- Optional fields seen in code: `short_name`, `exclude_from_final`, `submission_type`, `is_hidden`, `support_assets[{source,target,role,sha256}]`, `extensions`.
- **Bridge from blueprint JSON to this contract: none.** The only adapter is Page Kit → contract (`build_page_package.py:63-141`). A shared "course object map" (blueprint → object map → package) is a proposal only (`U/docs/ASSESSMENT_2026-06-12_ECOSYSTEM_ARCHITECTURE_REVIEW.md:339`, `:464-471`, `:643-646`). `U/workspace/design/README.md:19` mentions a `*_brightspace_object_map.seed.json` pattern in the MBA 630 fork, not upstream.

## 4. Verification status

Ladder L0–L5 is defined at `U/docs/IMPORT_TEST_LOG.md:18-25`; L3 = imports, L4 = re-export compared.

| Capability | Status | Evidence |
|---|---|---|
| Component bundle | L4, 2026-06-16 | Receipt 3 (`IMPORT_TEST_LOG.md:183-197`): 1 module, 2 HTML topics, 3 quicklinks, 1 dropbox, 1 forum + 2 topics (1 graded), 3 grade items; "7 join edges traced, 0 unresolved" |
| Simple rubric attached to dropbox, plus rubric-only analytic rubrics | L4 | Receipt 5 (`:152-164`); attaching analytic rubrics "remains a manual/explicit step" |
| Rubric Weave R1 | Accepted live matrix (five-case sandbox import/re-export) | `VERIFIED_WORKFLOWS.md:658-662` |
| Quiz (4 types, random draw, grade item, module placement, library-only) | L4 | Receipts 4, 6, 7, 8 |
| Quiz strict-model route and six named settings | Bounded L4, 2026-07-21 | `DEVELOPMENT_ROADMAP.md:131-137`; `VERIFIED_WORKFLOWS.md:482` still says not performed |
| Page Kit / module-page assembly | L3, operator-reported only | Receipt 9 (`:67-92`): "must not be described as a completed round trip"; L4 closure "Deferred to horizon" (`DEVELOPMENT_ROADMAP.md:864`) |
| Whole-course package from one contract | Never built or imported | Guidance is "Prefer small element bundles over whole-course builds" (`VERIFIED_WORKFLOWS.md:763`) |
| Blueprint → Brightspace | `Documented`, human-guided only | `VERIFIED_WORKFLOWS.md:922-943`; method doc and skill, no script |

- The blueprint-to-Brightspace method doc says "Prefer reviewable shells before import-ready packages" (`U/docs/project/BLUEPRINT_TO_BRIGHTSPACE_PROTOTYPING.md:193-199`). The skill adds: model a repeatable page family with Page Kit contracts (`U/.codex/skills/blueprint-to-brightspace-prototyping/SKILL.md:16`).
- Roadmap: no blueprint → package or importer milestone exists. "Importer" there means the quiz one ("Maintain and extend the first generic quiz + questiondb importer/generator", `DEVELOPMENT_ROADMAP.md:23`). Workstream F is extraction only (`:349-356`). Milestone 9 is the component builder (`:836-850`).
- Stale doc lines: `VERIFIED_WORKFLOWS.md:760` still says to verify a graded topic on first import, though Receipt 3 covers one. `U/plans/2026-06-15_comprehensive_roundtrip_test_package.md:36` says "first real import still pending".

## 5. Templates

- `U/workspace/reference/templates/brightspace-course-pages/` holds hand-authored HTML topic templates:
  - `week-overview.sample.html`, `lesson.template.html`, `review-walkthrough.template.html`, `course-welcome.template.html`, `project-landing.template.html`
  - `course-page.css`, `page-kit.css`
  - snippets for dropbox and discussion description fields
  - `MODULE_LAYOUT_MENU.md`
- Dropdowns: `course-page.css` has a `details.disclosure` component (`MODULE_LAYOUT_MENU.md:82`), but `week-overview.sample.html` contains no `<details>`. Page Kit renders `disclosure` as `<details><summary>` (`page_kit.py:745-746`). In the minimal example kit, `module_overview` does not allow `disclosure`; only `lesson` does. A course kit can change that.
- `MODULE_LAYOUT_MENU.md:128-139` describes assembly as hand-writing the contract: "one module per week… `html_topic` entries for pages, `dropbox_folders` / `discussions` for activities". It also sets the convention that discussion due dates live in a weekly checklist (`:59-73`).
- `U/workspace/generated/shareable-brightspace-design-kit/` is a staged colleague copy/paste library (dropdowns in `elements/02-organize-it.html`, overview and lesson page templates); "not yet a standalone tool" (`DEVELOPMENT_ROADMAP.md:318-330`).
- `U/docs/prompt_schemas/COURSE_OVERVIEW_PAGE_PROMPT_SCHEMA.md:89` asks for "2-4 dropdown sections where useful" in prompt-driven drafting.
- `U/workspace/reference/blueprints/templates/Course Blueprint Template 2020 CGPS.docx` is only a style base for DOCX rendering.
- No template shell/export exists that the packager lays content into.

## 6. Upstream git state

- Branch `main` at `9d3a620`. One stash: "Preserved pre-fidelity adoption notes 2026-09-17".
- Uncommitted: six untracked `workspace/review/*__fork_drift.{json,md}` files only.
- Last 15 commits (all quiz or run/2 work):
```
9d3a620 Merge reviewed quiz integration with run2 lineage work
bd82557 Merge pull request #4 from timebeing92/fix/quiz-reviewed-export-promotion
e5c8dd1 fix: keep rejected image replacements contained and unchanged
4d4089c docs: record native workbook roundtrip verification and clock limit
7fe7332 fix: preserve native Multi-Select answer keys on Brightspace import
baea115 test: isolate output safety checks from distribution checkout
0aa34bf fix: connect extracted pools and draw scoring to reviewer additions
9f4dbb9 test: sanitize shared native fixtures and clarify workbook additions
da77a7d test: roundtrip accepted revisions through authorized package
7782afa test: package and reextract reviewer image replacements
d06631e feat: support reviewed image and question additions
87552d7 fix: preserve source prompt media and audit SME workbook edits
2d4e8c4 fix: apply accepted export edits without promoting build evidence
093dc3e Keep section labels and rich-source display diagnostics explicit
854ca6e Bind review layout mappings to source identities and rich-content policy
```
- No branch or worktree concerns blueprint → package. `refine-page-kit-foundation` is merged into main. `feat/mba630-reuse-tranche-1` is unmerged (reuse-audit and Ruby/Nokogiri experiment scaffolds). The nine worktrees are quiz, run/2 or reading-room work, several under `/private/tmp` and marked prunable.

## 7. Drift: upstream vs MBA 620 fork

- The fork was cut from `c1b2075` (2026-08-22); upstream main is 77 commits ahead. Every differing shared script in the fork is byte-identical to upstream at `c1b2075`, so the fork is behind, not locally modified.
- The stored drift report (`U/workspace/review/MBA_620_Marketing_Major_Edit_Fall2026__fork_drift.md`, dated Sep 1) says 0 drift and is stale.
- Identical in both: `build_course_component_package.py`, `d2l_package_lib.py`, `build_rubric_package.py`, `make_rubric_package.py`, `rubric_package_lib.py`, `rubric_authoring.py`, `build_page.py`, `build_page_package.py`, `check_page_conformance.py`, `diff_packages.py`, `generate_creatorplus_practices.py`, `blueprint_to_docx.py`, `extract_course_activities.py`, `course_qa_report.py`. Page-kit schemas, templates and skills also match.
- Differ (upstream newer):
  - `build_quiz_package_from_workbook.py`, `validate_quiz_package.py` — the fork lacks `7fe7332`, the Multi-Select answer-key import fix.
  - `check_package_conformance.py` — upstream adds Creator+ join inspection and `--package-profile`.
  - `page_kit.py` — upstream requires Creator+ payloads directly under `practice/`.
  - `build_blueprint_bundle.py`, `reconstruct_course_structure.py`, `course_artifact_contracts.py` — run/2 lineage and source-backed titles.
  - `docx_to_review_md.py` — table-comment fix.
  - Quiz internals: `quiz_normalization.py`, `quiz_build_support.py`, `extract_quiz_pool_review.py`, `quiz_promote_revisions.py`, and others.
- Upstream only: `creatorplus_package.py` (needed by the newer conformance check), `quiz_draft_intake.py`, `quiz_review_station.py`, `quiz_review_projection.py`, `quiz_assessment_review.py`, `quiz_unbind*.py`, `quiz_variant_control_matrix.py`, `quiz_question_types.py`, `quiz_review_text.py`, `local_evidence_output.py`, `verify_quiz_unbind_run.py`, `build_quiz_draft_templates.mjs`, `backup_workbench_to_dropbox.sh`; 13 tests; run/2 and quiz-draft schemas.
- Fork only: `F/scripts/build_mba620_week1_quiz_alignment_review.py` (course-specific review surface, not packaging). `F/workspace/design/mba_620/weekly_blueprint/blueprint_current.json` uses schema `mba620.blueprint_review_snapshot/1` (Google Doc paragraph snapshot); its README says it "is not an accepted course design or a build contract". The fork's `workspace/generated/import-ready-components/` and `prototypes/` hold only READMEs.

## Inference: what this means for an 8-week build

- The verified route is to hand-author or script one component contract per small bundle, with HTML overview pages from the templates or Page Kit, rubrics via Weave (manual attachment) or the simple inline rubric on dropboxes, and quizzes built separately.
- Blueprint → contract is the missing piece and would be new tooling. Upstream's own rules say to build it upstream first.
- For eight weekly discussions, the only proven shape is one forum with eight topics.
