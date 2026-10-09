#!/usr/bin/env python3
"""Splash screen: the pixel-art wizard delivering a course package into a monitor.

The scene is the same character grid the README's SVG is drawn from
(docs/assets/blueprint-packager-art.txt), rendered two pixel rows per terminal
line with the half-block trick: ``▀`` drawn with the upper pixel's colour as
foreground and the lower pixel's colour as background. Truecolor terminals get
the exact hex palette; others get the nearest 256-colour index. Pure stdlib;
anything that cannot animate (no TTY, --plain) gets a text banner instead.

The construction follows the Blueprint Wizard runner's scripts/art.py
(brightspace-blueprint-runner, commit 85cef27); the scene is this tool's own.
"""
from __future__ import annotations

import select
import sys
import time
from pathlib import Path

GRID_FILE = Path(__file__).resolve().parents[1] / "docs" / "assets" / "blueprint-packager-art.txt"

# Hex palette, shared with scripts/render_readme_art.py; '.' is transparent.
PALETTE_HEX = {
    "H": "#5f0087", "R": "#875faf", "S": "#ffd7af", "B": "#dadada", "E": "#14303e", "W": "#875f00",
    "G": "#ffd787", "K": "#af875f", "D": "#875f00", "F": "#54707e", "C": "#d7ffff", "V": "#174b5c",
    "L": "#5f5faf", "T": "#54707e", "M": "#b8d3de", "P": "#ffe9b8", "Z": "#dadada",
    "!": "#fff7d6",  # sparkle, animation only
}
# Nearest 256-colour indexes for terminals without truecolor.
PALETTE_256 = {
    "H": 54, "R": 97, "S": 223, "B": 253, "E": 236, "W": 94, "G": 222, "K": 137, "D": 94, "F": 66,
    "C": 195, "V": 24, "L": 61, "T": 66, "M": 152, "P": 230, "Z": 253, "!": 230,
}
PACKAGE_CHARS = set("PKDGZ")
MOTION_CHAR = "M"

TITLE = "B L U E P R I N T   P A C K A G E R"
SUBTITLE = "course blueprint  →  Brightspace package"


def load_grid(path: Path = GRID_FILE) -> list[list[str]]:
    rows = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    width = max(len(row) for row in rows)
    return [list(row.ljust(width, ".")) for row in rows]


def _colour(term, char: str, *, background: bool) -> str:
    if term.truecolor:
        hexvalue = PALETTE_HEX[char].lstrip("#")
        r, g, b = int(hexvalue[0:2], 16), int(hexvalue[2:4], 16), int(hexvalue[4:6], 16)
        return f"{'48' if background else '38'};2;{r};{g};{b}"
    return f"{'48' if background else '38'};5;{PALETTE_256[char]}"


def render(grid: list[list[str]], term) -> str:
    """Half-block render: two pixel rows per text line."""
    lines = []
    for upper_row in range(0, len(grid) - 1, 2):
        chars = []
        for col in range(len(grid[0])):
            upper = grid[upper_row][col]
            lower = grid[upper_row + 1][col]
            upper_set = upper in PALETTE_HEX
            lower_set = lower in PALETTE_HEX
            if not upper_set and not lower_set:
                chars.append(" ")
            elif upper_set and not lower_set:
                chars.append(f"\x1b[{_colour(term, upper, background=False)}m▀\x1b[0m")
            elif not upper_set and lower_set:
                chars.append(f"\x1b[{_colour(term, lower, background=False)}m▄\x1b[0m")
            else:
                chars.append(f"\x1b[{_colour(term, upper, background=False)};{_colour(term, lower, background=True)}m▀\x1b[0m")
        lines.append("  " + "".join(chars))
    return "\n".join(lines)


def _key_pressed(timeout: float) -> bool:
    """Best-effort non-blocking key check (POSIX); falls back to a plain sleep."""
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            sys.stdin.readline()
            return True
        return False
    except (OSError, ValueError):
        time.sleep(timeout)
        return False


def package_cells(grid: list[list[str]]) -> list[tuple[int, int]]:
    """The package: box, edges, zip teeth, glow, and the ribbon cells that touch them (not the loose sparkles)."""
    solid = {(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch in "PKDZ"}
    cells = set(solid)
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == "G" and any((r + dr, c + dc) in solid for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))):
                cells.add((r, c))
    return sorted(cells)


def package_frames(grid: list[list[str]], distance: int = 9) -> list[list[list[str]]]:
    """Frames in which the package starts `distance` cells to the left and slides into place.

    Only package cells move; the wizard and the monitor stay. Motion lines show while moving."""
    package = package_cells(grid)
    motion = [(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch == MOTION_CHAR]
    frames = []
    for offset in range(distance, -1, -1):
        frame = [row[:] for row in grid]
        for r, c in package:
            frame[r][c] = "."
        for r, c in motion:
            frame[r][c] = "."
        for r, c in package:
            target = c - offset
            if 0 <= target < len(frame[r]) and frame[r][target] == ".":
                frame[r][target] = grid[r][c]
        if offset:
            for r, c in motion:
                target = c - offset
                if 0 <= target < len(frame[r]) and frame[r][target] == ".":
                    frame[r][target] = MOTION_CHAR
        frames.append(frame)
    frames[-1] = [row[:] for row in grid]  # at rest the scene is exactly the drawn grid
    return frames


def splash(term, *, animate: bool = True, version: str = "") -> None:
    """Draw the scene. Animated on a TTY: the package slides into the monitor."""
    title_line = f"  {term.accent(term.bold(TITLE))}"
    subtitle_line = "  " + term.dim(SUBTITLE + (f"  ·  {version}" if version else ""))

    if term.plain:
        print()
        print(f"  === {TITLE} ===")
        print(subtitle_line)
        print()
        return

    grid = load_grid()
    frame_height = (len(grid) // 2) + 3  # art lines + blank + title + subtitle

    def draw(current: list[list[str]], first: bool) -> None:
        if not first:
            sys.stdout.write(f"\x1b[{frame_height}F")
        sys.stdout.write(render(current, term) + "\n\n")
        sys.stdout.write(title_line + "\n" + subtitle_line + "\n")
        sys.stdout.flush()

    term.hide_cursor()
    try:
        if animate:
            drawn_any = False
            for frame in package_frames(grid):
                draw(frame, first=not drawn_any)
                drawn_any = True
                if _key_pressed(0.07):
                    break
            final = [row[:] for row in grid]
            draw(final, first=not drawn_any)
            # a brief twinkle on the sparkles, then rest
            inside = set(package_cells(grid))
            sparkles = [(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch == "G" and (r, c) not in inside]
            for step in range(3):
                frame = [row[:] for row in grid]
                for index, (r, c) in enumerate(sparkles):
                    if (index + step) % 2 == 0:
                        frame[r][c] = "!"
                draw(frame, first=False)
                if _key_pressed(0.16):
                    break
            draw(grid, first=False)
        else:
            draw(grid, first=True)
    finally:
        term.show_cursor()
    print()
