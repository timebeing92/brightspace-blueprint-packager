# Second opinion: the package read by current upstream tooling

Date: 2026-10-06. Read-only use of the upstream Workbench at commit `9d3a620`.

This fork's Workbench scripts are 77 commits behind upstream. The conformance
gate and the wizard pipeline are both newer there, so the sandbox package is
also checked with the upstream versions.

## Current result

The package rebuilt at about 19:00 UTC, after the title, points, and Week 5
changes, was read with upstream's scripts through the packager's own option:

```bash
.venv/bin/python -B tools/blueprint-packager/bpk.py verify BUILD_DIR --model MODEL.json \
  --workbench-scripts "/path/to/coursecraft_workbench/scripts" --label upstream
```

| Reader | Result |
|---|---|
| Upstream conformance gate | Conformant. 0 errors, 0 warnings |
| Upstream wizard pipeline on the package ZIP | Exit 0 |
| Joins | 50 traced, 0 unresolved |
| Activities, gradebook, rubrics, paragraphs, checklists | all match the course model |
| Wizard QA | 0 breaks |

All ten checks pass, with the same counts as this fork's readers. The report is
`verification_report__upstream.md` in the build folder. This is still L1
evidence.

## Earlier result and a correction

The first package of the day was checked the same way by hand, with the same
outcome. That check was recorded here as changing nothing upstream. It did
leave four Python bytecode cache files in upstream's ignored
`scripts/__pycache__/` folder. No tracked file changed. The four files were
removed, and the packager now runs its readers with bytecode writing switched
off. After the current check, no file in the upstream checkout carries today's
date.

What the gap means for the build is written up in
`../fork_drift_2026-10-06/IMPACT_ON_THE_BLUEPRINT_BUILD.md`.
