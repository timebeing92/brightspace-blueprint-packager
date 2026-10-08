# Declared ownership/governance model for blueprint -> Brightspace packaging

HUB = `/Users/ehanson8/Documents/D2l & Coursebuilding Tools /` (trailing space). Read-only; nothing was created or changed.

Read in full: `ECOSYSTEM.md` (all 1212 lines), `ecosystem.json`, `README.md`, `repos.lock`, the Desktop plan, both RECOMMENDATION docs, the Codex review, `CROSS_MACHINE_HANDOFF`, the 07-27 and 09-08 implementation logs, the governance READMEs, the 2026-10-01 reconciliation checkpoint, PR-2026-915/918/919, and the three workbench docs. Grep or head only: other checkpoints, older logs, the commission docs, and the catalog/workshop READMEs and ROADMAPs.

## 1. Repos, roles, flow, vocabulary (evidence)

**Roles** (`ECOSYSTEM.md:42-59`, `ecosystem.json:8-114`):

| Repo | Declared role | Boundary |
|---|---|---|
| `coursecraft_workbench` | "Master R&D workbench, evidence lane, extractor development, method distillation, course-build bootstrapper" (L44); json: "upstream extraction policy and reference contracts" | "Does not become a dumping ground for course product. Promotes stable methods and schemas downstream." |
| `brightspace-blueprint-bundle` | "Portable deterministic Brightspace export-to-blueprint engine" (L51) | Owns CLI extraction, artifacts, schemas, and canonical `coursecraft.progress/1` (`ecosystem.json:145-147`) |
| `brightspace-blueprint-runner` | "Local terminal Blueprint Wizard" (L54); public v2.8.1 | "Wraps the bundle and consumes progress events. Does not parse D2L XML or infer artifacts." |
| `brightspace-rubric-bundle` | Rubric Loom producer: "Unravel extraction plus Weave authoring/package generation" (L52); public v1.3.3 | "Byte-pinned downstream copies of accepted Workbench rubric scripts… behavior changes go upstream first." |
| `brightspace-rubric-loom-runner` | Colleague-facing local runner (L55); v1.0.2 | "does not parse D2L XML or own rubric semantics" |
| `brightspace-quiz-bundle` / `-public` | Private dev history / sanitized public runtime rc.8 (L48-49) | Workbench-pinned producer |
| `brightspace-frontend-design-bundle`, `brightspace-interactives-bundle` | Private prerelease scaffolds (L50, L53) | No release, no Workshop pin |
| `coursecraft-workshop-space` | Hosted five-card Workshop Hall (L56) | "Presentation layer only." |
| `coursecraft-catalog` | Evidence graph, Reader, Archivist (L57) | "Consumes versioned bundle/workbench artifacts. Does not parse D2L XML." |
| stylistics-lab, media, ruby-lab | Private labs/accessory (L45-47) | No Workbench pin, contract, or release (L107-108) |
| `_archive_superseded/` | Provenance only (L58-59) | |

- **Not registered:** `coursecraft-program-explorer` (`ECOSYSTEM.md:789`) and `coursecraft-desktop`, which "does not yet exist" (`README.md:48-49`).
- **Course builds:** "Active course builds remain in `~/Documents/` as independent repositories" (`README.md:95`).

**Flow** (`ECOSYSTEM.md:63-76`): `workbench -> blueprint-bundle -> runner | workshop-space | catalog`, with the same shape for rubric and quiz.

- **Ownership split:** "The Workbench owns reusable extraction meaning, schemas, evidence rules, general-purpose transformations, and durable knowledge workflows. Downstream repositories own their product experience, release mechanics, operating constraints…" (L131-135).
- **Promotion is not automatic:** it is "not a rule that every successful downstream implementation must eventually move into `coursecraft_workbench`" (L127-129).
- **Six dispositions** (L140-151): promote into an existing capability, create a new upstream capability, integrate through a shared contract, keep downstream, record intentional divergence, archive as provenance.
- **Promotion record required** when reusable behavior moves between repos or semantic ownership changes (L173-176); the ledger is `governance/promotion-records/`.
- **Pins:** "do not float to the current upstream `HEAD`" (L182-184).
- **Availability:** "Promotion to a lit bench requires a separately reviewed producer release and an exact consumer pin; repository presence alone is not availability" (L88-89).
- **Drift checks:**
  - `scripts/ecosystem_status.py --check-contracts --check-pins` (`README.md:102-110`), with byte-for-byte contract comparison (`ECOSYSTEM.md:270-271`).
  - Per-bundle `upstream/workbench_pin.json` plus adoption maps (`ecosystem.json:239-291`).
  - Workbench `scripts/check_bundle_drift.py`, with per-file policies `mirror | diverged-by-design | bundle-only` (docstring L2-27).
  - `check_fork_drift.py` for course forks.

**Vocabulary:** there is no glossary; terms are defined by use.

- **Producer / consumer pin / lit bench:** L88-89 above.
- **Presentation layer:** "No pipeline code lives in this repo; pipeline changes land upstream first, then the pin bumps" (`coursecraft-workshop-space/README.md:71-79`).
- **Share bundle:** "Share bundles are distribution artifacts" (`UPSTREAM_FIRST_DEVELOPMENT_WORKFLOW.md:142-144`).
- **Capability:** registry-gated with evidence levels L1/L2/L4 (`RECOMMENDATION_2026-07-19:121-125`).
- **Surface rule:** "extraction engines emit facts; user-facing tools make those facts understandable, reviewable, and navigable without silently creating new truth" (`ECOSYSTEM.md:1145-1147`).

## 2. Blueprint, packaging, import, course forks, consolidation (evidence)

- **Blueprint Bundle charter:** "This is extraction and review, not instructional-content generation." (`brightspace-blueprint-bundle/AGENTS.md:32`). "The blueprint mirrors the exported course; it does not try to reconstruct an ideal design model" (bundle `README.md:303-304`).
- **Blueprint Wizard:** "The Wizard reads and reports. It does not: import anything into Brightspace or change the source export" (`brightspace-blueprint-runner/README.md:59-61`).
- **Quiz precedent for a generative tool:** it became a sibling bundle because "The blueprint bundle's charter… structurally forbids housing a generative builder; its `run_end.outputs` is a closed mirroring-specific enumeration; and the workshop hub already promises 'every bench wraps its own pipeline bundle.'" (`RECOMMENDATION_2026-07-19:154-160`).
- **Generic packaging already lives in the Workbench:**
  - `scripts/d2l_package_lib.py` and `build_course_component_package.py` were generalized from the DSW 821 fork builder (`REUSABLE_PATTERN_TRANSFER_CRITERIA.md:174-187`).
  - "Live-import verified 2026-06-16" (workbench `docs/project/DEVELOPMENT_ROADMAP.md:841-844`).
  - "Prefer small element bundles over whole-course builds (ground rule 9)" (workbench `docs/VERIFIED_WORKFLOWS.md:763`).
- **PR-2026-919** (implemented, `promote_new`): "Support-asset identity is a generic packaging capability, so it belongs in d2l_package_lib rather than a Page Kit-only fork. A thin adapter is retained…" (L64). Scope "excludes live import automation" (L30). "The parallel candidate packager was not copied" (L29).
- **PR-2026-918:** a course-fork (RCORP) candidate was "re-expressed" as a Workbench-owned Page Kit contract and compiler, `promote_new`, with "L4 remains held" (L33, L73, L102).
- **Blueprint as input:** "Treat a blueprint as a **design source**, not automatically as package truth" (workbench `BLUEPRINT_TO_BRIGHTSPACE_PROTOTYPING.md:39`); "often better for **structured first-pass construction** than for immediate final package generation" (L56).
- **Whole-course horizon:** the operator's goal is to "funnel all of this tooling into unified whole-course building/import in a TUI and workshop/Hugging Face capacity" (`RECOMMENDATION_2026-07-25:13-16`).
  - "Course Foundry… Recommended posture: **do not open this frame yet.** Name its trigger instead — e.g., *two layer domains ingested in the catalog + one edge type proven + Weave live-import verified*" (L101-110).
  - It "should inherit the admission protocol (W4) and the Phase-5-style operator windows" (L111-114).
  - Status of that document is advisory only (L3-5).
- **Future tool branches** (`ECOSYSTEM.md:974-981`): "Package Graph Visualizer/Diff" and "CourseCraft Launcher or Hub that opens Blueprint Wizard, Archivist, quiz, rubric, HTML, package-diff, and Creator+ tools from one place."
- **Course forks:** "The course-fork bootstrapper creates complete course-engineering workbenches and is not an application bootstrapper" (Desktop plan L46). The CHEM fork's workflow "remains local; no new upstream promotion" (`governance/checkpoints/2026-10-01-reviewed-reconciliation.md:140`).
- **Blueprint consolidation plan:** none is declared. A grep across the hub and child repos (excluding archives and worktrees) for blueprint consolidation, builder, packager, importer, or blueprint-into-package found nothing. The nearest statements are:
  - "Upstream extraction has newer reviewed behavior requiring a bounded promotion" (`governance/checkpoints/2026-09-08-public-tooling-review.md:20`).
  - Execution-order step 7, "Continue bundle/extraction cleanup… without forking upstream knowledge or contracts" (`ECOSYSTEM.md:1119-1120`).

## 3. Planning and recommendation docs (evidence)

- **`PLAN_2026-09-14_COURSECRAFT_DESKTOP.md`** (proposal; no repo exists):
  - "Build one CourseCraft application with two entry paths" (L14).
  - The owner table gives `coursecraft-desktop` the UI, projects and "tool adapters", and gives Workbench "extraction, normalization, domain authoring, scoring, validation, source identity, page compilation, and package semantics" (L38-39).
  - "desktop UI -> application commands -> per-tool adapter -> pinned producer CLI" (L90); "The interface should never drive terminal prompts or parse D2L XML itself" (L99).
  - Navigation keeps "Blueprint | Blueprint Wizard | Create course blueprint" (L126).
  - Component packaging is "Later supported package assembly. A review archive, Manage Files bundle, and Brightspace import package have different contracts" (L79).
  - "Extracted review models do not establish lossless whole-course authoring" (L72).
  - "The initial product scope excludes whole-course round-trip authoring, direct live LMS publishing" (L214).
  - Hall and runners keep "their existing presentation surfaces and releases; desktop can reuse reviewed patterns without absorbing their responsibilities" (L43).
- **`RECOMMENDATION_2026-07-19`** ("recommendation only, nothing authorized", L3-7):
  - Sibling-bundle pattern, with the wizard inside the bundle repo behind a "CLI-and-events-only boundary" (L178-186).
  - Hosted bench lights only after live receipts (L187-194).
  - Launcher decision "decided only when the third colleague-facing tool ships; default is thin-shell generalization of the stable launcher" (L528-534).
  - Standing constraints: "One-directional promotion; never a second parser/schema/builder… presentation layers never own truth" (L683-689).
- **Codex review (07-20):** accept the direction but revise the sequence; "Add hosted quiz or page benches only if the local/pilot workflows establish a real zero-install need" (L142-143); launcher architecture left trigger-gated (L274-276).
- **Logs and handoff:** nothing decides a blueprint-packaging host.
  - 09-08 log: Hall exposes Quiz Unbind only, "Hall does not expose Compose/Rebind" (L32), and item 4 schedules a Blueprint bundle/runner/Hall chain audit (L64-67).
  - 10-01 checkpoint: Blueprint runner held on a diverged topic branch (L217).
  - 08-22 handoff: coordination only.
- **Governance:** 33 promotion records, none about blueprint authoring or packaging; "A checkpoint is operational context, not authorization" (`governance/checkpoints/README.md:7`).

## 4. Catalog and Workshop Space (evidence)

- **Catalog:** "the **downstream consumer**… It reads versioned JSON produced by the blueprint pipeline; it **never parses D2L XML itself**" (`coursecraft-catalog/README.md:11-13`; `AGENTS.md:20-24`). It consumes `coursecraft.blueprint/4`, rubrics, and run/progress artifacts. It declares no packaging or build capability; grep of its README and ROADMAP found none.
- **Workshop Space:** a presentation layer with pinned producers. Blueprint Wizard "turns a Brightspace/D2L course export ZIP into a flat course blueprint" (`README.md:21-23`). The only package-producing door is Rubric Weave, which returns "a validated rubric-only import package"; "A build is not a Brightspace import" (L28-30, L87). Quiz "does not build or import a quiz package" (L50-51). There is no blueprint-to-package bench.

## 5. Upstream absorption rules and the quiz pattern (evidence)

**Absorption rules**

- "It does not mean that every useful or mature downstream implementation should be copied here… Distill the reusable behavior rather than copying a downstream product wholesale" (`UPSTREAM_FIRST_DEVELOPMENT_WORKFLOW.md:12-32`).
- Order of work: upstream edit, verify, merge, then refresh share bundles in a separate commit (L56-128).
- Scripts enter master only when course constants are removed, inputs and outputs are documented, raw evidence is safe, joins are visible, a test or smoke note exists, and failures produce diagnostics (`REUSABLE_PATTERN_TRANSFER_CRITERIA.md:40-52`).
- "Separate referenced repo | The work is becoming a colleague-facing product or library" (L24).
- "Reference, do not absorb, when scope is product-like" (`MASTER_WORKBENCH_CONTINUITY_RECOMMENDATIONS_2026-06-12.md:108-111`).
- "keep this master as the package/tooling/standards spine" (L165).
- "Delay a `src/coursecraft_workbench/` refactor until field checks land" (L61-64).

**Quiz consolidation pattern** (workbench `plans/2026-07-15_quiz_tooling_consolidation_and_ecosystem_sequence.md`): "consolidated in `coursecraft_workbench` before a new quiz wizard, hosted surface, catalog integration, or other downstream product is built" (L16-20).

- Phase 0: provenance freeze and inventory.
- Phase 1: capability and corpus matrix.
- Phase 2: contract family and identity (`coursecraft.quiz/1`, `quiz_run/1`, `quiz_settings/1`), "a small related contract family, not one enormous closed record".
- Phase 3: consolidated extraction and normalization.
- Phase 4: builder, validator and differ alignment, plus the capability registry.
- Phase 4.5: readiness and stewardship.
- Phase 5: live Brightspace round trips, a separate operator authorization.
- Phase 6: promotion and product surfaces — "a quiz wizard or shared launcher as a presentation/orchestration layer, not a new parser or schema owner" (L319-340).
- Product boundary: "Schema validity is not buildability. Extraction support is not import support." (`docs/project/quiz-consolidation/QUIZ_BINDER_EVIDENCE_AND_PRODUCT_BOUNDARY_2026-07-20.md:191-192`). One service, two entry paths, one canonical contract (L218-226).
- Repo boundary: the bundle "owns the portable producer, release identity, and terminal Quiz Wizard/TUI"; Workbench "remains the upstream owner of quiz contracts, normalization semantics, capability evidence" (`ECOSYSTEM.md:666-674`).

**`docs/project/quiz-consolidation/` contents:** the phase records (0/1, 2, 3, 4, 4.5); the surface audit (md + json); the archive successor-pointer audit; the product-boundary note; and September adoption records (assessment review packets, deterministic draft and Word intake, optional review metadata, question-type adoption review and closure, math/review fidelity plan and evidence, projection fidelity gates, Reading Room image preview candidate).

## Inference (mine, not declared)

- A flat-blueprint -> package -> import capability is generative, so the Blueprint Bundle's current charter does not cover it. The declared pattern points to Workbench as semantic owner, extending `d2l_package_lib` and the component contract, then either a new sibling producer bundle or a deliberate, recorded charter change with a promotion record.
- Blueprint Wizard and Workshop Hall are presentation layers. They can host such a capability only through a released producer and an exact pin; neither may own the logic. Desktop is a proposal that explicitly excludes whole-course round-trip authoring for now.
- "Import" in every released surface stops at a validated package plus a manual operator import. No doc authorizes automated live import.
- The rubric Weave lineage (PR-2026-915: Workbench, then bundle, then runner and Hall) is the closest completed precedent for an authoring/packaging capability.

## Declared facts most relevant to deciding the upstream owner and the downstream host for blueprint -> Brightspace packaging

1. Workbench owns "general-purpose transformations", schemas and "package semantics"; generic component packaging already lives there and is live-import verified (`ECOSYSTEM.md:131-135`; Desktop plan L39; `DEVELOPMENT_ROADMAP.md:841-844`).
2. Blueprint Bundle is chartered as "extraction and review, not instructional-content generation", and that charter was the stated reason quiz building became a sibling bundle (bundle `AGENTS.md:32`; `RECOMMENDATION_2026-07-19:154-160`).
3. Blueprint Wizard, Workshop Hall and Catalog are consumers that must not parse D2L XML or own semantics; a lit bench needs a reviewed producer release plus an exact pin (`ECOSYSTEM.md:54-57, 88-89`).
4. Cross-repo movement or an ownership change requires a promotion record with one of six dispositions; downstream forks stay local unless distilled (`ECOSYSTEM.md:137-176`; PR-2026-918/919 as worked examples).
5. The quiz pattern is to consolidate upstream first (inventory, contract family, builder/validator/differ, live round trips), then promote to products (quiz plan L16-20, L189-340).
6. Whole-course build/import ("Course Foundry") is named but deliberately unopened and trigger-gated; Desktop excludes whole-course round-trip authoring and live LMS publishing (`RECOMMENDATION_2026-07-25:99-114`; Desktop plan L214).
7. The multi-tool host is undecided: launcher/hub is an open variable (`ECOSYSTEM.md:1189-1190`), Desktop is a proposal with no repo, and Hall is the only deployed multi-bench shell.
8. No blueprint consolidation plan or blueprint-to-package builder is declared anywhere in the hub or child repos.
9. Ground rule: "Prefer small element bundles over whole-course builds" (`VERIFIED_WORKFLOWS.md:763`).

One side note for anyone committing in these repos: `coursecraft-catalog/AGENTS.md:110` says "Never add Co-Authored-By trailers", and `RECOMMENDATION_2026-07-19:693-694` lists "no AI co-author trailers" as a standing constraint.
