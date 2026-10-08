#!/usr/bin/env python3
"""Compile CourseCraft Page Kit contracts into review or learner HTML topics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from page_kit import DEFAULT_STYLESHEET, PageKitError, PublicationGateError, build_pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, type=Path, help="coursecraft.page_kit/1 JSON")
    parser.add_argument("--composition", required=True, type=Path, help="coursecraft.module_composition/1 JSON")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mode", required=True, choices=("review", "learner"))
    parser.add_argument("--stylesheet", type=Path, default=DEFAULT_STYLESHEET)
    parser.add_argument("--force", action="store_true", help="Transactionally replace an existing output directory")
    args = parser.parse_args(argv)
    try:
        result = build_pages(
            kit_path=args.kit.expanduser(),
            composition_path=args.composition.expanduser(),
            output_dir=args.output_dir.expanduser(),
            mode=args.mode,
            stylesheet_path=args.stylesheet.expanduser(),
            force=args.force,
        )
    except PublicationGateError as exc:
        print(
            json.dumps(
                {
                    "schema": "coursecraft.page_build_refusal/1",
                    "status": "publication_hold",
                    "message": str(exc),
                    "release_blockers": exc.diagnostics,
                    "extensions": {},
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except PageKitError as exc:
        print(
            json.dumps(
                {
                    "schema": "coursecraft.page_build_refusal/1",
                    "status": "error",
                    "message": str(exc),
                    "diagnostics": exc.diagnostics,
                    "extensions": {},
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print("VALID")
    print(f"output_dir={result['output_dir']}")
    print(f"page_count={result['page_count']}")
    print(f"publication_hold={str(result['publication_hold']).lower()}")
    print(f"release_blocker_count={result['release_blocker_count']}")
    print(f"build_receipt={result['build_receipt'].name}")
    print(f"run_receipt={result['run_receipt'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
