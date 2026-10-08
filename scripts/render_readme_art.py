#!/usr/bin/env python3
"""Render docs/assets/blueprint-packager-art.txt into docs/assets/blueprint-packager.svg.

Same construction as the Blueprint Wizard runner's splash: a grid of pixel
squares, crisp edges, a soft rounded card behind. Edit the text grid, run this,
commit both.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "docs" / "assets" / "blueprint-packager-art.txt"
OUT = ROOT / "docs" / "assets" / "blueprint-packager.svg"

PALETTE = {
    "H": "#5f0087", "R": "#875faf", "S": "#ffd7af", "B": "#dadada", "E": "#14303e", "W": "#875f00",
    "G": "#ffd787", "K": "#af875f", "D": "#875f00", "F": "#54707e", "C": "#d7ffff", "V": "#174b5c",
    "L": "#5f5faf", "T": "#54707e", "M": "#b8d3de", "P": "#ffe9b8", "Z": "#dadada",
}
SCALE = 9
MARGIN_X, MARGIN_Y = 44, 22
TITLE = "Blueprint Packager"


def main() -> int:
    rows = [line.rstrip("\n") for line in GRID.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    width = max(len(r) for r in rows)
    rows = [r.ljust(width, ".") for r in rows]
    art_w, art_h = width * SCALE, len(rows) * SCALE
    canvas_w, canvas_h = art_w + 2 * MARGIN_X, art_h + MARGIN_Y + 86
    by_colour: dict[str, list[str]] = {}
    for y, row in enumerate(rows):
        x = 0
        while x < width:
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            run = 1
            while x + run < width and row[x + run] == ch:
                run += 1
            by_colour.setdefault(PALETTE[ch], []).append(f'      <rect x="{x}" y="{y}" width="{run}" height="1"/>')
            x += run
    groups = "\n".join(f'    <g fill="{colour}">\n' + "\n".join(rects) + "\n    </g>" for colour, rects in by_colour.items())
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}"
     viewBox="0 0 {canvas_w} {canvas_h}" role="img" aria-labelledby="bp-title bp-desc">
  <title id="bp-title">{TITLE}</title>
  <desc id="bp-desc">A colour pixel-art wizard waves a wand and a wrapped course package,
  zip teeth showing, slides into a monitor whose screen already shows a course page.</desc>
  <rect width="{canvas_w}" height="{canvas_h}" rx="14" fill="#eaf5f9"/>
  <rect x="1" y="1" width="{canvas_w - 2}" height="{canvas_h - 2}" rx="13" fill="none" stroke="#b8d3de" stroke-width="2"/>
  <g transform="translate({MARGIN_X} {MARGIN_Y}) scale({SCALE})" shape-rendering="crispEdges">
{groups}
  </g>
  <text x="{canvas_w / 2}" y="{canvas_h - 40}" text-anchor="middle" font-family="'Courier New', Courier, monospace"
        font-size="30" font-weight="700" fill="#14303e">{TITLE}</text>
  <text x="{canvas_w / 2}" y="{canvas_h - 16}" text-anchor="middle" font-family="'Courier New', Courier, monospace"
        font-size="13" fill="#54707e">blueprint in, Brightspace package out, receipts all the way</text>
</svg>
'''
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({canvas_w}x{canvas_h}, {sum(len(v) for v in by_colour.values())} rects)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
