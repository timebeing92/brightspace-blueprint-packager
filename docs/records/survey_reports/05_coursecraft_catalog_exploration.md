# coursecraft-catalog: what a blueprint parser/packager can reuse

All work was read-only; the live DB was opened with `sqlite3 -readonly`.

Path shorthand:
- CAT = `~/Documents/D2l & Coursebuilding Tools /coursecraft-catalog`
- WB = `~/Documents/D2l & Coursebuilding Tools /coursecraft_workbench`
- REC = `~/Documents/D2l & Coursebuilding Tools /RECOMMENDATION_2026-07-25_CATALOG_COURSE_LAYERS.md`
- PLAN = `WB/plans/2026-07-12_course_component_catalog_pipeline_plan.md`
- FORK = `~/Documents/MBA_620_Marketing_Major_Edit_Fall2026`

## Headline

- **The catalog is an extracted-facts consumer only.** No "authored layer", `course_layers` contract, or Foundry exists in its code, schemas or docs (grep of CAT and `ECOSYSTEM.md` found nothing). That idea lives only in REC, which says it "commissions nothing" (REC:3-5).
- **The most reusable engineering is upstream of the catalog.** The identity and receipt code is `WB/scripts/course_artifact_contracts.py`. FORK already has an older copy (20,790 bytes, Aug 17, run/1 only) against upstream's 25,757 bytes (Sep 25, adds run/2).
- **Align on record shapes now; do not couple.** The catalog cannot ingest the new tool's outputs today, and several recorded decisions argue against wiring it in yet.

## 1. What the catalog is (evidence)

- **Role.** "the downstream consumer… reads versioned JSON… never parses D2L XML itself" (CAT/README.md:11-13; AGENTS.md:20-24).
- **Storage.** One SQLite file `catalog.db` (WAL, FTS5), schema v12 (`PRAGMA user_version` = 12), 12 checksum-ledgered migrations in `catalog/migrations/`. Live counts: 60 offerings, 6,192 components, 572 modules, 1,001 grade items, 434 rubrics, 702 component-rubric links, 358 relations, 0 `component_lineage` rows.
- **Inputs** (one bundle directory; `catalog/ingest.py:7-14, 412-423`):
  - `*__course_activities.json` (`coursecraft.activities/1`)
  - `*__course_structure.json` (`coursecraft.structure/1`)
  - `*__blueprint.json` (`coursecraft.blueprint/4`)
  - optional `*__rubrics.json` (`coursecraft.rubrics/1`) and `*__course_qa.json`
  - `*__run_identity.json` (`coursecraft.run/1` or `/2`)
  - Pinned contract table: README.md:65-81.
- **Entry points** (README.md:97-122):
  - Intake: `catalog/migrate.py`, `ingest.py`, `refresh.py` (classifier), `coverage.py`, `versions.py`, `source_lineage.py`, `provenance.py`, `catalog_wizard.py` (Archivist), `catalog_batch.py`.
  - Annotation: `tagger.py`, `relate.py`, `curriculum.py`, `program_plans.py`.
  - Surfaces: `reader.py` (local web app, port 8060), `export_xlsx.py`, `snapshot.py`, `discovery.py`.
- **Outputs.** Reader pages, XLSX with a `Summary` receipt (README.md:601-604), `coursecraft.catalog_discovery_snapshot/2` JSON, append-only `registry.jsonl` (`coursecraft.catalog_registry/2`, ingest.py:1349-1387), relation truth sets.

## 2. Data model, identity, evidence vocabulary (evidence)

Core tables (`CAT/catalog/schema.sql`):
```sql
offerings(offering_id PK -- '<course_key>__<term-or-exportstamp>'   (120-127)
modules(module_id PK    -- '<offering_id>__m<position>'             (152-157)
components(component_id PK -- '<offering_id>__<kind>__<resource_code or slug>',
  module_id, placement, sequence_index, position_in_module, kind, title,
  resource_code, source_file, source_page, heading_level, points, grade_item_id,
  ..., content_hash, raw, parent_component_id, href, media_hint)    (161-197)
grade_items(grade_item_id PK -- '<offering_id>__<resource_code>')    (205-211)
rubrics(rubric_id PK -- '<offering_id>__<d2l numeric id>')           (213-218)
component_rubrics(component_id, rubric_id)  -- M:N                   (229-233)
component_relations(from_component, to_component, relation,
  assigned_by -- structural:quicklink | structural:condition_set |
              -- rule:<rule_id> | human:<who> | model:<name>
  confidence, evidence, created_at)                                  (271-282)
component_placements(placement_id, component_id, module_id, sequence_index,
  position_in_module, path, is_hidden, evidence_source)              (562-571)
diagnostics(offering_id, source, severity, message)                  (245-248)
```

Identity:
- **Catalog keys** are readable natural keys: `ident = resource_code or id_hint or slug(title)` (ingest.py:311-313). Collisions get a `--N` suffix plus a diagnostic (353-364). Rubric children are `__c01`, `__l01` (997, 1009).
- **Upstream keys** are hashes: `cc:{prefix}:{sha256([parts])[:32]}` (WB course_artifact_contracts.py:58-60). An entity key hashes `[source_lineage_key, entity_kind, basis, value]` (301-303).
- **Identity quality** is explicit: `durable_source_id | scoped_source_id | observed_reference | fallback | unresolved` (CAT/schemas/activities_schema.json:69).
- **Source identity** is `source_instance_key = cc:source:<logical digest>` plus a `source_lineage_key` (CAT/catalog/run_identity.py:67-100).
- **Course aliases** carry evidence: `course_code_aliases` (schema.sql:89-96).

Joins:
- Activity to grade item: by `grade_item_code` to `resource_code` (ingest.py:708, 765).
- Activity to rubric: by numeric rubric id; a miss becomes a diagnostic (ingest.py:1017-1024).
- Object to module: by manifest `rcode` (ingest.py:168-233, 673-689).
- Page section to module: by normalized title. "Never guess if several modules normalize to the same title" (ingest.py:662-671).
- Containment: `parent_component_id` (schema.sql:191-193).
- Structural relations: `references` from `rCode=` hrefs (1029-1035) and `release_condition` (1037-1056).
- Reader edge names: `placed_in`, `belongs_to`, `graded_by`, `assessed_by`, `collected_in` (views.sql:1312, 1330, 1364, 1382, 1401).

Fact versus annotation:
- "extracted FACTS and human/rule/model ANNOTATIONS never share a table" (schema.sql:4-6).
- Human annotations are never machine-modified (AGENTS.md:27-31).
- Review state is `extracted | provisional | confirmed | rejected` (schema.sql:447-448).
- Placement basis is `structure_json | component_primary_placement | section_week_key_unique_module` (discovery.py:223-236).
- Front-matter evidence role is `package_local_export` or `supplemental_linked_syllabus` (ingest.py:745-747).

## 3. Intake discipline (evidence)

- **Schema pinning.** "schema {declared!r} is not the pinned {expected!r} — refusing to ingest" (ingest.py:155-162). Legacy unversioned activities and structure files are still read, with a provenance diagnostic (428-441, 629-636).
- **Receipt verification** (`run_identity.py:103-150`) refuses:
  - an unknown run schema;
  - a contract checksum that differs from the vendored schema bytes (117-127);
  - symlinked or escaping artifact paths (56-64);
  - a missing artifact or sha256 mismatch (129-139);
  - a payload whose `run_id` or `source` differs from the receipt (140-150).
  - Contract ids the catalog does not know are skipped, not refused (119-121).
- **Classification** is `new | refreshed | duplicate | ambiguous`, with `safe_to_ingest` (refresh.py:100-124, 142-240).
  - Duplicate is a no-op (ingest.py:508-515).
  - Receipt-bearing lineage conflicts cannot be overridden (577-594).
  - Lineage equivalence comes only from an append-only `human:` record (schema.sql:99-116).
- **Coverage gate.** Any loss holds a refresh until `--accept-coverage-loss`; accepted losses become `ingest:coverage` diagnostics (refresh.py:288-303; ingest.py:616-628).
- **Atomicity.** One transaction per offering. An annotation that would be orphaned raises and rolls everything back (ingest.py:1069, 1295-1344).
- **Privacy.** `intake/`, `catalog.db`, `backups/`, `reports/` are gitignored (CAT/.gitignore). Batch sources must stay inside the inbox, with no symlinks (batch.py:241-254). Shared output "withholds rather than omits" (AGENTS.md:74-86; snapshot.py:41-44).
- **CI.** `cmp` of every vendored schema against a pinned producer SHA (`.github/workflows/ci.yml:22, 33-41`).

## 4. Diff, lineage, layers

Evidence:
- **Run-over-run diff.** `offering_versions.change_summary` (schema.sql:132-149), built by `versions.change_summary` as `{"added","removed","changed","counts":{…,"unchanged"}}` keyed by component id and content hash (versions.py:53-71).
- **Content hash** is `sha256(json.dumps(row, sort_keys=True))` over the whole row (ingest.py:132-133, 973-975).
- **Known defect in that design.** "Of 708 changed existing component hashes, 664 differ only in raw `identity.source_lineage_key` and `entity_key`… Do not report 708 authored-content changes" (CAT/docs/implementation/2026-09-25-run2-reextraction-rehearsal.md:80-87).
- **Cross-offering lineage is unbuilt.** Tables exist (schema.sql:360-375) with 0 rows; the planned `lineage.py` (PLAN:272) is absent. The planned ladder is exact = `course_key + resource_code + kind`, probable = normalized title, manual (PLAN:799-803).
- **Resource codes survive import and re-export**: "codes survive Brightspace import/re-export (basis for lineage matching)" (PLAN:117-118).

What REC proposes:
- **Layer** = "one domain's validated contract document about one course, plus provenance", with fields `domain`, `contract`, `provenance` (extracted or authored), `run`, and "Edges between layers as first-class evidence" (REC:40-56). "Producers stay layer-blind… The catalog composes" (58-60).
- **Sequence.** L0 `coursecraft.course_layers/1` or an extension of `curriculum_evidence/1`; L1 rubric-layer intake pilot; L2 rubric-to-activity attachment edges "with evidence levels"; L3 quiz layer; then Reader layer-stack views (76-97).
- **Course Foundry** is "the composition of layers run in reverse: authored layers built per domain, validated against the same contracts, assembled into an import package". The posture is "**do not open this frame yet.**" (99-108).
- **Trigger named:** "two layer domains ingested in the catalog + one edge type proven + Weave live-import verified" (109-111). Whole-course import "should inherit the admission protocol (W4) and the Phase-5-style operator windows" (111-114).
- **Open decisions:** L0's home; L1's timing against quiz intake; ratifying the trigger wording (116-123).

## 5. Patterns to reuse or align with

| Idea | Where | Example |
|---|---|---|
| Entity key + identity block per model object | WB `scripts/course_artifact_contracts.py:278-311`; CAT `schemas/activities_schema.json:64-92` | `"entity_key":"cc:entity:175b5c35…","identity":{"quality":"durable_source_id","basis":"resource_code","source_aliases":[{"kind":"resource_code","value":"CODE-A1"},{"kind":"id","value":"1"}]}` (CAT `tests/fixtures/bundle_produced_sample/sample_course__course_activities.json`) |
| Relationship record for joins | activities_schema.json:93-113; WB same file:341-378 | `{"source_kind":"dropbox_folder","source_code":"CODE-A1","join_type":"grade_item","target":"CODE-G-A1","resolved":"yes","source_entity_key":…,"target_entity_key":…,"relationship_key":"cc:relationship:…","identity":{"quality":"resolved_endpoints","duplicate_ordinal":0}}` |
| Unique-match-or-null rule | WB same file:354-365; ingest.py:662-671 | Endpoints resolve only on exactly one alias match; otherwise null with `partial_endpoints` or `evidence_only` |
| Run receipt | WB `build_run_identity` 564-602; CAT `schemas/run_identity_schema.json`; verifier `run_identity.py:103-150` | `emitted_files:[{"path","bytes","sha256","media_type","contract","extensions"}]`, `steps[]`, `contracts[]` with schema sha256 |
| Source fingerprints | WB same file:63-90, 229-237 | `"transport_fingerprint":{"algorithm":"sha256","digest":…,"scope":"transport_file","bytes":…}` |
| Package receipt | WB `workspace/reference/schemas/course/component_package_receipt_schema.json:6-18` (also in FORK) | required: `base_resource_code, deterministic, contract_sha256, codes, package_files, zip` |
| Structured diagnostics | WB `scripts/rubric_authoring.py:105-128`; catalog source namespaces at ingest.py:619-647 | `{"id":"diag-0001","code","severity","message","location","remediation","extensions"}` |
| Block-level provenance keys | ingest.py:253-264; `schemas/blueprint_schema.json:30-34` | `source_role, source_url, source_sha256, source_artifact, source_heading, extraction`; `meta` values must be strings |
| Immutable import by id + hash | `catalog/curriculum.py:326-337` | Same id and same hash is a no-op; same id with a different hash is refused |
| Evidence ladder | FORK `docs/IMPORT_TEST_LOG.md:21-24` | L1 join integrity, L2 shape plausibility, L3 imports, L4 round-trip diff |
| Fixtures and tamper tests | CAT `tests/fixtures/tiny_bundle/`, `bundle_produced_sample/`; `tests/test_bundle_produced_compatibility.py:36, 178, 188` | Modified artifact rejected; payload from another run rejected |

Inference (mine):
- **Source id.** The prototype's source-file SHA-256 is exactly a `transport_fingerprint`. Declare it in that shape.
- **Paragraph ledger.** Emit it as its own sidecar (for example `<label>__paragraph_ledger.json`) with a `schema` id, `run_id` and `source` block, listed in the receipt's `emitted_files` with `contract` set. Each row would hold source paragraph id, disposition, and target `entity_key`.
- **Why a sidecar.** `blueprint/4` is `additionalProperties:false` at root (blueprint_schema.json:8), so ledger data cannot ride inside it. Only string-valued block `meta` is open.
- **Title-text joins.** Keep exact-title joins, but record them as `identity.quality:"fallback"`, `basis:"title"`, with a relationship `quality`. Then a later move to resource-code joins is a basis change, not a redesign.
- **Dropdown to page.** The catalog has no such edge. Its analogue is containment (`parent_component_id`, edge `collected_in`), and `dropdown` is a block kind with nested blocks (blueprint_schema.json:26-29).
- **Two hashes per object.** Keep a content hash separate from an identity-and-provenance hash. This avoids the 664-of-708 noise the catalog hit.

## 6. Catalog as consumer, and the case against coupling

Evidence:
- **A parser-only bundle cannot be ingested today.** Ingest requires activities, structure and blueprint artifacts (ingest.py:413-421).
- **No authored provenance exists.** There is no `provenance` value for authored material and no L0 contract.
- **BUMK 515 is already in the catalog** as a legacy, receipt-less offering `BUMK-515__20267753` (org unit 102529; 9 assignments, 11 discussions, 2 quizzes, 19 grade items, 18 rubrics; no `run_provenance` row).

Arguments against coupling now:
- AGENTS.md hard rule 1 limits inputs to Blueprint-pipeline JSON (20-24).
- ROADMAP's 2026-07-17 decision is "provenance exchange without operational coupling: no sibling imports, path dependencies, shared mutable files" (CAT/ROADMAP.md:1091-1100).
- REC says "do not open this frame yet" and leaves L0's home undecided.

Inference:
- **Cheapest real path, no new contract:** import the package to a sandbox, re-export, run the Blueprint bundle, then ordinary ingest. This also serves the post-import comparison.
- **Limits of that path.** A sandbox is a different org unit, so it lands as a new offering. Component-level comparison with BUMK 515 would need the unbuilt lineage ladder. A legacy offering would also classify `ambiguous` on refresh.
- **Later authored-layer intake** would need: a run receipt, entity and relationship keys, structured diagnostics, hashed artifacts, and explicit `provenance: authored`.

## 7. Git state (CAT)

- Branch `main` at `3340d40`, 0 ahead and 0 behind `origin/main`; clean working tree; no stash.
- 14 other local branches, all 0 commits ahead of main (fully merged): `backup/reconciliation-20261001`, four `codex/*`, seven `fable/catalog-4-*`, `run-identity-refresh`, `sync-progress-partial-status`.
- 12 linked worktrees under `~/Documents/D2l & Coursebuilding Tools /.worktrees/coursecraft-catalog/` (two detached: `codex-verify-4-1-2`, `verify-codex-small-fixes`). None hold unmerged work.
- Last 12 commits:
```
3340d40 docs: clarify reviewed Catalog publication and current contracts
52ee892 docs: record run2 re-extraction rehearsal and pre-intake findings
be6040f chore: pin reviewed local run2 producer and record integration
f98ad20 feat: accept run2 receipts through explicit lineage transitions
d468758 Record verified architecture integration and live v12 activation
0ce21e7 Warn about placeholder course titles in Catalog health
9e9f1da Allow explicit options in the snapshot-history test helper
4563bf2 Test snapshot history behind the composed coverage gate
b09c378 Merge independently verified snapshot visibility search and projection repairs
6da41ca Merge independently verified coverage gate repairs
13892bb Repairs from Codex verification: R2 nested notices, R3 content hash, R4 term, R5 provisional relations
58b29cb Coverage gate on every fact-replacement path (Codex R1)
```

## Most useful things for the blueprint parser/packager

1. **Entity keys and identity quality on every model object.**
   - Where: `scripts/course_artifact_contracts.py` (`_scoped_key`, `add_entity_identity`), already in FORK.
   - How: mint `cc:entity:` keys per module, page, activity, rubric and grade item; keep the title as a `source_aliases` entry; label title-derived identity `fallback`.
   - Effort: small.
2. **Joins as relationship records with endpoint quality.**
   - Where: `annotate_activity_payload`, WB lines 341-378; `activities_schema.json:93-113`.
   - How: one record per join, covering activity to grade item, activity to rubric, and object to module. Use null endpoints and `partial_endpoints` instead of guessing.
   - Effort: small.
3. **A run receipt for every build.**
   - Where: `build_run_identity` and `verify_run_identity` in the same module; CAT `run_identity.py:103-150` as the consumer-side check.
   - How: emit `<label>__run_identity.json` hashing every output (ledger, model, package receipt) and every schema; refuse on mismatch before packaging.
   - Effort: small to medium.
4. **Deterministic resource codes plus the package receipt.**
   - Where: `component_package_receipt_schema.json` (FORK and WB).
   - How: fix `base_resource_code`, record the `codes` map, and carry codes as aliases on model objects. They are the join for the re-export diff and for future catalog lineage.
   - Effort: medium.
5. **Paragraph ledger as a versioned sidecar contract, not inside `blueprint/4`.**
   - Where: closed schema at `blueprint_schema.json:8`; the model to follow is the `curriculum_evidence/1` envelope (CAT `schemas/curriculum_evidence_schema.json`).
   - How: own schema id, `run_id`, transport fingerprint, rows pointing at `entity_key`.
   - Effort: medium.
6. **Structured diagnostics with namespaced sources.**
   - Where: `DiagnosticBag` (WB `scripts/rubric_authoring.py:105-128`); catalog `diagnostics.source` values.
   - How: `id/code/severity/message/location/remediation`; unresolved joins stay visible as data.
   - Effort: small.
7. **Separate content hash from identity hash, and reuse the change-summary shape.**
   - Where: `versions.py:53-71`; rehearsal finding 2.
   - How: use `added/removed/changed/unchanged` by key for model-versus-reader proof and the re-export comparison.
   - Effort: small.
8. **Refusal rules as tests.**
   - Where: CAT `tests/test_bundle_produced_compatibility.py`, `test_coverage.py`, `tests/fixtures/tiny_bundle/`.
   - How: copy the tamper, wrong-run and coverage-loss test patterns; adopt "loss holds until explicitly accepted" for normalization.
   - Effort: medium.
9. **Evidence ladder and provenance vocabulary.**
   - Where: FORK `docs/IMPORT_TEST_LOG.md:21-24`; `assigned_by` and `review_state` in schema.sql.
   - How: stamp outputs L1 to L4; mark each fact `extracted`, `authored` (the REC term) or inferred with `assigned_by`.
   - Effort: small.
10. **Defer catalog intake; use re-export, bundle, ingest for now.**
    - Where: REC:99-123; ROADMAP.md:1091-1100.
    - How: record the tool as a candidate authored-layer producer for the L0 decision; build no catalog-side code.
    - Effort: small now, large later.
