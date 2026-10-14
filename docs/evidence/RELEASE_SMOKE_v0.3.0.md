# Release smoke test: v0.3.0

Result: **passed**. Started 2026-10-14T01:34:36Z, finished 2026-10-14T01:35:29Z, on macOS-26.6.2-arm64-arm-64bit-Mach-O (driver Python 3.14.5, venv Python 3.14.5).

Asset `brightspace-blueprint-packager-v0.3.0.zip`: 780,217 bytes, SHA-256 `c1f94ac611f202ddaa8dadae8f81948ac4da59188a7565371c06110a19d8161b`.
Manifest: version 0.3.0, tag v0.3.0, commit `824fc1f0a5059fe444877b77e44504e5c15f3104`, 166 files, vendored Workbench `1f48e070ee28c50c8def9ed8707bb70bb264517d`.
Ready course: package `package.zip` SHA-256 `0d6b64e4ac18c2626d675de8607b6e14c7b160d25f9cca4e24d6e129d89c32be`; verify:   [passed] Blueprint Wizard QA finds no unclassified breaks: 0 findings; 0 expected generated page-chrome exclusions; 0 unclassified breaks; 0 broken relative references
Wizard cycle: converted; verify:   [passed] Blueprint Wizard QA finds no unclassified breaks: 0 findings; 0 expected generated page-chrome exclusions; 0 unclassified breaks; 0 broken relative references
Shipped suite: 205 passed, 1 skipped in 38.56s

| Step | Result | Seconds |
| --- | --- | --- |
| release view | ok | 0.4 |
| exactly one ZIP asset and its sidecar | ok |  |
| download brightspace-blueprint-packager-v0.3.0.zip | ok | 1.1 |
| download brightspace-blueprint-packager-v0.3.0.zip.sha256 | ok | 0.8 |
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
| verify the ready course | ok | 1.3 |
| vendored Wizard extracts the package | ok | 1.0 |
| from-wizard | ok | 0.2 |
| conversion status | ok |  |
| read the converted blueprint | ok | 0.1 |
| build the converted blueprint | ok | 0.2 |
| verify the converted blueprint | ok | 1.3 |
| install the dev requirements | ok | 0.9 |
| shipped suite | ok | 39.0 |
| suite summary | ok |  |
