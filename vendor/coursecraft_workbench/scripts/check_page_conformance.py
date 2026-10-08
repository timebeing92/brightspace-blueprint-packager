#!/usr/bin/env python3
"""Check compiled Brightspace HTML topics against the CourseCraft page gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from page_kit import check_html_conformance


def _html_paths(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted(path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in {".html", ".htm"})
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Compiled HTML file or directory")
    parser.add_argument("--mode", required=True, choices=("review", "learner"))
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    source = args.source.expanduser().resolve()
    paths = _html_paths(source)
    if not paths:
        print(f"error: no HTML files found at {source}", file=sys.stderr)
        return 2
    diagnostics = []
    counter = 0
    for path in paths:
        page_id = path.stem
        for row in check_html_conformance(path.read_text(encoding="utf-8"), mode=args.mode, page_id=page_id):
            counter += 1
            item = dict(row)
            item["id"] = f"diag-{counter:04d}"
            item["extensions"] = {**item.get("extensions", {}), "source_file": path.name}
            diagnostics.append(item)
    errors = [row for row in diagnostics if row["severity"] == "error"]
    report = {
        "schema": "coursecraft.page_conformance/1",
        "mode": args.mode,
        "status": "fail" if errors else ("pass_with_warnings" if diagnostics else "pass"),
        "files": [path.name for path in paths],
        "diagnostics": diagnostics,
        "extensions": {"live_brightspace_operations": "not_performed"},
    }
    output = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.json_output:
        target = args.json_output.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
    print(output, end="")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
