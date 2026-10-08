# Vendored CourseCraft Workbench

A read-only mirror of the Workbench scripts and schema files the packager imports or runs, at the commit named in `MANIFEST.json`. Never edit these files here; run `python3 scripts/check_vendor_drift.py <workbench checkout>` to see drift, and `--commit <sha>` to re-pin from upstream.
