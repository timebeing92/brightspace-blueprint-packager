# Producer conventions and consolidation thinking: summary and how it was applied

Date: 2026-10-06. The full report is
`survey_reports/06_producer_conventions_and_consolidation_thinking.md`. This
summary gives its findings, the reasoning behind each, and what the blueprint
packager did with it.

## What the report set out to answer

A new tool was being written in a course build. The intent is to promote it
later as a sibling producer with Blueprint Wizard as its front door. The
question was what the ecosystem already expects of a producer, so the tool
could be written now in a way that makes that promotion cheap.

It read the rubric and quiz bundles and their runners, the blueprint bundle's
progress and receipt contracts, the hub's recommendation, review, and commission
documents from July through September, the quiz consolidation plan, the page
template surfaces, and the frontend design bundle.

## Five findings that changed the build

| # | Finding | Reasoning in the source documents | What the tool did |
|---|---|---|---|
| 1 | The Workbench already has a page compiler and page packager, Page Kit. | The hub's standing rule is "never a second parser/schema/builder". A second page compiler would be a parallel owner of the same truth. | Rendering sits behind a narrow adapter. The built-in renderer exists because MBA 620 was to use the original BUMK 515 pages, which Page Kit's fixed markup cannot reproduce without a kit. Convergence on Page Kit is the recorded direction. |
| 2 | A course-build renderer has been promoted upstream before. | Promotion record PR-2026-918 took the RCORP module-page renderer from a course build into the Workbench as a new capability, by re-expressing it, not copying it. | The tool is organized so each stage can be re-expressed upstream on its own. The ownership notes propose a disposition per piece. |
| 3 | The authoring contract must be separate from `coursecraft.blueprint/4`. | That schema describes what was extracted from an export and is closed to extra fields. The rubric work drew the same line: an extraction record enters authoring only through a strict adapter. | The course model is its own contract. Nothing writes into `coursecraft.blueprint/4`. A suggested upstream name is `coursecraft.blueprint_authoring/1`. |
| 4 | The progress contract's list of output keys is closed, and one unreviewed extension is still an open defect. | Rubric Weave added six keys without review and the parity check has failed since. | The tool emits no progress events yet. Adding them is a roadmap item that must not add output keys on its own. |
| 5 | Whole-course build and import already has a name and a gate: "Course Foundry", "do not open this frame yet". | The July 25 recommendation wanted two catalog layer domains, one proven edge type, and a verified rubric import first, because live import is where privacy and tenant risk bind hardest. | The operator opened the frame for the blueprint lane on 2026-10-06. The notes record that the hub's trigger wording should be revisited to match. |

## Conventions, and where the tool stands on each

| Convention | Why the ecosystem has it | Status in the tool |
|---|---|---|
| CLI: positional source, `--output-dir`, `--label`, `--force`; exit 0, 1, 2, 130 | Runners wrap producers by command line and must rely on stable flags and exit meanings | Adopted |
| `--preflight` and `--progress-events` | A runner needs a plan-only run and live step events | Not yet; on the roadmap |
| Run receipt in the `coursecraft.run/1` shape | Every artifact is hashed so a consumer can refuse a tampered or mismatched bundle | Field names adopted under the tool's own schema id. Not validated against `run/1`, whose source block describes an export, not a document |
| Component package receipt | Records codes, files, and the ZIP so a re-export can be joined by resource code | Adopted and schema-valid |
| Fixed base resource code, byte-stable ZIP, transactional output | Reproducible builds; a failed build never leaves a half-written folder | Adopted, with a double-build equality test |
| Identity keys, identity quality, relationship records | Joins and objects must say how well they are identified, not just that they matched | Adopted for built objects and joins. Authored objects are marked as title-based fallback identity |
| Diagnostic record with id, code, severity, message, location, remediation | Unresolved things stay visible as data | Adopted. Severity words are info, warning, error |
| Evidence ladder L0 to L5; never "importable" or "verified" without a level | Schema validity is not buildability, and local validation is not import evidence | Adopted. Everything is labelled L1 and "not imported". `CAPABILITIES.json` names the best evidence per shape |
| Capability registry | States what may be built and claimed; unknown shapes are refused | Adopted as `CAPABILITIES.json` |
| Authoring contract distinct from the extracted one | See finding 3 | Adopted |
| Source bound by fingerprint | A decision made about one file must not be applied to another | Adopted. A course map refuses a file with a different SHA-256 |
| Live work needs a runbook, an object prefix, and an append-only ledger | Live objects must be findable and removable by exact identity | Runbook written. Prefix is optional and unset for the sandbox. The ledger entry follows the first import |
| Synthetic fixtures only; no machine paths or course text in receipts | Privacy, and portability of evidence | Tests are synthetic. The tool's receipts carry relative paths. The wizard's own read-back bundle inside the build folder does contain absolute paths |
| No assistant-authorship notes in bundles or source; no AI co-author commit trailers | Standing constraint in the hub recommendation and two repos' agent files | Nothing was committed. No such notes were added to tool source |
| Promotion-ready repository contents | A new bundle needs a charter, roadmap, changelog, tests, and pinned upstream hashes | README, boundary file, roadmap, changelog, and tests exist. Upstream file hashes are recorded in each build receipt. No promotion record has been drafted |

## The consolidation thinking, in brief

The quiz consolidation set the pattern, and the report distilled it:

- **Consolidate upstream before building product surfaces.** Inventory what exists, then build a capability matrix, then contracts and identity, then extraction, then builder with validator and differ, then live round trips, then promotion.
- **A small family of related contracts, not one large closed record.** Keep absent, unknown, not applicable, unresolved, and unsupported distinct.
- **A capability registry is not a data contract.** Being able to represent a shape never means the builder supports it.
- **Treat the vocabulary and shared model as the contract, not a file format.** A Word file is preserved source entering a visible translation step.
- **Plain language carries state, evidence, risk, and proof.** Naming and metaphor may carry welcome and orientation only.

Two corrections on record shaped how this work was paced:

- The July recommendation's own adversarial pass removed a hosted lane that came before live evidence, and removed an invented quotation.
- The review that followed pushed back on putting new contracts and governance work on the critical path before live evidence, warned about too many prose documents each claiming authority, and asked for a pilot after a minimum working pipeline. It also noted that gates catch conformance defects and cannot settle composition, hierarchy, or tone.

Applied here: the tool was built to a working pipeline first, on one real course, and the next step is a sandbox import, not more contract work.

## Page and template surfaces

Three families exist today:

1. **Hand-authored page templates** in the Workbench reference lane: week overview, lesson, welcome, project landing, with a shared stylesheet and snippets for activity descriptions.
2. **The design kit**, staged in the Workbench and preserved in the frontend design bundle: element libraries and styled page templates. Its ZIP is a Manage Files folder, not an import package.
3. **Page Kit**, the only one with a machine manifest: page types, required slots, allowed blocks, colour tokens, and lifecycle rules.

There is no registry of kits. Selection is whichever kit and stylesheet are
passed on the command line. Editor fields strip style blocks and classes, so
activity descriptions need inline styles. That last constraint is why this tool
renders two surfaces.

The report's inference, which the design adopts: "a selection of templates"
maps to a directory of kits chosen by id, and the planned Pagewrights' Guild
surface is the frontend design bundle.

## Tensions for the owner

1. **Rubric attachment.** Rubric Loom treats attaching a rubric to an activity as a manual step. The component library can join a rubric to an assignment folder, and this tool also joins rubrics to discussion topics. The catalog layers proposal wants attachment recorded as an edge with its own evidence level. These need one answer.
2. **Second page builder.** The built-in renderer is a deliberate, temporary exception to the one-builder rule.
3. **The Course Foundry gate.** Opened in practice; the hub document still says not to.
4. **Commit trailers.** The hub's standing constraint is no AI co-author trailers. Confirm before any commit in ecosystem repositories.

## What the report did not cover

It did not read part of `ECOSYSTEM.md` (lines 433 to 958), parts of two
commission documents, the interactives bundle, or the private quiz bundle's
documents. It did not test whether Page Kit's markup can reproduce the BUMK 515
pages; that is stated as an inference.

## Checks made on the report

Read first-hand after the report arrived: the "never a second
parser/schema/builder" and "no AI co-author trailers" passages, the sibling
bundle decision and its reasoning, the Course Foundry passage, and the evidence
ladder with Receipts 3, 5, and 9. All matched.
