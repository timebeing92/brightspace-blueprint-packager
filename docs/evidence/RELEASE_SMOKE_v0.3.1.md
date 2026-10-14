# Release smoke test: v0.3.1

Result: **passed**. Started 2026-10-14T02:07:41Z, finished 2026-10-14T02:08:33Z, on macOS-26.6.2-arm64-arm-64bit-Mach-O (driver Python 3.14.5, venv Python 3.14.5).

Asset `brightspace-blueprint-packager-v0.3.1.zip`: 806,248 bytes, SHA-256 `566d9823d447c41e239d01547e32ab83904eeeb0621e0051de8f71822b7260b0`.
Manifest: version 0.3.1, tag v0.3.1, commit `4f95ff41cd542d967606c2713daffb07870de4d8`, 172 files, vendored Workbench `1f48e070ee28c50c8def9ed8707bb70bb264517d`.
Ready course: package `package.zip` SHA-256 `99786d6cfe582d6b84f25a48c68f669f1889d68f9845de116f4f7f5c2be290e9`; verify:   [passed] Blueprint Wizard QA finds no unclassified breaks: 0 findings; 0 expected generated page-chrome exclusions; 0 unclassified breaks; 0 broken relative references
Wizard cycle: converted; verify:   [passed] Blueprint Wizard QA finds no unclassified breaks: 0 findings; 0 expected generated page-chrome exclusions; 0 unclassified breaks; 0 broken relative references
Shipped suite: 211 passed, 1 skipped in 38.31s

| Step | Result | Seconds |
| --- | --- | --- |
| release view | ok | 0.6 |
| exactly one ZIP asset and its sidecar | ok |  |
| download brightspace-blueprint-packager-v0.3.1.zip | ok | 1.1 |
| download brightspace-blueprint-packager-v0.3.1.zip.sha256 | ok | 0.9 |
| sidecar matches the ZIP | ok |  |
| installer verified and installed | ok |  |
| shipped installer sees it installed | ok | 0.2 |
| shipped installer reports already_installed | ok |  |
| manifest names the verified tag for this version | ok |  |
| manifest commit is the tag's commit | ok |  |
| vendored Workbench pin recorded | ok |  |
| launcher --yes --doctor | ok | 4.8 |
| doctor reports the engine and the version | ok |  |
| launcher created the venv | ok |  |
| bpk.py --version | ok | 0.1 |
| bpk.py reports the version | ok |  |
| venv python version | ok | 0.1 |
| blank | ok | 0.2 |
| read the blank | ok | 0.1 |
| blank read writes a model and a readiness report | ok |  |
| synthetic ready course | ok | 0.1 |
| read the ready course | ok | 0.1 |
| build the ready course | ok | 0.2 |
| build wrote a package and its receipt | ok |  |
| run identity names the release commit | ok |  |
| verify the ready course | ok | 1.3 |
| vendored Wizard extracts the package | ok | 1.0 |
| from-wizard | ok | 0.2 |
| conversion status | ok |  |
| read the converted blueprint | ok | 0.1 |
| build the converted blueprint | ok | 0.2 |
| verify the converted blueprint | ok | 1.3 |
| install the dev requirements | ok | 0.9 |
| shipped suite | ok | 38.7 |
| suite summary | ok |  |
