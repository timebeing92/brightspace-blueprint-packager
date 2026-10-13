"""Render model blocks to Brightspace HTML in a chosen page template.

Two delivery surfaces, because Brightspace treats them differently:

* page      a packaged HTML topic. It carries its own <style> block.
* fragment  an editor field (assignment instructions, discussion description).
            Style blocks are unreliable there, so every element is styled inline.

Authored text is escaped and emitted exactly as written. The renderer adds
only template chrome (page shell, section headings, back-to-top link).
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .render_text import plain
from .authoring import video_player_url, absolute_web_url

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
EMBEDDABLE = re.compile(r"^https://(player\.vimeo\.com/video/|www\.youtube(-nocookie)?\.com/embed/)")


def drop_query_parameters(href: str, rules: list[dict[str, str]]) -> str:
    """Remove named query parameters from a web address, leaving everything else byte for byte.

    A rule is ``{"name": "utm_source"}`` or ``{"name": "utm_source", "value": "chatgpt.com"}``.
    """
    if not rules or "?" not in href:
        return href
    head, _, rest = href.partition("?")
    query, hash_mark, fragment = rest.partition("#")
    kept = []
    for pair in query.split("&"):
        name, _, value = pair.partition("=")
        if any(rule["name"] == name and ("value" not in rule or rule["value"] == value) for rule in rules):
            continue
        kept.append(pair)
    return head + ("?" + "&".join(kept) if kept else "") + (hash_mark + fragment if hash_mark else "")


# "[link to assignment: Title]" or "[link to page: Title | words to show]" inside a
# paragraph becomes a link to that object. The target is matched by exact title.
INTERNAL_LINK = re.compile(r"\[\s*link to (page|assignment|discussion|quiz|checklist)\s*:\s*([^\]|]+?)\s*(?:\|\s*([^\]]+?)\s*)?\]", re.I)


@dataclass
class Template:
    id: str
    manifest: dict[str, Any]
    css: str
    directory: Path
    link_rules: list[dict[str, str]] = field(default_factory=list)
    cleaned_links: list[dict[str, str]] = field(default_factory=list)
    # internal link targets the build knows: (kind, title) -> {"page": relative href or None, "quicklink": href or None}
    link_targets: dict[tuple[str, str], dict[str, str | None]] = field(default_factory=dict)
    provenance: str = ""  # one line written as an HTML comment at the top of every page's source (13c)
    course_label: str = ""  # small line above the page title, e.g. "MBA 620 · Marketing" (owner, 2026-10-08)
    heading_offset: int = 0  # the model's frame offset (0 by convention; 1 for an older frame at Heading 2)
    fragment_styles: bool = False  # inline styles in editor fields; off by default

    def internal_href(self, kind: str, title: str, surface: str) -> str | None:
        target = self.link_targets.get((kind.lower(), title))
        if not target:
            return None
        if kind.lower() == "page":
            return target.get("page") if surface == "page" else target.get("quicklink")
        return target.get("quicklink")

    def clean(self, href: str, where: str = "") -> str:
        """Apply the build's link cleanup to one address and remember what changed."""
        cleaned = drop_query_parameters(href, self.link_rules)
        if cleaned != href:
            self.cleaned_links.append({"where": where, "from": href, "to": cleaned})
        return cleaned

    @classmethod
    def load(cls, template_id: str, search: Path | None = None) -> "Template":
        for base in ([search] if search else []) + [TEMPLATES_DIR]:
            for directory in sorted(base.iterdir()):
                manifest_path = directory / "template.json"
                if not manifest_path.is_file():
                    continue
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("id") == template_id:
                    css = (directory / manifest["surfaces"]["page"]["css"]).read_text(encoding="utf-8")
                    return cls(template_id, manifest, css, directory)
        raise ValueError(f"Unknown page template: {template_id}")

    def cue_kind(self, cue: str) -> str:
        for prefix, kind in self.manifest.get("visual_cues", {}).items():
            if cue.strip().lower().startswith(prefix.lower()):
                return kind
        return "callout"


@dataclass
class LinkRestoration:
    """Re-attach a link that the export-to-blueprint step flattened or dropped."""
    where: str
    anchor_text: str
    href: str
    remove_text: str = ""
    evidence: str = ""
    used: int = 0


@dataclass
class RenderContext:
    template: Template
    surface: str  # "page" | "fragment"
    where: str = ""
    restorations: list[LinkRestoration] = field(default_factory=list)
    diagnostics: list[dict[str, str]] = field(default_factory=list)
    heading_shift: int = 0
    heading_offset: int = 0  # frame_level - FRAME_LEVEL, from the model's conventions
    content_top: int = 2  # the first content level on this surface

    def style(self, key: str) -> str:
        """Inline style for an editor-field element. Empty by default.

        Editor fields (assignment and discussion descriptions) are plain semantic HTML
        so the tenant's own stylesheet sets type, color, and spacing, the same as every
        hand-written description. A template may still offer inline styles; a build
        turns them on with `fragment_styles: "template"` (owner's call of 2026-10-07:
        the BUMK 515 inline styles are not the default)."""
        if self.surface != "fragment" or not self.template.fragment_styles:
            return ""
        value = self.template.manifest["surfaces"]["fragment"].get("styles", {}).get(key, "")
        return f' style="{html.escape(value, quote=True)}"' if value else ""

    def heading_tag(self, level: int) -> str:
        """Word Heading N -> hN, after removing a legacy frame offset and any local shift.

        The page heading is the surface's h1, so content never renders below h2.
        A template may still remap a level in its `heading_map`; the default is identity."""
        mapping = self.template.manifest["surfaces"][self.surface].get("heading_map", {})
        level = max(2, min(6, level - self.heading_offset + self.heading_shift))
        return mapping.get(str(level), f"h{level}")

    def warn(self, code: str, message: str) -> None:
        self.diagnostics.append({"severity": "warning", "code": code, "message": message, "where": self.where})


# ------------------------------------------------------------------- inline text
def _segments(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(run) for run in runs if run.get("text")]


def _apply_span(segments: list[dict[str, Any]], start: int, end: int, *, href: str | None = None, remove: bool = False) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    position = 0
    for seg in segments:
        text = seg["text"]
        seg_start, seg_end = position, position + len(text)
        position = seg_end
        if seg_end <= start or seg_start >= end:
            out.append(seg)
            continue
        before = text[: max(0, start - seg_start)]
        middle = text[max(0, start - seg_start) : min(len(text), end - seg_start)]
        after = text[min(len(text), end - seg_start) :]
        if before:
            out.append({**seg, "text": before})
        if middle and not remove:
            out.append({**seg, "text": middle, "href": href, "restored": True})
        if after:
            out.append({**seg, "text": after})
    return out


def _replace_span(segments: list[dict[str, Any]], start: int, end: int, replacement: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace the text between start and end with one new segment."""
    out: list[dict[str, Any]] = []
    position = 0
    placed = False
    for seg in segments:
        text = seg["text"]
        seg_start, seg_end = position, position + len(text)
        position = seg_end
        if seg_end <= start or seg_start >= end:
            out.append(seg)
            continue
        before = text[: max(0, start - seg_start)]
        after = text[min(len(text), end - seg_start):]
        if before:
            out.append({**seg, "text": before})
        if not placed:
            out.append({**{k: v for k, v in seg.items() if k not in ("href", "restored")}, **replacement})
            placed = True
        if after:
            out.append({**seg, "text": after})
    return out


def _internal_links(segments: list[dict[str, Any]], ctx: RenderContext) -> list[dict[str, Any]]:
    """Turn "[link to kind: Title | words]" into a link to that object, or leave it visible and say so."""
    while True:
        text = "".join(seg["text"] for seg in segments)
        match = INTERNAL_LINK.search(text)
        if not match:
            return segments
        kind, title, words = match.group(1).lower(), match.group(2).strip(), (match.group(3) or "").strip()
        href = ctx.template.internal_href(kind, title, ctx.surface)
        if href is None:
            known = any(k == kind and t == title for k, t in ctx.template.link_targets)
            if known and kind == "page":
                ctx.diagnostics.append({"severity": "error", "code": "LINK_TARGET_UNREACHABLE",
                                        "message": f"'[link to page: {title}]' sits in an activity description, where a page link needs the page's topic code; not supported yet. Link to the page from a course page instead.",
                                        "where": ctx.where})
            else:
                ctx.diagnostics.append({"severity": "error", "code": "LINK_TARGET_UNKNOWN",
                                        "message": f"'[link to {kind}: {title}]' names no {kind} in this blueprint; titles must match exactly", "where": ctx.where})
            # leave the bracket in place so the problem is visible, and stop looking at it
            marker = {"text": match.group(0).replace("[", "［", 1).replace("]", "］"), "href": ""}
            segments = _replace_span(segments, match.start(), match.end(), marker)
            continue
        segments = _replace_span(segments, match.start(), match.end(), {"text": words or title, "href": href, "internal": True})


def heading_inline(runs: list[dict[str, Any]], ctx: RenderContext) -> str:
    """A heading's text; anything the author put after a line break inside it is a subline.

    Authors write "1. Initial Observation⏎What did you notice?" as one heading with a soft
    break. The words stay in the heading; the second line is wrapped in <small> so it reads as
    a subtitle instead of a second heading line of the same weight."""
    text = inline(runs, ctx)
    if "<br>" not in text:
        return text
    first, rest = text.split("<br>", 1)
    return f"{first}<br><small>{rest.replace('<br>', ' ')}</small>"


def inline(runs: list[dict[str, Any]], ctx: RenderContext) -> str:
    segments = _internal_links(_segments(runs), ctx)
    text = "".join(seg["text"] for seg in segments)
    for restoration in ctx.restorations:
        if restoration.where and restoration.where != ctx.where:
            continue
        index = text.find(restoration.anchor_text)
        if index < 0:
            continue
        if restoration.remove_text:
            cut = text.find(restoration.remove_text)
            if cut < 0:
                continue
        segments = _apply_span(segments, index, index + len(restoration.anchor_text), href=restoration.href)
        if restoration.remove_text:
            text = "".join(seg["text"] for seg in segments)
            cut = text.find(restoration.remove_text)
            lead = 1 if cut > 0 and text[cut - 1] == " " else 0
            segments = _apply_span(segments, cut - lead, cut + len(restoration.remove_text), remove=True)
        text = "".join(seg["text"] for seg in segments)
        restoration.used += 1
    parts: list[str] = []
    index = 0
    while index < len(segments):
        seg = segments[index]
        href = seg.get("href")
        group = [seg]
        while href and index + 1 < len(segments) and segments[index + 1].get("href") == href:
            index += 1
            group.append(segments[index])
        rendered = "".join(_format(item) for item in group)
        if href:
            href = ctx.template.clean(href, ctx.where)
            if group[0].get("internal"):
                # a link to another object of this course opens in the same window
                parts.append(f'<a href="{html.escape(href, quote=True)}"{ctx.style("a")}>{rendered}</a>')
                index += 1
                continue
            external = not href.startswith("#") and "://" in href
            attrs = ' target="_blank" rel="noopener"' if external or not href.startswith("#") else ""
            rendered = f'<a href="{html.escape(href, quote=True)}"{attrs}{ctx.style("a")}>{rendered}</a>'
        parts.append(rendered)
        index += 1
    return "".join(parts).strip()


def _format(seg: dict[str, Any]) -> str:
    text = html.escape(seg["text"], quote=False).replace("\n", "<br>")
    if not text.strip():
        return text
    if seg.get("u") and not seg.get("href"):
        text = f"<u>{text}</u>"
    if seg.get("i"):
        text = f"<em>{text}</em>"
    if seg.get("b"):
        text = f"<strong>{text}</strong>"
    return text


# ------------------------------------------------------------------------ blocks
def render_blocks(blocks: list[dict[str, Any]], ctx: RenderContext) -> str:
    out: list[str] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        kind = block["kind"]
        if kind == "li":
            run_end = index
            while run_end < len(blocks) and blocks[run_end]["kind"] == "li":
                run_end += 1
            out.append(_render_list(blocks[index:run_end], ctx))
            index = run_end
            continue
        if kind == "p":
            out.append(f"<p{ctx.style('p')}>{inline(block['runs'], ctx)}</p>")
        elif kind == "heading":
            tag = ctx.heading_tag(block["level"])
            runs = block["runs"]
            if all(run.get("b") for run in runs if run["text"].strip()):
                # a heading that is bold from end to end takes its weight from the template
                runs = [{k: v for k, v in run.items() if k != "b"} for run in runs]
            out.append(f"<{tag}{ctx.style(tag)}>{heading_inline(runs, ctx)}</{tag}>")
        elif kind == "dropdown":
            inner = render_blocks(block["blocks"], ctx)
            out.append(f"<details>\n<summary>{html.escape(block['title'], quote=False)}</summary>\n{inner}\n</details>")
        elif kind == "visual":
            out.append(_render_visual(block, ctx))
        elif kind == "video":
            out.append(_render_video(block, ctx))
        elif kind == "placeholder":
            text = html.escape(block["text"], quote=False)
            out.append(f'<p{ctx.style("p")} data-blueprint-pending="true"><strong>Draft:</strong> {text}</p>')
        elif kind == "table":
            out.append(_render_table(block, ctx))
        elif kind == "image":
            ctx.warn("IMAGE_NOT_BUILT", f"Embedded image line not rendered: {block.get('text', '')[:80]}")
        index += 1
    return "\n".join(part for part in out if part)


def _render_list(items: list[dict[str, Any]], ctx: RenderContext) -> str:
    def build(position: int, level: int) -> tuple[str, int]:
        ordered = bool(items[position].get("ordered"))
        tag = "ol" if ordered else "ul"
        parts = [f"<{tag}{ctx.style(tag)}>"]
        while position < len(items) and items[position].get("level", 0) >= level:
            item = items[position]
            if item.get("level", 0) > level:
                nested, position = build(position, item.get("level", 0))
                parts[-1] = parts[-1][: -len("</li>")] + "\n" + nested + "\n</li>"
                continue
            if bool(item.get("ordered")) != ordered:
                break
            parts.append(f"<li{ctx.style('li')}>{inline(item['runs'], ctx)}</li>")
            position += 1
        parts.append(f"</{tag}>")
        return "\n".join(parts), position

    out: list[str] = []
    position = 0
    while position < len(items):
        rendered, position = build(position, items[position].get("level", 0))
        out.append(rendered)
    return "\n".join(out)


def _render_visual(block: dict[str, Any], ctx: RenderContext) -> str:
    kind = ctx.template.cue_kind(block.get("cue", ""))
    if kind == "timeline" and ctx.surface == "page":
        stages: list[list[dict[str, Any]]] = []
        lead: list[dict[str, Any]] = []
        for child in block["blocks"]:
            is_title = child["kind"] == "heading" or (
                child["kind"] == "p" and child["runs"] and all(r.get("b") for r in child["runs"] if r["text"].strip())
            )
            if is_title:
                stages.append([child])
            elif stages:
                stages[-1].append(child)
            else:
                lead.append(child)
        parts = [render_blocks(lead, ctx)] if lead else []
        parts.append('<section class="timeline">')
        for stage in stages:
            title, rest = stage[0], stage[1:]
            parts.append('<article class="stage">')
            parts.append(f"<h2>{inline(title['runs'], ctx)}</h2>")
            parts.append(render_blocks(rest, ctx))
            parts.append("</article>")
        parts.append("</section>")
        return "\n".join(p for p in parts if p)
    inner = render_blocks(block["blocks"], ctx)
    attrs = block.get("attrs") or {}
    tone = attrs.get("tone", "")
    palette = ctx.template.manifest.get("callout_tones", {})
    if tone and tone not in palette:
        ctx.warn("CALLOUT_TONE_UNKNOWN", f"callout tone '{tone}' is not in the template's palette {sorted(palette)}; the default tone is used")
        tone = ""
    color = attrs.get("color", "")
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        ctx.warn("CALLOUT_COLOR_INVALID", f"callout color '{color}' is not a six-digit hex colour; ignored")
        color = ""
    if ctx.surface == "fragment":
        style = ctx.style(f"callout_{tone}") if tone else ""
        style = style or ctx.style("callout")
        if color:
            style = (style[:-1] + f" border-left-color: {color};\"") if style else f' style="border-left: .3rem solid {color};"'
        return f"<div{style}>\n{inner}\n</div>"
    css_class = "styled-box" if kind == "styled_box" else "callout"
    if tone:
        css_class += f" callout--{tone}"
    style = f' style="border-left-color: {color};"' if color else ""
    return f'<div class="{css_class}"{style}>\n{inner}\n</div>'


def _render_video(block: dict[str, Any], ctx: RenderContext) -> str:
    href = ctx.template.clean(block.get("href", ""), ctx.where)
    title = html.escape(block.get("title", "Video"), quote=True)
    if block.get("placeholder"):
        return (f'<div class="video-pending" data-blueprint-video-pending="{title}" '
                'style="border: 1px dashed #567682; padding: 1.25rem; margin: 1rem 0;">'
                f'<p{ctx.style("p")}>Video to be added: {title}</p></div>')
    player = video_player_url(href)
    if not player:
        ctx.warn("VIDEO_NOT_EMBEDDABLE", f"Video '{block.get('title')}' has no embeddable player URL; rendered as a link")
        if not absolute_web_url(href):
            return f"<p{ctx.style('p')}>{title}</p>"
        return f'<p{ctx.style("p")}><a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">{title}</a></p>'
    src = html.escape(player, quote=True)
    frame = f'<iframe src="{src}" title="{title}" loading="lazy" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>'
    if ctx.surface == "fragment":
        return ('<div style="position: relative; padding-top: 56.25%; margin-bottom: 1rem;">'
                + frame.replace("<iframe ", '<iframe style="position: absolute; inset: 0; width: 100%; height: 100%; border: 0;" ')
                + "</div>")
    return f'<div class="video-wrap">{frame}</div>'


def _render_table(block: dict[str, Any], ctx: RenderContext) -> str:
    attrs = ctx.style("table") if ctx.surface == "fragment" else ' class="bp-table"'
    rows = []
    for row in block["rows"]:
        cells = "".join(f"<td{ctx.style('td')}>{render_blocks(cell, ctx)}</td>" for cell in row)
        rows.append(f"<tr>{cells}</tr>")
    return f"<table{attrs}>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"


# ------------------------------------------------------------------------- pages
def _shell(template: Template, title: str, heading: str, body: str) -> str:
    page = template.manifest["surfaces"]["page"]
    links = "\n".join(f'<link rel="stylesheet" href="{html.escape(url, quote=True)}">' for url in page.get("external_stylesheets", []))
    stamp = f"<!-- {html.escape(template.provenance, quote=False).replace('--', '- -')} -->\n" if template.provenance else ""
    return (
        "<!DOCTYPE html>\n"
        + stamp +
        '<html lang="en"><head>\n'
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title, quote=False)}</title>\n"
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"{links}\n<style>\n{template.css}\n</style>\n"
        '</head><body id="top"><a class="skip" href="#main">Skip to content</a><header class="wrapper">\n'
        + (f'<p class="kicker">{html.escape(template.course_label, quote=False)}</p>\n' if template.course_label else "")
        + f"<h1>{html.escape(heading, quote=False)}</h1>\n"
        '</header><main id="main" class="wrapper" role="main" tabindex="-1">\n'
        f"{body}\n"
        "</main></body></html>\n"
    )


def _resources_section(blocks: list[dict[str, Any]], ctx: RenderContext, default_heading: str) -> str:
    """Resources keep their own lead heading when they have one; otherwise the template names the section."""
    headings = [b for b in blocks if b["kind"] == "heading"]
    top = min((b["level"] for b in headings), default=None)
    lead_is_own = bool(blocks) and blocks[0]["kind"] == "heading" and blocks[0]["level"] == top and sum(1 for b in headings if b["level"] == top) == 1
    model_top = ctx.content_top + ctx.heading_offset  # the first content level as the model records it
    if lead_is_own:
        ctx.heading_shift = model_top - top
        return render_blocks(blocks, ctx)
    ctx.heading_shift = (model_top + 1 - top) if top is not None else 0
    return f"<h2>{html.escape(default_heading, quote=False)}</h2>\n" + render_blocks(blocks, ctx)


def render_week_page(week: dict[str, Any], template: Template, restorations: list[LinkRestoration]) -> tuple[str, list[dict[str, str]]]:
    page = week["overview_page"]
    chrome = template.manifest["surfaces"]["page"]
    ctx = RenderContext(template, "page", where=page["title"], restorations=restorations, heading_offset=template.heading_offset)
    heading = page.get("page_heading") or page["title"]
    sections = ['<section id="overview"><hr>', render_blocks(page["blocks"], ctx), "</section>"]
    if week["objectives"]:
        ctx.heading_shift = 0
        sections += ['<section id="learning-objectives">', f"<h2>{html.escape(chrome['section_headings']['objectives'], quote=False)}</h2>",
                     render_blocks(week["objectives"], ctx), "<hr></section>"]
    if week["resources"]:
        sections += ['<section id="resources">', _resources_section(week["resources"], ctx, chrome["section_headings"]["resources"]), "</section>"]
        ctx.heading_shift = 0
    sections += ['<section id="next">', f'<div class="back-top"><a href="#top">{html.escape(chrome["back_to_top"], quote=False)}</a></div>', "</section>"]
    return _shell(template, heading, heading, "\n".join(sections)), ctx.diagnostics


def render_course_page(page: dict[str, Any], template: Template, restorations: list[LinkRestoration]) -> tuple[str, list[dict[str, str]]]:
    ctx = RenderContext(template, "page", where=page["title"], restorations=restorations, heading_offset=template.heading_offset)
    heading = page.get("page_heading") or page["title"]
    body = '<section id="content"><hr>\n' + render_blocks(page["blocks"], ctx) + "\n</section>"
    return _shell(template, heading, heading, body), ctx.diagnostics


def render_fragment(blocks: list[dict[str, Any]], template: Template, where: str, restorations: list[LinkRestoration] | None = None) -> tuple[str, list[dict[str, str]]]:
    ctx = RenderContext(template, "fragment", where=where, restorations=restorations or [], heading_offset=template.heading_offset)
    inner = render_blocks(blocks, ctx)
    if not template.fragment_styles:
        return inner, ctx.diagnostics  # plain semantic HTML, no wrapper
    return f"<div{ctx.style('wrapper')}>\n{inner}\n</div>", ctx.diagnostics


def plain_text(blocks: list[dict[str, Any]]) -> str:
    return " ".join(plain(b["runs"]) for b in blocks if b.get("runs"))
