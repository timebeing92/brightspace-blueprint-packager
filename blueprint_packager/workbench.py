"""Where the CourseCraft Workbench scripts come from.

The packager builds on two Workbench libraries (d2l_package_lib,
rubric_package_lib) and verifies with the Workbench's readers. One rule decides
which copy is used, in this order:

1. an explicit path (``--workbench-scripts`` on the command line, the
   ``workbench_scripts`` build setting, or the ``BPK_WORKBENCH_SCRIPTS``
   environment variable);
2. the vendored mirror in this repository, ``vendor/coursecraft_workbench/scripts``,
   pinned at the commit named in its ``MANIFEST.json``;
3. the fork layout the tool was born in: a ``scripts/`` directory with
   ``d2l_package_lib.py`` above the settings file or above this package, so the
   frozen copy inside a course repository keeps working unchanged.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
VENDOR_DIR = REPO_DIR / "vendor" / "coursecraft_workbench"
VENDOR_SCRIPTS = VENDOR_DIR / "scripts"
MARKER = "d2l_package_lib.py"


class WorkbenchNotFound(FileNotFoundError):
    pass


def _fork_scripts(start: Path | None) -> Path | None:
    for base in [start, PACKAGE_DIR]:
        if base is None:
            continue
        for candidate in [base, *base.parents]:
            if (candidate / "scripts" / MARKER).is_file():
                return candidate / "scripts"
    return None


def scripts_dir(explicit: str | os.PathLike | None = None, start: Path | None = None) -> Path:
    """The directory holding the Workbench scripts to use. See the module docstring for the order."""
    chosen = explicit or os.environ.get("BPK_WORKBENCH_SCRIPTS")
    if chosen:
        path = Path(chosen).expanduser()
        if not path.is_absolute() and start is not None:
            path = (start / path).resolve()
        path = path.resolve()
        if not (path / MARKER).is_file():
            raise WorkbenchNotFound(f"No {MARKER} in {path}")
        return path
    if (VENDOR_SCRIPTS / MARKER).is_file():
        return VENDOR_SCRIPTS
    found = _fork_scripts(start)
    if found is None:
        raise WorkbenchNotFound(
            f"No Workbench scripts: none given, no vendored copy at {VENDOR_SCRIPTS}, and no scripts/{MARKER} above "
            f"{start or PACKAGE_DIR}. Pass --workbench-scripts or set BPK_WORKBENCH_SCRIPTS.")
    return found


def pinned_commit(scripts: Path) -> str | None:
    """The commit the vendored mirror is pinned at, when `scripts` is that mirror; else None."""
    manifest = scripts.parent / "MANIFEST.json"
    if manifest.is_file():
        try:
            return json.loads(manifest.read_text(encoding="utf-8")).get("commit")
        except (OSError, ValueError):
            return None
    return None


def describe(scripts: Path) -> dict[str, str | None]:
    """What the receipt and the verification report record about the scripts used."""
    source = "vendored" if scripts == VENDOR_SCRIPTS else ("explicit" if os.environ.get("BPK_WORKBENCH_SCRIPTS") else "checkout")
    return {"dir": str(scripts), "source": source, "pinned_commit": pinned_commit(scripts)}
