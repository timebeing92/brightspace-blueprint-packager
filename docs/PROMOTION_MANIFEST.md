# Promotion manifest: what moves where, and how to tell

Date: 2026-10-06. The owner's direction: the Blueprint Wizard fixes land on a
branch of the wizard's source; the new tooling stays in this repository until
promotion. This file is the documentation that makes a later move safe.

## Three kinds of material in this repository

| Kind | Lives at | Goes to | Depends on |
|---|---|---|---|
| The packager | `tools/blueprint-packager/` | a new sibling producer in CourseCraft, Blueprint Wizard as the likely front door | Workbench `scripts/d2l_package_lib.py` and `scripts/rubric_package_lib.py`, byte-identical to upstream `9d3a620`; the Workbench readers for verification |
| Wizard fixes | `candidate/blueprint_wizard_structure/` | on Workbench branch `fix/blueprint-structure-fidelity` (four commits and counting; not merged); a bundle refresh follows the merge | Workbench at `9d3a620` |
| MBA 620 course work | `workspace/design/mba_620/`, `workspace/review/mba_620/`, `workspace/generated/…/mba_620_*` | stays here | the tool, at the version recorded in each build receipt |

Course text never leaves the course lanes. Tests in the tool use synthetic
fixtures only.

## The packager, file by file

| Path | Role | Moves |
|---|---|---|
| `bpk.py` | command line | yes |
| `blueprint_packager/*.py` | the tool | yes |
| `blueprint_packager/templates/bumk515_classic/` | one page template, lifted from a UNE shell | yes, as the first template; a kit registry is the intended replacement |
| `tests/` | synthetic tests | yes |
| `docs/DESIGN.md`, `docs/AUTHORING_GUIDE.md`, this file | design and authoring contract | yes |
| `AGENTS.md`, `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `CAPABILITIES.json` | boundary, use, history, plan, evidence | yes |

Contracts the tool defines, all `blueprint_packager.*/0.1`: course map, course
model, run receipt, paragraph ledger, fidelity report, verification report,
build settings, object map, map rebase. At promotion each needs a Workbench
name; the design document proposes `coursecraft.blueprint_authoring/1` for the
course model. The run receipt follows `coursecraft.run/1` field names; upstream
now writes `run/2`, whose lineage key needs an answer for packages that have no
org unit yet.

## Behavior that belongs upstream once proven

Each is a local extension of the Workbench component library, listed in every
build receipt under `beyond_workbench_library`:

1. more than one discussion forum in a package;
2. rubric association on discussion topics;
3. hidden modules and topics;
4. external link topics;
5. one page placed in two modules;
6. a quiz carried forward from a source export;
7. a due date on a carried quiz in Brightspace's nested timestamp form.

Each becomes a promotion candidate for `d2l_package_lib` after it survives an
import and a re-export comparison. None has yet.

## Records that should travel with the tool

`workspace/review/mba_620/blueprint_packager_records_2026-10-06/` holds the
seven survey reports, the producer-conventions summary, and an index of every
decision, log, and review document produced while the tool was built. The
owner asked that these come into CourseCraft as a record at promotion.

## Where the commits are, 2026-10-06

| Repository | Branch | What |
|---|---|---|
| this one | `tool/blueprint-packager` | three commits: the packager, the wizard candidate, the ownership notes and records packet |
| this one | `master` | the tool branch plus two course commits: September intake and reviews; the 2026-10-06 build and reviews |
| CourseCraft Workbench | `fix/blueprint-structure-fidelity` | `f6a28fb` the first fix set; `a92a3ab` one-to-one headings; `a0f3195` model /5; `a80af3f` bracket panels; `79bceaa` empty panels as pairs; `d05aa9a` headings inside descriptions (loss 17); `483441c` internal links as brackets. Pushed into the local Workbench, not to GitHub. Not merged |

This repository has a private GitHub remote as of 2026-10-06 night, with both
branches pushed. The Workbench branch and the two backlog notes are local only.
The owner intends a repository of its own for the packager; the tool branch is
the seed, and the only personal material on it is machine paths in the survey
reports, which a split would rewrite.

## How to tell it was applied correctly

- The tool's tests pass in the new home.
- A build of the MBA 620 model from this repository's course map, with the
  same settings, produces a ZIP with SHA-256
  `d764fc939bd9dbdcd780419cd3063c9bd9a46db6fe8a497377743073ea271ef3`.
- The candidate patch applies to the wizard branch with `git apply --check`
  and its 22 tests pass there.
- The MBA 620 verification reports in the build folder are reproduced by the
  moved tool.

## Where things stand, 2026-10-08

The packager lives in its own repository, `brightspace-blueprint-packager`,
with the Workbench scripts it builds on vendored at `2c967f9` and a drift
check. The Blueprint Wizard fixes are now Workbench pull request #5
(https://github.com/timebeing92/coursecraft-workbench/pull/5), eight commits
on `fix/blueprint-structure-fidelity`; the `candidate/` folder that carried
them as patches stays in the MBA 620 course repository as the record. The
MBA 620 course map, build settings, package, and the frozen copy of this tool
that built it stay in that course repository.

