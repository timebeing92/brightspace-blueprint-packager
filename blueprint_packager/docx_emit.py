"""WordprocessingML helpers for writing a normalized blueprint.

Authored paragraphs are never retyped. They are deep-copied from the source
document, pending suggestions are resolved to the chosen view, comment anchors
are removed, and (only when the course map says so) the paragraph style or
accidental block bold is changed. Generated structure lines are new paragraphs.
"""
from __future__ import annotations

import copy
import re
import zipfile
from pathlib import Path

from lxml import etree

from .docx_ingest import W_NS, w

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

STRUCTURE_FILL = "E8EEF4"  # light blue-grey behind generated directive lines
LABEL_FILL = "F2F2F2"  # wizard label-row fill


def clone_clean(element: etree._Element, view: str = "proposed") -> etree._Element:
    """Deep-copy a paragraph or table and resolve suggestions and comment anchors."""
    el = copy.deepcopy(element)
    keep, drop = ("ins", "del") if view == "proposed" else ("del", "ins")
    for node in list(el.iter(w(drop))):
        parent = node.getparent()
        if parent is None:
            continue
        if parent.tag == w("rPr"):
            parent.remove(node)  # paragraph-mark change marker
            continue
        parent.remove(node)
    for node in list(el.iter(w(keep))):
        parent = node.getparent()
        if parent is None:
            continue
        if parent.tag == w("rPr"):
            parent.remove(node)
            continue
        index = parent.index(node)
        for child in list(node):
            if view != "proposed":
                for del_text in child.iter(w("delText")):
                    del_text.tag = w("t")
            parent.insert(index, child)
            index += 1
        parent.remove(node)
    for tag in ("commentRangeStart", "commentRangeEnd"):
        for node in list(el.iter(w(tag))):
            node.getparent().remove(node)
    for ref in list(el.iter(w("commentReference"))):
        run = ref.getparent()
        if run is not None and run.getparent() is not None:
            run.getparent().remove(run)
    return el


def set_style(para: etree._Element, style_id: str | None) -> None:
    """Set or clear the paragraph style (pStyle) without touching runs."""
    ppr = para.find(w("pPr"))
    if ppr is None:
        if style_id is None:
            return
        ppr = etree.SubElement(para, w("pPr"))
        para.remove(ppr)
        para.insert(0, ppr)
    pstyle = ppr.find(w("pStyle"))
    if style_id is None:
        if pstyle is not None:
            ppr.remove(pstyle)
        return
    if pstyle is None:
        pstyle = etree.Element(w("pStyle"))
        ppr.insert(0, pstyle)
    pstyle.set(w("val"), style_id)


def remove_numbering(para: etree._Element) -> None:
    ppr = para.find(w("pPr"))
    if ppr is not None and ppr.find(w("numPr")) is not None:
        ppr.remove(ppr.find(w("numPr")))


def unbold(para: etree._Element) -> None:
    """Remove explicit bold from every run of a paragraph."""
    for rpr in para.iter(w("rPr")):
        if rpr.getparent() is not None and rpr.getparent().tag == w("pPr"):
            continue
        for tag in ("b", "bCs"):
            node = rpr.find(w(tag))
            if node is not None:
                rpr.remove(node)


def _run(text: str, bold: bool = False, italic: bool = False, color: str | None = None, size: int | None = None) -> etree._Element:
    run = etree.Element(w("r"))
    if bold or italic or color or size:
        rpr = etree.SubElement(run, w("rPr"))
        if bold:
            etree.SubElement(rpr, w("b")).set(w("val"), "1")
            etree.SubElement(rpr, w("bCs")).set(w("val"), "1")
        if italic:
            etree.SubElement(rpr, w("i")).set(w("val"), "1")
        if color:
            etree.SubElement(rpr, w("color")).set(w("val"), color)
        if size:
            etree.SubElement(rpr, w("sz")).set(w("val"), str(size))
            etree.SubElement(rpr, w("szCs")).set(w("val"), str(size))
    t = etree.SubElement(run, w("t"))
    t.text = text
    t.set(XML_SPACE, "preserve")
    return run


def make_para(
    text: str = "",
    *,
    style_id: str | None = None,
    bold: bool = False,
    fill: str | None = None,
    bold_prefix: str | None = None,
    size: int | None = None,
) -> etree._Element:
    """Create a new paragraph. `bold_prefix` renders `prefix` bold and the rest plain."""
    para = etree.Element(w("p"))
    if style_id or fill:
        ppr = etree.SubElement(para, w("pPr"))
        if style_id:
            etree.SubElement(ppr, w("pStyle")).set(w("val"), style_id)
        if fill:
            shd = etree.SubElement(ppr, w("shd"))
            shd.set(w("val"), "clear")
            shd.set(w("color"), "auto")
            shd.set(w("fill"), fill)
    if bold_prefix is not None and text.startswith(bold_prefix):
        para.append(_run(bold_prefix, bold=True, size=size))
        rest = text[len(bold_prefix):]
        if rest:
            para.append(_run(rest, size=size))
    elif text:
        para.append(_run(text, bold=bold, size=size))
    return para


def make_cell(children: list[etree._Element], template_tcpr: etree._Element | None, fill: str | None) -> etree._Element:
    cell = etree.Element(w("tc"))
    tcpr = copy.deepcopy(template_tcpr) if template_tcpr is not None else etree.Element(w("tcPr"))
    shd = tcpr.find(w("shd"))
    if fill:
        if shd is None:
            shd = etree.SubElement(tcpr, w("shd"))
        shd.set(w("val"), "clear")
        shd.set(w("fill"), fill)
    elif shd is not None:
        tcpr.remove(shd)
    cell.append(tcpr)
    for child in children:
        cell.append(child)
    if not children or children[-1].tag != w("p"):
        cell.append(etree.Element(w("p")))  # Word requires a closing paragraph in every cell
    return cell


def make_single_column_table(rows: list[tuple[list[etree._Element], str | None]], template_table: etree._Element) -> etree._Element:
    """Build a one-column table whose look is copied from an existing table."""
    table = etree.Element(w("tbl"))
    for tag in ("tblPr", "tblGrid"):
        node = template_table.find(w(tag))
        if node is not None:
            table.append(copy.deepcopy(node))
    template_tc = template_table.find(f"{w('tr')}/{w('tc')}")
    template_tcpr = template_tc.find(w("tcPr")) if template_tc is not None else None
    template_trpr = template_table.find(f"{w('tr')}/{w('trPr')}")
    for children, fill in rows:
        row = etree.SubElement(table, w("tr"))
        if template_trpr is not None:
            row.append(copy.deepcopy(template_trpr))
        row.append(make_cell(children, template_tcpr, fill))
    return table


XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def paragraph_text_nodes(para: etree._Element) -> list[etree._Element]:
    return list(para.iter(w("t")))


def replace_text(para: etree._Element, find: str, new: str) -> bool:
    """Replace one exact stretch of text inside a paragraph, keeping the formatting
    of the run where the stretch begins. Returns False unless it occurs exactly once."""
    nodes = paragraph_text_nodes(para)
    full = "".join(node.text or "" for node in nodes)
    start = full.find(find)
    if not find or start < 0 or full.find(find, start + 1) >= 0:
        return False
    end = start + len(find)
    position, placed = 0, False
    for node in nodes:
        text = node.text or ""
        node_start, node_end = position, position + len(text)
        position = node_end
        if node_end <= start or node_start >= end:
            continue
        before = text[: max(0, start - node_start)]
        after = text[min(len(text), end - node_start):]
        node.text = before + ("" if placed else new) + after
        node.set(XML_SPACE, "preserve")
        placed = True
    return placed


HYPERLINK_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def make_link_run(text: str, rel_id: str) -> etree._Element:
    """A hyperlink element pointing at a relationship that write_docx will add."""
    link = etree.Element(w("hyperlink"))
    link.set(R_ID, rel_id)
    run = _run(text, color="1155CC")
    rpr = run.find(w("rPr"))
    if rpr is None:
        rpr = etree.Element(w("rPr"))
        run.insert(0, rpr)
    etree.SubElement(rpr, w("u")).set(w("val"), "single")
    link.append(run)
    return link


def write_docx(source_path: Path, out_path: Path, document_root: etree._Element,
               extra_links: dict[str, str] | None = None) -> None:
    """Write a new DOCX: source package with a new document.xml and no comments part.

    ``extra_links`` maps new relationship ids to external addresses, for
    hyperlinks in paragraphs that were not in the source.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_path) as src, zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            name = info.filename
            if name == "word/comments.xml":
                continue
            data = src.read(name)
            if name == "word/document.xml":
                data = etree.tostring(document_root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "word/_rels/document.xml.rels":
                root = etree.fromstring(data)
                for rel in list(root):
                    if rel.get("Target") == "comments.xml":
                        root.remove(rel)
                for rel_id, target in (extra_links or {}).items():
                    rel = etree.SubElement(root, f"{{{root.nsmap.get(None)}}}Relationship" if root.nsmap.get(None) else "Relationship")
                    rel.set("Id", rel_id)
                    rel.set("Type", HYPERLINK_REL)
                    rel.set("Target", target)
                    rel.set("TargetMode", "External")
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "[Content_Types].xml":
                root = etree.fromstring(data)
                for override in list(root):
                    if override.get("PartName") == "/word/comments.xml":
                        root.remove(override)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            fixed = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            fixed.compress_type = zipfile.ZIP_DEFLATED
            fixed.external_attr = 0o100644 << 16
            dst.writestr(fixed, data)


def style_ids_by_name(source_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(source_path) as archive:
        root = etree.fromstring(archive.read("word/styles.xml"))
    out: dict[str, str] = {}
    for style in root.iter(w("style")):
        name = style.find(w("name"))
        if name is not None:
            out[name.get(w("val")).lower()] = style.get(w("styleId"))
    return out
