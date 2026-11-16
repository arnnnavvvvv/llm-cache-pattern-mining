# python-docx helpers for the thesis layout: styles, fields, captions, figures, tables and lists
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

FONT = "Times New Roman"


# sets a style's font everywhere word looks for it, including east-asian and complex-script slots
def set_font(style, size, bold=False, italic=False):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for key in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(key), None)
    for key in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(key), FONT)


# new a4 document with thesis margins, body text and heading styles
def new_document() -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(2.5)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.5)
    normal = doc.styles["Normal"]
    set_font(normal, 12)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    for name, size, align, before, after in [("Heading 1", 16, WD_ALIGN_PARAGRAPH.CENTER, 0, 18),
                                            ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT, 18, 8),
                                            ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT, 12, 6)]:
        st = doc.styles[name]
        set_font(st, size, bold=True)
        pf = st.paragraph_format
        pf.alignment, pf.space_before, pf.space_after = align, Pt(before), Pt(after)
        pf.keep_with_next, pf.line_spacing = True, 1.15
    for name in ("List Bullet", "List Number", "Caption"):
        set_font(doc.styles[name], 12 if name != "Caption" else 11, bold=(name == "Caption"))
    doc.styles["Caption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    modern_mode(doc)
    return doc


# marks the file as a current word document so it does not open in compatibility mode
def modern_mode(doc):
    settings = doc.settings.element
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = OxmlElement("w:compat")
        settings.append(compat)
    for el in compat.findall(qn("w:compatSetting")):
        if el.get(qn("w:name")) == "compatibilityMode":
            compat.remove(el)
    el = OxmlElement("w:compatSetting")
    for k, v in (("w:name", "compatibilityMode"), ("w:uri", "http://schemas.microsoft.com/office/word"), ("w:val", "15")):
        el.set(qn(k), v)
    compat.append(el)


# appends a word field (toc, seq, page...) to a paragraph, with a placeholder result shown until fields update
def add_field(paragraph, instr: str, shown: str = ""):
    def fld(kind):
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
        r = OxmlElement("w:r")
        r.append(el)
        return r
    paragraph._p.append(fld("begin"))
    r = OxmlElement("w:r")
    t = OxmlElement("w:instrText")
    t.set(qn("xml:space"), "preserve")
    t.text = f" {instr} "
    r.append(t)
    paragraph._p.append(r)
    paragraph._p.append(fld("separate"))
    run = paragraph.add_run(shown)
    paragraph._p.append(fld("end"))
    return run


# plain body paragraph, justified, with optional bold lead-in text
def para(doc, text: str, lead: str = "", align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, size=None, italic=False):
    p = doc.add_paragraph()
    p.alignment = align
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.0)
    if lead:
        r = p.add_run(lead)
        r.bold = True
    r = p.add_run(text)
    r.italic = italic
    if size:
        for run in p.runs:
            run.font.size = Pt(size)
    return p


# centred line used on the title and certificate pages
def centred(doc, text: str, size=12, bold=False, italic=False, space_after=6, highlight=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(text)
    r.font.size, r.bold, r.italic = Pt(size), bold, italic
    if highlight:
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


# bulleted list, one paragraph per item, with an optional bold lead before a colon
def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if isinstance(item, tuple):
            r = p.add_run(item[0])
            r.bold = True
            p.add_run(item[1])
        else:
            p.add_run(item)


# displayed formula on its own line with a right-aligned equation number
def equation(doc, text: str, number: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(text)
    r.italic = True
    r.font.name = "Cambria Math"
    p.add_run(f"\t({number})")
    p.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), alignment=2)
    return p


# chapter opening: page break, "CHAPTER n" and the title, as one heading-1 paragraph for the contents
def chapter(doc, number, title: str, first=False):
    if not first:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    h = doc.add_heading(level=1)
    if number is not None:
        h.add_run(f"CHAPTER {number}")
        h.add_run().add_break()
    h.add_run(title.upper())
    return h


# figure image centred with its caption below ("Figure n Title"), numbered by a seq field
class Counter:
    figure = 0
    table = {}


def figure(doc, path, title: str, width_in=6.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width_in))
    Counter.figure += 1
    cap = doc.add_paragraph(style="Caption")
    cap.add_run("Figure ")
    add_field(cap, "SEQ Figure \\* ARABIC", str(Counter.figure))
    cap.add_run(f" {title}")
    return Counter.figure


# caption placed above a table ("Table c.n Title"), restarting the number in every chapter
def table_caption(doc, chapter_no: int, title: str):
    n = Counter.table.get(chapter_no, 0) + 1
    Counter.table[chapter_no] = n
    cap = doc.add_paragraph(style="Caption")
    cap.paragraph_format.keep_with_next = True
    cap.add_run(f"Table {chapter_no}.")
    add_field(cap, "SEQ Table \\r 1 \\* ARABIC" if n == 1 else "SEQ Table \\* ARABIC", str(n))
    cap.add_run(f" {title}")
    return f"{chapter_no}.{n}"


# shades one table cell with a hex fill
def shade(cell, fill: str):
    tcpr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    tcpr.append(sh)


# grid table with a shaded bold header row, fixed column widths and small single-spaced text
def table(doc, header, rows, widths_cm, size=10, bold_rows=(), align_right=()):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(h))
        r.bold, r.font.size = True, Pt(size)
        shade(c, "E8E8E8")
    for k, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(size)
            r.bold = k in bold_rows
            if i in align_right:
                cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for row in t.rows:
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.first_line_indent = Cm(0)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


# monospaced code listing, single spaced, in a light box
def code(doc, text: str, size=8.5):
    for line in text.rstrip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run(line if line else " ")
        r.font.name, r.font.size = "Consolas", Pt(size)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# starts a new section on a new page with page numbers in the footer, numbering from start
def numbered_section(doc, start=1):
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sec.footer.is_linked_to_previous = False
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(p, "PAGE", str(start))
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), str(start))
    sec._sectPr.append(pg)
    return sec


# field-driven contents page: table of contents, list of tables or list of figures
def field_page(doc, title: str, instr: str, first=False):
    if not first:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    centred(doc, title, size=14, bold=True, space_after=12)
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    add_field(p, instr, "Right-click and choose Update Field to build this list.")


# a page break on its own
def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


__all__ = ["new_document", "add_field", "para", "centred", "bullets", "equation", "chapter", "figure", "table_caption",
           "table", "code", "numbered_section", "field_page", "page_break", "Path", "Inches", "Cm", "Pt",
           "WD_ALIGN_PARAGRAPH", "WD_COLOR_INDEX"]
