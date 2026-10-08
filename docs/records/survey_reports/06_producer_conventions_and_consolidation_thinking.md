## Ecosystem producer conventions and consolidation thinking, distilled for the blueprint parser/packager

All paths are absolute under `HUB = ~/Documents/D2l & Coursebuilding Tools /` (trailing space). Abbreviations:

- Repos: `WB` = `HUB/coursecraft_workbench`, `BB` = `HUB/brightspace-blueprint-bundle`, `RB` = `HUB/brightspace-rubric-bundle`, `QB` = `HUB/brightspace-quiz-bundle-public`, `FD` = `HUB/brightspace-frontend-design-bundle`, `WS` = `HUB/coursecraft-workshop-space`.
- Hub docs: `ECO` = `HUB/ECOSYSTEM.md`, `REC` = `HUB/RECOMMENDATION_2026-07-19_PRODUCTIZATION_AND_DESIGN.md`, `CODEX` = `HUB/CODEX_REVIEW_OF_FABLE_PRODUCTIZATION_AND_DESIGN_RECOMMENDATION_2026-07-20.md`, `QBWO` = `HUB/QUIZ_BINDER_EXPERIENCE_AND_MYTHOS_WORK_ORDER_2026-07-20.md`, `R4` = `HUB/FABLE_QUIZ_BINDER_R4_AND_CAPABILITY_LAB_COMMISSION_2026-07-23.md`, `HF` = `HUB/FABLE_RUBRIC_LOOM_HUGGING_FACE_SPACE_COMMISSION_2026-07-24.md`, `WEAVE` = `HUB/CODEX_RUBRIC_LOOM_WEAVE_COMMISSION_2026-07-25.md`, `HALL-F` / `HALL-S` = the two `*_WORKSHOP_HALL_*_COMMISSION_2026-07-27.md` files, `LAYERS` = `HUB/RECOMMENDATION_2026-07-25_CATALOG_COURSE_LAYERS.md`, `DESK` = `HUB/PLAN_2026-09-14_COURSECRAFT_DESKTOP.md`, `QPLAN` = `WB/plans/2026-07-15_quiz_tooling_consolidation_and_ecosystem_sequence.md`.

### Findings that change what you build

1. **A page compiler and page packager already exist upstream.** Workbench owns an experimental Page Kit: contracts `coursecraft.page_kit/1`, `coursecraft.page/1`, `coursecraft.module_composition/1`, `coursecraft.page_build/1`, with `scripts/build_page.py`, `check_page_conformance.py` and `build_page_package.py` (`WB/docs/project/PAGE_KIT_MODULE_ASSEMBLY_METHOD.md:19-32,148-206`). Scripts of the same names are in the MBA 620 fork's `scripts/`; I did not diff the fork's copies against the hub's. A separate renderer or packager in the new tool would breach the standing rule "never a second parser/schema/builder" (`REC:683`).
2. **Direct precedent for your promotion path.** `HUB/governance/promotion-records/records/PR-2026-918-page-kit-module-assembly.json:8-19,72-79`: a course-build renderer (RCORP) was handed off as a checksum-bound candidate and re-expressed upstream as `promote_new`.
3. **The authoring contract must be separate from `coursecraft.blueprint/4`.** That schema is the "structured model emitted by build_blueprint_bundle.py from a Brightspace/D2L export" (`BB/schemas/blueprint_schema.json:5`).
4. **The progress `run_end.outputs` enumeration is closed, and an unreviewed extension is a still-open defect.** Rubric Loom Weave added six keys under `/1` and the parity check still fails (`ECO:1014-1023`).
5. **Whole-course build/import already has a reserved name and a gate.** It is "Course Foundry", with the posture "do not open this frame yet" (`LAYERS:101-111`).

### A. Producer conventions (evidence)

**CLI shape**
- One orchestrator script per door: positional source, `--output-dir`, `--label`, `--force`, `--preflight/--peek`, `--progress-events`, `--step-timeout`, `--expected-source-sha256/-bytes` (`RB/scripts/run_weave_bundle.py:652-684`).
- Exit codes are stated in the module docstring: "0 success, 1 producer or verification failure, 2 usage, environment, or authoring-policy refusal" (same file `:10-11`). Unravel adds `3` for no evidence (`RB/scripts/make_release_asset.py:82-87`). Ctrl-C returns `130` (`RB/docs/RUBRIC_LOOM_WIZARD.md:216-217`).
- Wizard layer flags are `--yes`, `--plain`, `--brisk`, `--doctor` (`RB/scripts/rubric_loom_wizard.py:1840-1844`). "`--yes` never supplies missing rubric decisions" (`RB/README.md:237-238`).
- Without `--progress-events`, stdout "must stay exactly" the historical output (`BB/knowledge/PROGRESS_EVENTS_CONTRACT.md:81-82`).
- Blueprint returns 0 for `ok` or `partial`, else 1 (`BB/scripts/build_blueprint_bundle.py:2794`).

**Progress events, `coursecraft.progress/1`** (`BB/schemas/progress_events_schema.json`)
- Flow: "one run_start, then step_start/step_end pairs, then exactly one run_end" (`:5`).
- `run_start` requires `event, schema, label, total, steps` (`:23-29`).
- `step_start` requires `event, index, total, label` (`:57-62`).
- `step_end` requires `event, index, status(ok|error), seconds` (`:84-104`).
- `run_end` requires `event, status(ok|partial|error)` (`:117-131`).
- `run_end.outputs` is closed (`additionalProperties:false`, `:140-236`). Its keys are `markdown, json, docx, workbook, rubrics_json, rubrics_unparsed, rubrics_workbook, rubrics_docx, qa_report, render_qa_dir, docx_structure_report, docx_structure_json, status_report, status_json, run_identity`.
- `issues[].status` is `failed|degraded|skipped` (`:237-263`). `delivery` is `{usable, empty, core_failures}` (`:308-330`).
- Consumers "must use these paths rather than re-deriving output locations" (contract `:32-34`).

**Run receipt, `coursecraft.run/1`** (`BB/schemas/run_identity_schema.json`)
- Required fields: `schema, run_id(^cc:run:), status, started_at, finished_at, source, producer, contracts, parameters, steps, emitted_files, receipt_path, diagnostics, extensions` (`:7-15`).
- `producer` carries `component, identity_state(release|git|unknown), version, repository, ref, commit, dirty` (`:63-77`).
- Step status is `completed|skipped|failed|unresolved` (`:95`).
- Artifacts carry a relative `path`, `bytes`, `sha256`, `media_type`, `contract` (`:104-116`).
- It is emitted as `<label>__run_identity.json` (`ECO:284-285`).
- `run/2` exists, Workbench-owned, and adds export-lineage fields (`ECO:257-263`).

**Output layout**
- Blueprint: `<output-dir>/<label>__blueprint_bundle` (`build_blueprint_bundle.py:1991`).
- Weave: `output/<label>__weave_bundle` (`run_weave_bundle.py:749-754`).
- Component packages: `package/`, `package.zip`, `component_mapping.md`, `component_package_receipt.json` (`WB/docs/VERIFIED_WORKFLOWS.md:749-750`).
- Release manifests declare fixed artifact keys, paths and roles, with one marked primary (`RB/scripts/make_release_asset.py:103-130`).

**Diagnostics**
- Record shape: `{id: diag-NNNN, code: UPPER_SNAKE, severity, message, location, remediation, extensions}` (`RB/workspace/reference/schemas/rubrics/rubric_authoring_schema.json:19-32`).
- Severity vocabularies differ across lanes: `info|warning|error` (rubric authoring), `note|warning|error` (`WB/workspace/reference/schemas/page-kit/page_build.schema.json:73`), and `breaks/warnings/notes` (QA summary, progress schema `:285-305`).

**Verdict language**
- "The three verdicts answer different questions and must not be conflated" (contract `:41-54`).
- A generative vocabulary was proposed: `delivery.faithful / valid / empty`, with "importable" reserved for L4 shapes (`REC:169-177`).
- "Never use **importable**, **Brightspace-ready**, **verified**… without naming the relevant validation/evidence level" (`QBWO:367-369`).
- "Delivery claims fail closed" (`RB/docs/RUBRIC_LOOM_WIZARD.md:190-193`).

**Contracts and pins**
- Contract `$id` form is `coursecraft.<name>/<n>`. Evolution is additive; a bump is required on rename, meaning change or join change (`ECO:231-248`).
- Shared contracts are registered with byte-parity copies in `HUB/ecosystem.json:115-238`.
- Vendored producer files are pinned in `upstream/workbench_pin.json` (`coursecraft.workbench_vendor_pin/1`, source commit plus per-file sha256; `RB/upstream/workbench_pin.json:2-14`).
- Consumer pin: `coursecraft.bundle_pin/1` (`WS/rubric_pin.json:1-10`). Runner pairing: `HUB/brightspace-rubric-loom-runner/BUNDLE_COMPATIBILITY.json:1-9`.
- Release manifest: `coursecraft.bundle_release/1`, with per-capability `status, entry_point, source_forms, output_artifacts, steps, exit_codes` (`make_release_asset.py:472-538,579-594`).
- Pins "do not float to the current upstream HEAD" (`ECO:181-184`).

**Determinism**
- "With an explicit `package.base_resource_code`, normalized ZIP timestamps and permissions make repeated builds byte-stable. If the builder must mint a UUID, the receipt marks the build as non-deterministic" (`WB/docs/project/BRIGHTSPACE_PACKAGE_STRUCTURE_AND_IMPORT_NOTES.md:105-107`; code at `WB/scripts/d2l_package_lib.py:109-114,558-559,730-731`).
- `build_page_package.py` requires `--base-resource-code` (`:148`).
- Page builds are transactional (Page Kit method `:44-45`).

**Privacy**
- "Never commit raw course exports, real course rubrics, student data, tenant identifiers, cookies, or tokens"; fixtures must be synthetic (`RB/AGENTS.md:23-29`).
- "Do not emit absolute machine paths in deliverables" (`R4:257-260`).
- Outputs inside a repo must sit in a gitignored lane (`QB/scripts/local_evidence_output.py:36-57`).

**Licensing**
- Licensing is repo-level: `LICENSE` (AGPL-3.0-or-later), `COMMERCIAL.md`, `LICENSE_POSTURE.md` (`RB/LICENSE_POSTURE.md:3-6`), `NOTICE.md`.
- A grep for SPDX across five bundles found no per-file headers. Scripts open with a docstring stating the boundary and exit codes.
- "Do not add AI-authorship or assistant-provenance notes to generated bundles or source files" (`BB/AGENTS.md:20-23`); "no AI co-author trailers" (`REC:693-694`).

**Tests**
- Vendor check plus pytest before commit (`RB/AGENTS.md:31-41`).
- A boundary test asserts the UI imports no semantic modules (`RB/tests/test_repository_controls.py:108-124`).
- Golden run over a committed example (`BB/README.md:288-299`).
- Synthetic journey Weave → validate → Unravel (`RB/README.md:300-310`).
- "A serializer without a validator and semantic differ is not an admitted candidate" (`R4:517-518`).

**Evidence ladder**
- L0 parse/schema, L1 in-process round trip, L2 shape plausibility, L3 imports, L4 re-export diff with every difference classified, L5 human review (`WB/docs/IMPORT_TEST_LOG.md:16-25`). The receipt template is at `:35-47`.
- Registry rows carry `status`, `evidence_level`, `receipt_refs`; unknown shapes are `reject_without_transforming` (`QB/workspace/reference/schemas/quiz/quiz_build_capabilities.json:4-18`).
- Live work needs a `LIVE_RUNBOOK.md`, an object-name prefix, and an append-only ledger; delete "by exact recorded object identity" (`WEAVE:264-286`).

**Authoring versus extracted**
- "Do not mutate `coursecraft.rubrics/1` into an authoring schema… The user-interface metaphor must not appear in the contract name" (`WEAVE:175-190`).
- An extraction record enters authoring "only through the strict adapter" (`RB/workspace/reference/schemas/rubrics/README.md:11-14`).

**Runners**
- A runner "must not parse D2L XML… or invent a second progress or receipt contract" (`HUB/brightspace-rubric-loom-runner/AGENTS.md:15-19`).
- Each runner ships an exact pair plus `RELEASE_MANIFEST.json` (`:33-42`).
- The Blueprint runner reads `run_end.delivery` and treats an unusable run as a failed reading (`HUB/brightspace-blueprint-runner/scripts/blueprint_wizard.py:945-967,1206-1208`).

### B. Consolidation thinking

**Principles (evidence)**
- "Not a greenfield project… Superseded does not mean disposable"; consolidate upstream before any wizard, hosted surface or catalog work (`QPLAN:16-25`).
- "A small related contract family, not one enormous closed record", with a minimal envelope, `extensions`, typed unknowns, and absent/unknown/not-applicable/unresolved/unsupported kept distinct (`QPLAN:102-157`).
- Phases: 0 provenance freeze, 1 capability/corpus matrix, 2 contracts and identity, 3 extraction, 4 builder/validator/differ, 4.5 local reliability, 5 live round trips, 6 promotion (`QPLAN:191-340`).
- Phase 5 "is capability-specific rather than a blanket promotion veto" (`QPLAN:333-337`).
- "Encode the eye as data, enforce it as gates, teach it as receipts, and watch the drift" (`REC:135-138`).
- The registry is "a machine-readable capability registry, not a fourth data contract… the model's ability to preserve an observed shape never promotes that shape to builder support" (`WB/workspace/reference/schemas/quiz/QUIZ_CONTRACT_FAMILY.md:53-56`).
- Capability admission ladder, 10 steps from source anatomy to a separate registry proposal (`R4:553-569`).
- "Schema validity is not buildability… Local validation is not import evidence" (`R4:643-645`).
- "Treat the field vocabulary and shared model as the contract—not a single file format"; Word is "preserved source material entering a visible translation step" (`QBWO:271-284`).
- "Mythos may carry welcome, memory, and orientation. Plain language must carry state, evidence, risk, capability, privacy, failure, retention, and proof" (`QBWO:95-96`).
- "Use exact step names from the implementation as the only authority. UI flavor must follow" (`WEAVE:677-678`).

**Lit bench**
- A lit bench needs "a separately reviewed producer release and an exact consumer pin; repository presence alone is not availability" (`ECO:88-89`).
- Planned benches "stay unlit regardless of whether a private scaffold repo exists" (`HALL-S:308`).
- Required scaffold contents for a new bundle, and the pin/adoption-map fields, are listed at `HALL-S:416-442`.

**Corrections recorded**
- Fable's own adversarial pass (`REC:639-679`): a pre-Phase-5 hosted lane violated promotion order; an invented quotation was removed; done work had been described as pending.
- Codex's pushback (`CODEX:99-109`):
  - Do not put a new progress contract or governance work on the critical path before live evidence.
  - Too many prose authorities risk "multiple prose owners of truth".
  - Pilot "after the minimum compiler, inliner, conformance gate, and two or three exemplars".
  - "Gates can catch conformance defects; they cannot fully determine composition, hierarchy, tone".
  - Split decisions into now, after-evidence, and trigger-gated.

**Future directions to stay compatible with**
- Course layers, each with `provenance: extracted | authored`; "edges between layers as first-class evidence", with rubric↔activity attachment the decisive example; "Producers stay layer-blind" (`LAYERS:40-60`).
- Pagewrights' Guild's upstream surface "will be `brightspace-frontend-design-bundle`, not `brightspace-course-templates`" (`HALL-F:357-359`).
- Module Composer, "emitting the existing packaging contract JSON" (`REC:410-416`).
- Desktop: Page Kit "source contracts drive generated HTML"; "A review archive, Manage Files bundle, and Brightspace import package have different contracts"; initial scope "excludes whole-course round-trip authoring" (`DESK:76,79,214`).

### C. Page and template surfaces

**Three families (evidence)**
1. **Hand-authored templates**, in `WB/workspace/reference/templates/brightspace-course-pages/`:
   - Pages: `week-overview.sample.html`, `lesson.template.html`, `review-walkthrough.template.html`, `course-welcome.template.html`, `project-landing.template.html`.
   - Snippets: `activity-description`, `assessment-description`, `creatorplus-practice-embed`.
   - `course-page.css`, with tokens at `:14-26`. The component table and themes (House teal, Navy) are in `MODULE_LAYOUT_MENU.md:80-88,165-171`.
2. **Design kit**, staged at `WB/workspace/generated/shareable-brightspace-design-kit/` and preserved in `FD/`:
   - `elements/01-signal-it.html`, `02-organize-it.html`, `03-act-on-it.html`, `brightspace-element-library.html`.
   - `styled-pages/overview-page-template.html`, `lesson-page-template.html`, plus demos.
   - Its ZIP "is a Manage Files folder bundle, not a Brightspace import package" (`FD/README.md:55-56`).
3. **Page Kit**, the only one with a machine manifest (`WB/workspace/reference/schemas/page-kit/page_kit.schema.json`):
   - `kit_id`, `status(experimental|supported|retired)`, `delivery_surface: brightspace_html_topic`, `theme.theme_id` plus 11 colour tokens, `page_types[]{page_type, required_slots, allowed_blocks}`, an 11-item block vocabulary, and `lifecycle{blocking_review_states, raw_html_policy, creatorplus_provider_policy}` (`:6-18,43-65,69-83,93-128,133-151`).
   - The example kit has page types `module_overview` and `lesson` (`WB/workspace/reference/examples/page-kit/minimal/page-kit.json:24-37`).

**How selection works today**
- There is no registry of kits. Selection is whichever `--kit` and `--stylesheet` you pass (`WB/scripts/build_page.py:16-20`).
- The compiler embeds the stylesheet in a head `<style>` and records its sha256 (`WB/scripts/page_kit.py:829,1057`).
- "A course-specific Page Kit and page instances belong in the course repo" (method `:29-30`).

**Constraints**
- Four contexts: "standalone packaged HTML pages / Brightspace HTML topics / constrained description/editor fields / iframe or embed" (`WB/docs/project/FRONTEND_CONSTRAINTS.md:33-37`).
- Editor fields "strip `<style>` blocks, classes, and wrappers", so use the inline tier there (kit `README.md:10-14`).
- Activities are "NOT pages — inline-safe HTML description embedded in the payload XML" (`MODULE_LAYOUT_MENU.md:39-52`).
- "Choose the narrowest delivery surface"; state `Delivery surface: <chosen surface> because <reason>.` (`WB/docs/project/DELIVERY_SURFACE_MATRIX.md:7,70-76`).
- Avoid external CDNs and assumptions about iframe permissions (`FRONTEND_CONSTRAINTS.md:94-99`).
- The conformance gate emits these codes: `PLACEHOLDER_LEAK, REVIEW_CONTENT_LEAK, IFRAME_TITLE_MISSING, IMAGE_ALT_MISSING, H1_COUNT, INLINE_EVENT_HANDLER, JAVASCRIPT_URL, UNSAFE_HTML_TAG, DUPLICATE_HTML_ID`, plus warnings `DECLARED_RAW_HTML, HEADING_LEVEL_JUMP` (`WB/scripts/page_kit.py`).
- Creator+ wrappers are embedded verbatim; the missing iframe title stays a warning (method `:98-99,120-123`).
- Evidence status: one operator-reported L3 import, "not yet a Workbench-verified L4 round trip" (method `:221-223`).

**Inference**
- "A selection of templates" maps to a directory of kits (kit JSON plus stylesheet), chosen by `kit_id`.
- The BUMK 515 design would be a course-local kit. I did not verify whether Page Kit's fixed `.cc-*` markup can reproduce BUMK 515's page structure. "Semantic layout should not be forked for cosmetic variation alone" (method `:139-141`), so expect either a stylesheet mapping or declared `raw_html` blocks.

### D. Glossary

| Term | Definition | Source |
| --- | --- | --- |
| Producer | Deterministic engine repo that owns CLI, artifacts, schema copies and events | `ECO:63-76` |
| Bundle | Repo naming for a portable producer; "the product name is deliberately distinct from the repo name" | `RB/docs/REPOSITORY_BOUNDARY.md:12-14` |
| Runner | Colleague-facing launcher pairing one exact bundle; never parses D2L XML | `ECO:54-55` |
| Door | A verb-named entry path into one product (Unravel/Weave; Unbind/Compose/Rebind) | `RB/docs/RUBRIC_LOOM_EXPERIENCE_FRAME.md:14-17` |
| Bench | A Workshop Hall card and route presenting one producer; registry is presentation metadata only | `WS/bench_registry.py:1-8` |
| Lit / unlit | Lit means a reviewed release plus an exact consumer pin; unlit is planned and control-free | `ECO:88-89` |
| Pin | Recorded immutable commit plus digests of the last accepted promotion | `ECO:181-184` |
| Adoption map | File-level source/destination hashes with relationship (mirror, purpose-neutral adaptation, diverged by design) | `FD/NOTICE.md:19-27` |
| Promotion record | Structured review of cross-repo movement (`coursecraft.promotion_record/1`) | `HUB/governance/promotion-records/README.md:1-15` |
| Disposition | One of promote_existing, promote_new, integrate_shared_contract, remain_downstream, intentional_divergence, archive_as_provenance | `ECO:137-151` |
| Evidence levels | L0–L5 validation ladder | `WB/docs/IMPORT_TEST_LOG.md:16-25` |
| Operator window | Separately authorized live-Brightspace session with run-sheet and receipts | `REC:226-232`; `LAYERS:113` |
| Admission protocol | Checklist with receipts when a repo joins (charter, ecosystem rows, CI, corpus, drift policy); proposed | `REC:504-512` |
| Layer / edge | One domain's contract document about a course, with provenance; a first-class cross-layer relation with its own evidence level | `LAYERS:40-56` |
| Capability registry | Machine-readable statement of what may be built and claimed | `QUIZ_CONTRACT_FAMILY.md:53-56` |
| Truth chassis | Engine outcomes, stdout record, receipts and exit semantics a UI may not weaken | `R4:59-61` |

### Guidance for the new blueprint parser/packager — do now

1. **Define a separate authoring contract** with a plain name; `coursecraft.blueprint_authoring/1` is my suggestion. Never write into `coursecraft.blueprint/4`; accept Wizard output only through an adapter that refuses what it cannot translate (`WEAVE:175-190`).
2. **Treat the Word/Google blueprint as preserved source entering a visible translation step.** JSON is machine truth. Fingerprint source bytes and bind the build to the reviewed bytes (`QBWO:271-284`; `RB/docs/RUBRIC_LOOM_WIZARD.md:195-203`).
3. **Make joins first-class records** with status and evidence; list ambiguous ones, never auto-resolve them. Keep `origin` separate from `review_state` (`WB/.../page.schema.json:78-79`; `QUIZ_CONTRACT_FAMILY.md:178-183`).
4. **Emit `coursecraft.page/1` and `coursecraft.module_composition/1`, then call `build_page.py`, `check_page_conformance.py`, `build_page_package.py` and `d2l_package_lib.py`.** Template choice is `--kit`. Native objects stay with their own builders (method `:125-129`).
5. **Use the CLI shape above:** positional source, `--output-dir`, `--label`, `--force`, `--preflight` (JSON), `--progress-events`; exit 0/1/2/130; exit codes in the docstring; default stdout stable.
6. **Write a `coursecraft.run/1` receipt validated against the schema.** Use relative paths and sha256 for every artifact, and record every explicit fallback in `parameters` (`WEAVE:192-212`).
7. **Emit progress in `/1` grammar from step-name constants, but keep new `run_end.outputs` keys in a clearly provisional schema.** Record the upstream decision as needed (`ECO:1020-1023`; `CODEX:101`).
8. **Require a fixed `--base-resource-code`,** add a double-build byte-equality test, and build transactionally.
9. **Use the diagnostic record shape** `id/code/severity/message/location/remediation/extensions`, and state which severity vocabulary you chose.
10. **Ship a small capability registry** covering html topic, module placement, discussion, dropbox, grade item, checklist and rubric join. Give each `status`, `evidence_level`, `receipt_refs`; reject anything unlisted.
11. **Keep verdict copy honest:** completion, then faithful/valid/empty; "nothing was imported"; never "importable" below L4.
12. **Before the sandbox import, write a `LIVE_RUNBOOK.md`,** set an object prefix, and keep an append-only ledger. Record L3 and L4 separately in the `IMPORT_TEST_LOG` format. The Blueprint Wizard read-back is L1, not import evidence.
13. **Use synthetic fixtures only, gitignored output lanes, and no absolute paths or course text in receipts or logs.**
14. **Give `tools/blueprint-packager/` promotion-ready contents:** README, AGENTS boundary (what it must never own), ROADMAP, CHANGELOG, tests, a synthetic example with expected output, one verify command, and a local list of the upstream script hashes it depends on (`HALL-S:416-442`). Draft a promotion record locally; do not write to the ledger.
15. **Pilot early, keep human sign-off, and do not let governance work block evidence** (`CODEX:107-109`).

### Naming candidates

The naming logic in evidence:
- Coinage is ⟨artifact⟩ + ⟨craft-role⟩ (`REC:277-281`).
- Doors are craft verbs.
- Mythos "should arise from the real work" (`QBWO:75`).
- Contract and repo names stay plain.

The candidates themselves are my inference.

1. **Blueprint Wizard, second door** (for example Draft for export→blueprint and Raise for blueprint→course; the Wizard's run phase is already "The drafting", `HUB/brightspace-blueprint-runner/README.md:180`).
   - Fits the two-door pattern and "Keep one… hub card and one… route with two doors" (`WEAVE:779`).
   - Caveat: the bundle charter is "extraction and review, not instructional-content generation" (`BB/AGENTS.md:32`), so the producer needs its own sibling repo.
2. **Course Foundry.** This is the existing coinage for exactly this horizon (`LAYERS:101`). It is gated; using it now claims the whole-course frame.
3. **Course Joiner / Joiner's Bench.** The tool's distinctive work is explicit joins. Possible doors: True (normalize) and Raise.
4. **Module Composer.** Already named as the CLI-first instrument (`REC:410`), and it matches `coursecraft.module_composition/1`. Plain register; "Compose" collides with a Quiz Binder door.
5. **Course Press.** Book-trade family with Binder and Pagewrights. Doors Proof and Print would mirror Page Kit's review and learner modes (method `:36-42`).

Plain repo name: the pattern is `brightspace-<domain>-bundle`. `brightspace-blueprint-bundle` is taken, and `brightspace-course-templates` must not be revived (`HALL-S:369-370`).

### Caveats

- **Method deviation:** I ran one `python3 -I -c` one-liner to summarize the structure of `RB/upstream/workbench_pin.json`, outside the cat/sed/grep rule. It wrote nothing. Everything else was cat/sed/awk/grep/ls/git log/git status.
- **Unread or partly read:**
  - `ECO:433-958`.
  - `WEAVE:305-455`.
  - `HF`, apart from `:161-200`, `:243-362` and `:439-494`.
  - `HUB/brightspace-interactives-bundle`.
  - Runner READMEs beyond the cited lines.
  - The private quiz bundle's docs.
  - The gitignored raw evidence corpus.
- **Tension to raise with the owner:** Rubric Loom keeps attachment "manual_only", while the Workbench component builder supports dropbox/grade/rubric joins (`MODULE_LAYOUT_MENU.md:44`). The layers proposal wants attachment as an edge "with its own evidence level" (`LAYERS:51-56`).
- **Commit trailers:** the ecosystem's standing constraint is "no AI co-author trailers" (`REC:693-694`), and I found none in the sampled recent Workbench and rubric-bundle commits. Confirm with the owner before applying the session's default trailer.
