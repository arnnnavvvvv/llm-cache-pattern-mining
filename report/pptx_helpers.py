# python-pptx helpers shared by the review deck and the poster: palette, text, stat callouts, cards, images, charts
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from PIL import Image

INK = RGBColor(0x14, 0x24, 0x2B)
TEAL = RGBColor(0x0F, 0x3D, 0x3E)
TEAL_LIGHT = RGBColor(0xE6, 0xF0, 0xEE)
ALERT = RGBColor(0xD0, 0x3B, 0x3B)
GOOD = RGBColor(0x1B, 0xAF, 0x7A)
PINK = RGBColor(0xE8, 0x7B, 0xA4)
MUTED = RGBColor(0x5F, 0x6B, 0x6E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD = RGBColor(0xF3, 0xF6, 0xF5)
HEAD, BODY = "Cambria", "Calibri"


# text box with one or more paragraphs; each paragraph is a string or a list of (text, options) runs
def text(slide, x, y, w, h, paras, size=16, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6, bullet=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, p in enumerate(paras if isinstance(paras, list) else [paras]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        runs = p if isinstance(p, list) else [(("• " if bullet else "") + p, {})]
        for t, opt in runs:
            r = para.add_run()
            r.text = t
            r.font.name = opt.get("font", font)
            r.font.size = Pt(opt.get("size", size))
            r.font.bold = opt.get("bold", bold)
            r.font.italic = opt.get("italic", False)
            r.font.color.rgb = opt.get("color", color)
    return box


# filled rounded card behind a group of content
def card(slide, x, y, w, h, fill=CARD, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    s.shadow.inherit = False
    return s


# big number with a small label under it
def stat(slide, x, y, w, value, label, color=TEAL, size=54, label_size=14):
    text(slide, x, y, w, size / 72 * 1.3, value, size=size, color=color, bold=True, font=HEAD)
    text(slide, x, y + size / 72 * 1.25, w, 0.9, label, size=label_size, color=MUTED)


# circle with a number inside, used for numbered steps
def badge(slide, x, y, n, d=0.5, fill=TEAL):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(16 * d / 0.5), True, WHITE, BODY
    return s


# picture fitted inside a box, keeping its aspect ratio and centring it
def picture(slide, path, x, y, w, h):
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    return slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


# native horizontal bar chart with value labels, one series, styled to match the deck
def bar_chart(slide, x, y, w, h, categories, values, colors, number_format='0.00"%"', size=12, max_value=None):
    data = CategoryChartData()
    data.categories = categories
    data.add_series("value", values)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), data)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.number_format, labels.number_format_is_linked = number_format, False
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size, labels.font.color.rgb, labels.font.name = Pt(size), INK, BODY
    for i, c in enumerate(colors):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    if max_value:
        ch.value_axis.maximum_scale = max_value
    ch.value_axis.minimum_scale = 0
    cat = ch.category_axis
    cat.tick_labels.font.size, cat.tick_labels.font.color.rgb, cat.tick_labels.font.name = Pt(size), INK, BODY
    cat.format.line.fill.background()
    cat.reverse_order = True
    return gf


# solid background colour for a slide
def background(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


# screenshot fitted to a box by trimming the left sidebar and the bottom, so the visible part stays readable
def screenshot(slide, path, x, y, w, h, left=0.2):
    iw, ih = Image.open(path).size
    vis_w = iw * (1 - left)
    keep_h = min(ih, vis_w * h / w)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(w * keep_h / vis_w))
    pic.crop_left = left
    pic.crop_bottom = 1 - keep_h / ih
    return pic
