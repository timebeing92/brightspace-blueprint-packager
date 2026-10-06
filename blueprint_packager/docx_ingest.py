"""Stage A: read a blueprint DOCX into an ordered tree with stable paragraph IDs.

Nothing here interprets course structure. The reader records what the Word
file contains: paragraphs, tables, runs with inline formatting and links,
list membership, styles, cell shading, and tracked-change state (Google Docs
suggestions export as Word tracked changes).

IDs are sequential in document order (`p00001`, `t001`, `c0001`) and are stable
for a given source file, which is identified by its SHA-256.
"""
from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NSMAP = {"w": W_NS, "r": R_NS}


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _flag(rpr: etree._Element | None, name: str) -> bool:
    if rpr is None:
        return False
    el = rpr.find(w(name))
    if el is None:
        return False
    val = el.get(w("val"))
    if name == "u":
        return val not in (None, "none")
    return val not in ("0", "false")


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    href: str = ""
    change: str | None = None  # None | "ins" | "del"
    change_author: str = ""
    change_date: str = ""
    image: bool = False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"text": self.text}
        if self.bold:
            out["b"] = True
        if self.italic:
            out["i"] = True
        if self.underline:
            out["u"] = True
        if self.href:
            out["href"] = self.href
        if self.change:
            out["change"] = self.change
        if self.image:
            out["image"] = True
        return out


@dataclass
class Para:
    id: str
    element: etree._Element
    style: str
    list_num_id: str | None
    list_level: int | None
    runs: list[Run]
    container: str  # "body" or a cell id
    comment_ids: list[str] = field(default_factory=list)
    kind: str = "p"

    # --- text views -----------------------------------------------------
    def text(self, view: str = "proposed") -> str:
        """Text in the requested view.

        proposed: suggested insertions included, suggested deletions omitted.
        base:     suggested insertions omitted, suggested deletions included.
        raw:      everything.
        """
        parts = []
        for run in self.runs:
            if view == "proposed" and run.change == "del":
                continue
            if view == "base" and run.change == "ins":
                continue
            parts.append(run.text)
        return "".join(parts)

    @property
    def has_change(self) -> bool:
        return any(run.change for run in self.runs)

    @property
    def fully_deleted(self) -> bool:
        """True when the paragraph has content and all of it is a pending deletion."""
        content = [run for run in self.runs if run.text.strip() or run.image]
        return bool(content) and all(run.change == "del" for run in content)

    @property
    def fully_inserted(self) -> bool:
        content = [run for run in self.runs if run.text.strip() or run.image]
        return bool(content) and all(run.change == "ins" for run in content)

    def visible_runs(self, view: str = "proposed") -> list[Run]:
        drop = "del" if view == "proposed" else "ins" if view == "base" else None
        return [run for run in self.runs if run.change != drop]

    @property
    def all_bold(self) -> bool:
        runs = [run for run in self.visible_runs() if run.text.strip()]
        return bool(runs) and all(run.bold for run in runs)

    @property
    def is_heading(self) -> bool:
        return self.style.lower().startswith("heading") or self.style in ("Title", "Subtitle")

    @property
    def heading_level(self) -> int | None:
        if self.style.lower().startswith("heading "):
            try:
                return int(self.style.split()[-1])
            except ValueError:
                return None
        return None

    def to_dict(self, view: str = "proposed") -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "kind": "p",
            "container": self.container,
            "style": self.style,
            "text": self.text(view),
            "runs": [run.to_dict() for run in self.runs],
        }
        if self.list_num_id is not None:
            out["list"] = {"num_id": self.list_num_id, "level": self.list_level}
        if self.has_change:
            out["base_text"] = self.text("base")
        if self.comment_ids:
            out["comment_ids"] = self.comment_ids
        return out


@dataclass
class Cell:
    id: str
    element: etree._Element
    row: int
    col: int
    fill: str
    children: list["Para | Table"] = field(default_factory=list)

    def paras(self, recursive: bool = True) -> Iterator[Para]:
        for child in self.children:
            if isinstance(child, Para):
                yield child
            elif recursive:
                yield from child.paras()

    def text(self, view: str = "proposed") -> str:
        return "\n".join(p.text(view) for p in self.paras())


@dataclass
class Table:
    id: str
    element: etree._Element
    container: str
    rows: list[list[Cell]] = field(default_factory=list)
    kind: str = "tbl"

    def paras(self) -> Iterator[Para]:
        for row in self.rows:
            for cell in row:
                yield from cell.paras()

    @property
    def n_cols(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    def to_dict(self, view: str = "proposed") -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "tbl",
            "container": self.container,
            "rows": [
                [
                    {
                        "id": cell.id,
                        "fill": cell.fill,
                        "children": [child.to_dict(view) for child in cell.children],
                    }
                    for cell in row
                ]
                for row in self.rows
            ],
        }


@dataclass
class Document:
    path: Path
    sha256: str
    tree: etree._ElementTree
    body_element: etree._Element
    body: list[Para | Table]
    rels: dict[str, str]
    style_names: dict[str, str]
    comments: dict[str, dict[str, str]]
    numbering: dict[tuple[str, int], str] = field(default_factory=dict)

    def list_format(self, para: "Para") -> str | None:
        """'bullet', 'decimal', ... for a list paragraph; None when not in a list."""
        if para.list_num_id is None:
            return None
        return self.numbering.get((para.list_num_id, para.list_level or 0), "bullet")

    def paras(self) -> Iterator[Para]:
        for node in self.body:
            if isinstance(node, Para):
                yield node
            else:
                yield from node.paras()

    def by_id(self) -> dict[str, Para]:
        return {p.id: p for p in self.paras()}

    def tables(self) -> Iterator[Table]:
        def walk(nodes: list[Para | Table]) -> Iterator[Table]:
            for node in nodes:
                if isinstance(node, Table):
                    yield node
                    for row in node.rows:
                        for cell in row:
                            yield from walk(cell.children)

        yield from walk(self.body)

    def to_dict(self, view: str = "proposed") -> dict[str, Any]:
        paras = list(self.paras())
        return {
            "schema": "blueprint_packager.docx_stream/1",
            "source": {"name": self.path.name, "sha256": self.sha256},
            "view": view,
            "counts": {
                "paragraphs": len(paras),
                "tables": sum(1 for _ in self.tables()),
                "paragraphs_with_pending_suggestions": sum(1 for p in paras if p.has_change),
                "comments": len(self.comments),
            },
            "body": [node.to_dict(view) for node in self.body],
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rels(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = etree.fromstring(archive.read("word/_rels/document.xml.rels"))
    except KeyError:
        return {}
    return {rel.get("Id"): rel.get("Target", "") for rel in root.iter(f"{{{PKG_REL_NS}}}Relationship")}


def _read_styles(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = etree.fromstring(archive.read("word/styles.xml"))
    except KeyError:
        return {}
    names: dict[str, str] = {}
    for style in root.iter(w("style")):
        name = style.find(w("name"))
        names[style.get(w("styleId"))] = name.get(w("val")) if name is not None else style.get(w("styleId"))
    return names


def _read_numbering(archive: zipfile.ZipFile) -> dict[tuple[str, int], str]:
    """Map (numId, level) -> number format ('bullet', 'decimal', ...)."""
    try:
        root = etree.fromstring(archive.read("word/numbering.xml"))
    except KeyError:
        return {}
    abstract: dict[str, dict[int, str]] = {}
    for abstract_num in root.iter(w("abstractNum")):
        levels: dict[int, str] = {}
        for lvl in abstract_num.findall(w("lvl")):
            fmt = lvl.find(w("numFmt"))
            levels[int(lvl.get(w("ilvl"), "0"))] = fmt.get(w("val")) if fmt is not None else "bullet"
        abstract[abstract_num.get(w("abstractNumId"))] = levels
    out: dict[tuple[str, int], str] = {}
    for num in root.iter(w("num")):
        ref = num.find(w("abstractNumId"))
        if ref is None:
            continue
        for level, fmt in abstract.get(ref.get(w("val")), {}).items():
            out[(num.get(w("numId")), level)] = fmt
    return out


def _read_comments(archive: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    try:
        root = etree.fromstring(archive.read("word/comments.xml"))
    except KeyError:
        return {}
    out: dict[str, dict[str, str]] = {}
    for comment in root.iter(w("comment")):
        out[comment.get(w("id"))] = {
            "author": comment.get(w("author"), ""),
            "date": comment.get(w("date"), ""),
            "text": " ".join((t.text or "") for t in comment.iter(w("t"))).strip(),
        }
    return out


class _Ingest:
    def __init__(self, rels: dict[str, str], style_names: dict[str, str]) -> None:
        self.rels = rels
        self.style_names = style_names
        self.n_para = 0
        self.n_table = 0
        self.n_cell = 0

    # -- runs ---------------------------------------------------------------
    def _runs(self, para_el: etree._Element) -> tuple[list[Run], list[str]]:
        runs: list[Run] = []
        comment_ids: list[str] = []

        def walk(el: etree._Element, change: str | None, author: str, date: str, href: str) -> None:
            for child in el:
                tag = child.tag
                if tag == w("ins"):
                    walk(child, "ins", child.get(w("author"), ""), child.get(w("date"), ""), href)
                elif tag == w("del"):
                    walk(child, "del", child.get(w("author"), ""), child.get(w("date"), ""), href)
                elif tag == w("hyperlink"):
                    rid = child.get(f"{{{R_NS}}}id")
                    target = self.rels.get(rid, "") if rid else ""
                    anchor = child.get(w("anchor"))
                    if not target and anchor:
                        target = f"#{anchor}"
                    walk(child, change, author, date, target)
                elif tag in (w("smartTag"), w("sdt"), w("sdtContent"), w("fldSimple")):
                    walk(child, change, author, date, href)
                elif tag == w("commentRangeStart"):
                    comment_ids.append(child.get(w("id")))
                elif tag == w("r"):
                    rpr = child.find(w("rPr"))
                    text_parts: list[str] = []
                    image = False
                    for piece in child:
                        if piece.tag in (w("t"), w("delText")):
                            text_parts.append(piece.text or "")
                        elif piece.tag == w("tab"):
                            text_parts.append("\t")
                        elif piece.tag in (w("br"), w("cr")):
                            text_parts.append("\n")
                        elif piece.tag == w("noBreakHyphen"):
                            text_parts.append("‑")
                        elif piece.tag in (w("drawing"), w("pict")):
                            image = True
                    text = "".join(text_parts)
                    if not text and not image:
                        continue
                    runs.append(
                        Run(
                            text=text,
                            bold=_flag(rpr, "b"),
                            italic=_flag(rpr, "i"),
                            underline=_flag(rpr, "u") and not href,
                            href=href,
                            change=change,
                            change_author=author,
                            change_date=date,
                            image=image,
                        )
                    )

        walk(para_el, None, "", "", "")
        return runs, comment_ids

    def para(self, el: etree._Element, container: str) -> Para:
        self.n_para += 1
        ppr = el.find(w("pPr"))
        style = ""
        num_id: str | None = None
        level: int | None = None
        if ppr is not None:
            pstyle = ppr.find(w("pStyle"))
            if pstyle is not None:
                style = self.style_names.get(pstyle.get(w("val")), pstyle.get(w("val")) or "")
            numpr = ppr.find(w("numPr"))
            if numpr is not None:
                nid = numpr.find(w("numId"))
                ilvl = numpr.find(w("ilvl"))
                num_id = nid.get(w("val")) if nid is not None else "0"
                level = int(ilvl.get(w("val"))) if ilvl is not None else 0
                if num_id == "0":  # numId 0 means "no list"
                    num_id, level = None, None
        runs, comment_ids = self._runs(el)
        return Para(
            id=f"p{self.n_para:05d}",
            element=el,
            style=style,
            list_num_id=num_id,
            list_level=level,
            runs=runs,
            container=container,
            comment_ids=comment_ids,
        )

    def table(self, el: etree._Element, container: str) -> Table:
        self.n_table += 1
        table = Table(id=f"t{self.n_table:03d}", element=el, container=container)
        for r_index, tr in enumerate(el.findall(w("tr"))):
            row: list[Cell] = []
            for c_index, tc in enumerate(tr.findall(w("tc"))):
                self.n_cell += 1
                tcpr = tc.find(w("tcPr"))
                fill = ""
                if tcpr is not None and tcpr.find(w("shd")) is not None:
                    fill = (tcpr.find(w("shd")).get(w("fill")) or "").lower()
                cell = Cell(id=f"c{self.n_cell:04d}", element=tc, row=r_index, col=c_index, fill=fill)
                cell.children = self.children(tc, cell.id)
                row.append(cell)
            table.rows.append(row)
        return table

    def children(self, parent: etree._Element, container: str) -> list[Para | Table]:
        nodes: list[Para | Table] = []
        for child in parent:
            if child.tag == w("p"):
                nodes.append(self.para(child, container))
            elif child.tag == w("tbl"):
                nodes.append(self.table(child, container))
        return nodes


def read_docx(path: str | Path) -> Document:
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        rels = _read_rels(archive)
        style_names = _read_styles(archive)
        comments = _read_comments(archive)
        numbering = _read_numbering(archive)
        tree = etree.ElementTree(etree.fromstring(archive.read("word/document.xml")))
    body_el = tree.getroot().find(w("body"))
    ingest = _Ingest(rels, style_names)
    body = ingest.children(body_el, "body")
    return Document(
        path=path,
        sha256=sha256_file(path),
        tree=tree,
        body_element=body_el,
        body=body,
        rels=rels,
        style_names=style_names,
        comments=comments,
        numbering=numbering,
    )
