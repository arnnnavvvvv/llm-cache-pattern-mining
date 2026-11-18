# builds the final (external) review deck on the university template from the result files, figures and demo screenshots
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

RES = ROOT / "results"
FIG, REP, DEMO = RES / "figures", RES / "figures" / "report", RES / "figures" / "demo"
TEMPLATE = ROOT / "report" / "assets" / "final_review_template.pptx"
OUT = ROOT / "report" / "Final_Review_Presentation.pptx"
TITLE = "Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways"
MEMBERS = ["Arnav Gupta – [Regd. No.]", "Saugata Kumar Jana – [Regd. No.]", "Avishkar Maitra – [Regd. No.]",
           "Arpita Suresh Kulkarni – [Regd. No.]"]

MAROON, TEAL, INK = RGBColor(0x57, 0x23, 0x14), RGBColor(0x38, 0x91, 0xA7), RGBColor(0x1A, 0x1A, 0x1A)
MUTED, CARD, GOOD = RGBColor(0x5E, 0x5A, 0x55), RGBColor(0xF6, 0xF1, 0xEA), RGBColor(0x1B, 0xAF, 0x7A)
ALERT, PINK, GREY, WHITE = RGBColor(0xC0, 0x39, 0x2B), RGBColor(0xE8, 0x7B, 0xA4), RGBColor(0x9A, 0x98, 0x93), RGBColor(0xFF, 0xFF, 0xFF)
BODY, HEAD = "Gill Sans MT", "Times New Roman"
TOP, BOTTOM, LEFT, RIGHT = 1.05, 5.0, 0.3, 9.7


# copies a template slide (text, shapes and pictures) to a new slide placed right after it
def duplicate(prs, index):
    src = prs.slides[index]
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    rid = {}
    for key, rel in src.part.rels.items():
        if rel.reltype.endswith("/image"):
            rid[key] = new.part.relate_to(rel._target, rel.reltype)
    tree = new.shapes._spTree
    for el in src.shapes._spTree:
        if el.tag.endswith("}nvGrpSpPr") or el.tag.endswith("}grpSpPr"):
            continue
        dup = copy.deepcopy(el)
        for node in dup.iter():
            for attr in (qn("r:embed"), qn("r:link")):
                if node.get(attr) in rid:
                    node.set(attr, rid[node.get(attr)])
        tree.append(dup)
    ids = prs.slides._sldIdLst
    moved = ids[-1]
    ids.remove(moved)
    ids.insert(index + 1, moved)
    return new


# text shape on a slide by its template name
def shape(slide, name):
    return next(s for s in slide.shapes if s.name == name)


# sets the section title and the bulleted sub-heading of a content slide, dropping the template's empty lines
def heading(slide, title, sub):
    t = shape(slide, "TextShape 1") if any(s.name == "TextShape 1" for s in slide.shapes) else None
    if t is not None:
        t.text_frame.paragraphs[0].runs[0].text = title
    body = shape(slide, "TextShape 2")
    paras = body.text_frame.paragraphs
    runs = paras[0].runs
    runs[0].text = sub
    for r in runs[1:]:
        r.text = ""
    for p in paras[1:]:
        p._p.getparent().remove(p._p)
    body.height = Inches(0.45)
    for r in paras[0].runs:
        r.font.size = Pt(17)


# text box in the template's body font; paragraphs are strings or lists of (text, options) runs
def text(slide, x, y, w, h, paras, size=13, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, after=4, bullet=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, p in enumerate(paras if isinstance(paras, list) else [paras]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(after)
        runs = p if isinstance(p, list) else [(p, {})]
        if bullet:
            runs = [("▪ ", {"color": TEAL, "bold": True})] + list(runs)
        for t, o in runs:
            r = para.add_run()
            r.text = t
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.italic = o.get("italic", False)
            r.font.color.rgb = o.get("color", color)
    return box


# rounded card used to group content
def card(slide, x, y, w, h, fill=CARD, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.08
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


# big number with a short label beneath it
def stat(slide, x, y, w, value, label, color=MAROON, size=30, label_size=11):
    text(slide, x, y, w, size / 72 * 1.25, value, size=size, color=color, bold=True, font=HEAD)
    text(slide, x, y + size / 72 * 1.2, w, 0.7, label, size=label_size, color=MUTED)


# picture fitted inside a box, centred, keeping its aspect ratio
def picture(slide, path, x, y, w, h):
    iw, ih = Image.open(path).size
    k = min(w / iw, h / ih)
    return slide.shapes.add_picture(str(path), Inches(x + (w - iw * k) / 2), Inches(y + (h - ih * k) / 2),
                                    Inches(iw * k), Inches(ih * k))


# screenshot cropped to drop the app sidebar and the lower part so it fills a box legibly
def screenshot(slide, path, x, y, w, h, left=0.2):
    iw, ih = Image.open(path).size
    vis = iw * (1 - left)
    keep = min(ih, vis * h / w)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(w * keep / vis))
    pic.crop_left, pic.crop_bottom = left, 1 - keep / ih
    pic.line.color.rgb = RGBColor(0xD9, 0xD4, 0xCC)
    return pic


# simple grid table with a shaded header
def table(slide, x, y, w, header, rows, widths, size=10, bold_rows=()):
    gt = slide.shapes.add_table(len(rows) + 1, len(header), Inches(x), Inches(y), Inches(w), Inches(0.3 * (len(rows) + 1)))
    t = gt.table
    for i, wd in enumerate(widths):
        t.columns[i].width = Inches(wd)
    for r, row in enumerate([header] + rows):
        for c, v in enumerate(row):
            cell = t.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.fill.solid()
            cell.fill.fore_color.rgb = MAROON if r == 0 else (CARD if r % 2 else WHITE)
            p = cell.text_frame.paragraphs[0]
            run = p.add_run()
            run.text = str(v)
            run.font.name, run.font.size = BODY, Pt(size)
            run.font.bold = r == 0 or (r - 1) in bold_rows
            run.font.color.rgb = WHITE if r == 0 else INK
    return gt


# native horizontal bar chart, one series, values labelled
def bars(slide, x, y, w, h, cats, vals, colors, fmt='0.00"%"', size=11, vmax=None):
    data = CategoryChartData()
    data.categories = cats
    data.add_series("v", vals)
    ch = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), data).chart
    ch.has_legend = ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked, dl.position = fmt, False, XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.name, dl.font.color.rgb = Pt(size), BODY, INK
    for i, c in enumerate(colors):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.value_axis.minimum_scale = 0
    if vmax:
        ch.value_axis.maximum_scale = vmax
    ca = ch.category_axis
    ca.reverse_order = True
    ca.tick_labels.font.size, ca.tick_labels.font.name, ca.tick_labels.font.color.rgb = Pt(size), BODY, INK
    ca.format.line.fill.background()
    return ch


# small numbered circle for steps and module cards
def badge(slide, x, y, n, d=0.32):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    s.fill.solid()
    s.fill.fore_color.rgb = TEAL
    s.line.fill.background()
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(11), True, WHITE, BODY


# speaker notes for the presenter
def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body


# title slide: project title, guide, students
def title_slide(s):
    t = shape(s, "TextShape 1").text_frame.paragraphs[1].runs[0]
    t.text, t.font.size = TITLE, Pt(20)
    sup = shape(s, "TextShape 2").text_frame.paragraphs[0].runs
    sup[2].text, sup[3].text = "Dr. Sandipan Maiti", ""
    box = shape(s, "CustomShape 3").text_frame.paragraphs
    box[0].runs[-1].text = ": [fill SDP Id]"
    for i, m in enumerate(MEMBERS):
        p = box[2 + i]
        r = p.add_run()
        r.text, r.font.size, r.font.name = m, Pt(13), BODY
    notes(s, "Introduce the team and the project in one line: an LLM-gateway cache that decides when a stored answer can "
             "be safely reused by mining how conversations behave.")


# introduction: overview, problem, objectives
def introduction(prs):
    s = prs.slides[2]
    heading(s, "Introduction", "Project Overview")
    text(s, LEFT, 1.15, 5.0, 2.6, [
        [("A behavior-aware cache admission engine for LLM gateways. ", {"bold": True, "color": MAROON}),
         ("It decides whether a stored answer can be safely reused by mining how real conversations behave — not only how "
          "similar two requests look.", {})],
        "Built end to end: data pipeline on 30,015 real chat turns, pattern miner, association-rule learner, LightGBM "
        "verifier, a REST admission service and an interactive replay demo.",
        "Evaluated on a held-out later week with a frozen, pre-registered protocol."], size=13, after=10)
    for i, (v, l) in enumerate([("240×", "more requests served safely than a standard semantic cache"),
                                ("56.3%", "near-duplicate requests a similarity cache answers wrongly — the gap we found"),
                                ("66.7% → 0%", "wrong reuse on correction turns once mined patterns are used"),
                                ("43 ms", "per admission decision on a laptop CPU")]):
        x, y = 5.55 + (i % 2) * 2.1, 1.15 + (i // 2) * 1.85
        card(s, x, y, 1.95, 1.65)
        stat(s, x + 0.1, y + 0.1, 1.8, v, l, size=24 if len(v) < 7 else 18)
    notes(s, "Four numbers to remember: 240x, 56.3%, 66.7% to 0%, 43 ms.")

    s = prs.slides[3]
    heading(s, "Introduction", "Problem Statement & Motivations")
    text(s, LEFT, 1.15, 4.6, 3.3, [
        "LLM calls cost money per token and take seconds; gateways answer repeated requests from a cache.",
        "Semantic caches (GPTCache and successors) reuse an answer when one request is similar enough to an old one.",
        "But real users iterate: “make it shorter”, “continue”, “that’s wrong” only make sense inside their own conversation.",
        "52.8% of 30,015 real chat turns are not self-contained requests."], size=12.5, bullet=True, after=8)
    picture(s, REP / "act_distribution.png", 4.95, 1.1, 4.75, 2.9)
    card(s, LEFT, 4.3, RIGHT - LEFT, 0.62, fill=RGBColor(0xEA, 0xF3, 0xF6))
    text(s, LEFT + 0.15, 4.32, RIGHT - LEFT - 0.3, 0.58, [[("Problem: ", {"bold": True, "color": MAROON}),
         ("decide, for each request in a multi-turn stream, when a cached answer is safe to reuse — so the gateway saves "
          "cost and latency without serving wrong answers.", {})]], size=12.5, anchor=MSO_ANCHOR.MIDDLE)
    notes(s, "Motivation: similarity is not interchangeability in conversations.")

    s = prs.slides[4]
    heading(s, "Introduction", "Objectives & Expected Impact")
    text(s, LEFT, 1.1, 4.5, 0.35, "Objectives", size=15, bold=True, color=MAROON, font=HEAD)
    objs = ["Mine behavioral patterns (dialogue acts, intents, sequences) from gateway traffic",
            "Build a behavior-aware admission engine: rules + verifier + expected-benefit decision",
            "Evaluate rigorously on real traffic at matched error rates on a held-out period",
            "Deliver a deployable admission service and an inspectable demo"]
    for i, o in enumerate(objs):
        badge(s, LEFT, 1.55 + i * 0.78, i + 1)
        text(s, LEFT + 0.42, 1.5 + i * 0.78, 4.1, 0.75, o, size=12.5)
    card(s, 5.1, 1.1, 4.6, 3.8)
    text(s, 5.25, 1.15, 4.3, 0.35, "Expected impact", size=15, bold=True, color=MAROON, font=HEAD)
    text(s, 5.25, 1.6, 4.3, 3.2, [
        [("Lower cost and latency: ", {"bold": True}), ("each safe reuse skips a paid, multi-second model call", {})],
        [("Fewer wrong answers: ", {"bold": True}), ("blocks unsafe reuse on follow-ups and corrections", {})],
        [("Explainable decisions: ", {"bold": True}), ("human-readable mined rules for audit and debugging", {})],
        [("Reusable method: ", {"bold": True}), ("a fair, replay-based way to evaluate any LLM cache", {})]],
         size=12.5, bullet=True, after=10)


# related work and improvements
def background(prs):
    s = prs.slides[5]
    heading(s, "Background & Related Work", "Related Work & Their Limitations")
    table(s, LEFT, 1.15, RIGHT - LEFT, ["System", "Approach", "Limitation"], [
        ["GPTCache (2023)", "one global similarity threshold", "same threshold for every request; ignores conversation"],
        ["MeanCache (IPDPS 2025)", "per-user learned similarity (federated)", "still judges each query in isolation"],
        ["VectorQ (2025)", "adaptive thresholds per embedding region", "similarity of one request only"],
        ["Category-aware caching (2025)", "thresholds / TTL per query category", "topic ≠ conversational role"],
        ["ContextCache (PVLDB 2025)", "attention over the current dialogue history", "no behavior mined across sessions and users"],
        ["FrugalGPT, RouteLLM", "model cascades / per-prompt routers", "no session behavior in routing"]],
          [2.4, 3.3, 3.7], size=11)
    text(s, LEFT, 4.35, RIGHT - LEFT, 0.6, [[("Common gap: ", {"bold": True, "color": MAROON}),
         ("every system decides from one request (at most with its own context); none mines the recurring structure of "
          "the traffic stream.", {})]], size=12.5)

    s = prs.slides[6]
    heading(s, "Background & Related Work", "Improvements over Existing Solutions")
    table(s, LEFT, 1.15, 5.1, ["System", "Context", "Mined behavior", "Both sides"], [
        ["GPTCache", "✗", "✗", "✗"], ["MeanCache", "✗", "✗", "✗"], ["VectorQ", "✗", "✗", "✗"], ["Category-aware", "✗", "✗", "✗"],
        ["ContextCache", "✓", "✗", "✗"], ["Ours", "✓", "✓", "✓"]], [1.8, 1.0, 1.3, 1.0], size=11, bold_rows=(5,))
    text(s, 5.6, 1.15, 4.1, 3.8, [
        [("Mines behavior across all traffic: ", {"bold": True}), ("FP-Growth + PrefixSpan over dialogue acts and intents, re-mined daily", {})],
        [("Conditions on both sides of a reuse: ", {"bold": True}), ("behavioral state of the request and of the cached entry", {})],
        [("Learns interpretable rules: ", {"bold": True}), ("e.g. reuse from a correction chain → 0% acceptable", {})],
        [("Evaluated fairly: ", {"bold": True}), ("per-policy replay at matched wrong-reuse rates on a held-out future period", {})]],
         size=12, bullet=True, after=9)


# proposed solution: architecture, workflow, modules, methods, tools
def solution(prs):
    s = prs.slides[7]
    heading(s, "Proposed Solution", "System Architecture / Block Diagram")
    picture(s, REP / "block_diagram.png", LEFT, 1.05, RIGHT - LEFT, 3.95)
    notes(s, "Top: online path per request. Bottom: offline loop re-mined daily from past traffic only.")

    s = prs.slides[8]
    heading(s, "Proposed Solution", "Workflow: one request through the admission engine")
    picture(s, REP / "decision_flow.png", LEFT, 1.05, 3.9, 3.95)
    steps = [("Retrieve", "top-3 earlier requests by cosine similarity (FAISS), floor 0.70"),
             ("Describe", "dialogue act and intent of both turns; behavioral state from mined sequences"),
             ("Look up", "association-rule prior π(r) for the (state, act) pair of request and entry"),
             ("Score", "LightGBM verifier → probability q, discounted by entry age"),
             ("Decide", "expected benefit B = U·q − L·(1 − q); serve the best entry if B ≥ θ")]
    for i, (h, b) in enumerate(steps):
        y = 1.15 + i * 0.75
        badge(s, 4.45, y, i + 1)
        text(s, 4.85, y - 0.04, 4.85, 0.75, [[(h + ": ", {"bold": True, "color": MAROON}), (b, {})]], size=12)

    s = prs.slides[9]
    heading(s, "Proposed Solution", "Key Components / Features & Modules")
    mods = [("Data ingest & replay", "WildChat → gateway-style logs; time-ordered replay with a separate cache per policy"),
            ("Behavior tagger", "5 dialogue acts and 20 intents for every turn"),
            ("Pattern miner", "daily FP-Growth + PrefixSpan per session and user; behavioral states"),
            ("Rule learner", "smoothed association rules over request/entry states (out-of-fold)"),
            ("Decision engine", "LightGBM verifier + expected-benefit admission with staleness decay"),
            ("Service & demo", "FastAPI /admit · /record · /health and a 5-page interactive demo")]
    for i, (h, b) in enumerate(mods):
        x, y = LEFT + (i % 3) * 3.15, 1.15 + (i // 3) * 1.9
        card(s, x, y, 3.0, 1.75)
        badge(s, x + 0.15, y + 0.15, i + 1)
        text(s, x + 0.55, y + 0.12, 2.35, 0.45, h, size=13.5, bold=True, color=MAROON, font=HEAD)
        text(s, x + 0.15, y + 0.62, 2.75, 1.1, b, size=11.5)

    s = prs.slides[10]
    heading(s, "Proposed Solution", "Algorithms and Methods Used")
    table(s, LEFT, 1.12, 5.3, ["Method", "Used for"], [
        ["Sentence-BERT (MiniLM-L6-v2)", "request embeddings"], ["FAISS exact inner product", "candidate retrieval"],
        ["k-means (k = 20)", "intent clusters"], ["LLM tagging + logistic regression", "dialogue acts"],
        ["FP-Growth", "frequent behavior itemsets"], ["PrefixSpan", "ordered behavior sequences"],
        ["Class association rules (CBA)", "reuse-safety prior π(r)"], ["LightGBM", "reuse verifier"],
        ["Session bootstrap + Holm", "significance testing"]], [3.0, 2.3], size=10.5)
    card(s, 5.8, 1.12, 3.9, 3.85)
    text(s, 5.95, 1.18, 3.6, 0.35, "Core formulas", size=14, bold=True, color=MAROON, font=HEAD)
    text(s, 5.95, 1.6, 3.6, 3.3, [
        [("Rule prior  ", {"bold": True}), ("π(r) = (Σ yᵢ + m·ȳ) / (nᵣ + m)", {"font": "Cambria Math"})],
        [("Validity  ", {"bold": True}), ("q = f(z) · 2^(−age / T)", {"font": "Cambria Math"})],
        [("Benefit  ", {"bold": True}), ("B = U·q − L·(1 − q)", {"font": "Cambria Math"})],
        [("Decision  ", {"bold": True}), ("serve argmax B if B ≥ θ", {"font": "Cambria Math"})],
        [("Score  ", {"bold": True}), ("HR@α = max_θ {HR : WR ≤ α}", {"font": "Cambria Math"})],
        [("r = (state, act) of request and of cached entry; m = 20; T = 30 days", {"size": 10.5, "color": MUTED})]],
         size=12.5, after=11)

    s = prs.slides[11]
    heading(s, "Proposed Solution", "Technologies, Frameworks and Tools Used")
    groups = [("Data & ML", "Python 3.11 · pandas · NumPy · PyArrow · Hugging Face datasets · scikit-learn · LightGBM"),
              ("Embeddings & search", "sentence-transformers · PyTorch (CPU) · FAISS"),
              ("Pattern mining", "mlxtend (FP-Growth) · prefixspan"),
              ("Labeling", "Claude Sonnet / Haiku via API gateway (judge, act tags) · Qwen via Groq (seed labels)"),
              ("Service & demo", "FastAPI · Uvicorn · Streamlit · Altair · OpenAPI 3.1"),
              ("Quality & reporting", "pytest (19 tests) · Git/GitHub · Matplotlib · python-docx · python-pptx")]
    for i, (h, b) in enumerate(groups):
        x, y = LEFT + (i % 2) * 4.75, 1.15 + (i // 2) * 1.27
        card(s, x, y, 4.6, 1.12)
        text(s, x + 0.15, y + 0.08, 4.3, 0.35, h, size=13, bold=True, color=MAROON, font=HEAD)
        text(s, x + 0.15, y + 0.45, 4.3, 0.65, b, size=11.5)


# implementation: dataset, labels, parameters
def implementation(prs):
    s = prs.slides[12]
    heading(s, "Implementation and Results", "Dataset Descriptions / Input – Output Descriptions")
    ds = pd.read_csv(RES / "dataset_stats.csv").set_index("period")
    table(s, LEFT, 1.12, 5.2, ["Period", "Turns", "Sessions", "Users", "Dates (2023)"],
          [[p, f"{ds.loc[p, 'turns']:,}", f"{ds.loc[p, 'sessions']:,}", f"{ds.loc[p, 'users']:,}",
            f"{pd.Timestamp(ds.loc[p, 'start']):%b %d}–{pd.Timestamp(ds.loc[p, 'end']):%b %d}"]
           for p in ["train", "dev", "confirm", "all"]], [1.0, 0.95, 1.0, 0.85, 1.4], size=11, bold_rows=(3,))
    text(s, LEFT, 2.75, 5.2, 2.2, [
        "WildChat-1M: real multi-turn chatbot conversations with timestamps, anonymised users and the real answers",
        "English, multi-turn, non-toxic; one row per user turn",
        "Time-ordered split 60 / 20 / 20 — the confirmation week is unseen until the final run"], size=11.5, bullet=True, after=6)
    card(s, 5.7, 1.12, 4.0, 1.75, fill=RGBColor(0xEA, 0xF3, 0xF6))
    text(s, 5.85, 1.17, 3.7, 1.7, [[("Input ", {"bold": True, "color": MAROON, "size": 14})],
                                   "session id, user id, request text",
                                   "cache of earlier answered requests"], size=11.5, after=3)
    card(s, 5.7, 3.0, 4.0, 1.95, fill=RGBColor(0xEA, 0xF6, 0xEF))
    text(s, 5.85, 3.05, 3.7, 1.9, [[("Output ", {"bold": True, "color": MAROON, "size": 14})],
                                   "serve / call model decision",
                                   "cached answer, matched entry, score",
                                   "dialogue act, intent, latency"], size=11.5, after=3)

    s = prs.slides[13]
    heading(s, "Implementation and Results", "Ground Truth: judged reuse labels")
    text(s, LEFT, 1.12, 3.9, 3.9, [
        "Candidates: top-3 earlier turns with similarity ≥ 0.70 → 12,124 turns, 25,345 pairs",
        "Reference-based judge sees the new request, the answer the user really got, and each cached answer",
        "Judge chosen from 3 models on the same 199 pairs: 85–88% agreement",
        "10,776 turns labeled (88.9%), even 88.5–89.3% coverage in every stratum; metrics re-weighted",
        "Two-rater human gold set prepared for judge validation"], size=11.5, bullet=True, after=7)
    picture(s, REP / "label_coverage.png", 4.3, 1.1, 5.4, 3.9)

    s = prs.slides[14]
    heading(s, "Implementation and Results", "Parameters Descriptions")
    rows = [["Similarity floor / candidates", "0.70 / top 3"], ["Intent clusters (k-means)", "20"], ["Dialogue acts", "5"],
            ["FP-Growth min support", "0.02"], ["PrefixSpan min support / max length", "0.01 / 3"],
            ["Behavioral state (frequent suffix)", "≤ 2 acts"], ["Rule smoothing m", "20 pseudo-pairs"]]
    rows2 = [["Staleness half-life T", "30 days"], ["Reuse value U / wrong cost L", "1 / 1"], ["Softmax temperature", "0.05"],
             ["Wrong-reuse levels α", "5%, 10%"], ["Bootstrap resamples", "1,000 sessions"], ["Significance", "α = 0.05, Holm"],
             ["Split (by time)", "60 / 20 / 20"]]
    table(s, LEFT, 1.15, 4.6, ["Parameter", "Value"], rows, [3.0, 1.6], size=11)
    table(s, 5.1, 1.15, 4.6, ["Parameter", "Value"], rows2, [3.0, 1.6], size=11)
    text(s, LEFT, 4.55, RIGHT - LEFT, 0.4, "All values fixed in config.yaml before the confirmation run.", size=11, color=MUTED)


# experimental outcomes: finding, main result, curves, safety, rules, validation, performance, ui
def outcomes(prs):
    summ = pd.read_csv(RES / "confirm_summary.csv").set_index("policy")
    lat = json.loads((RES / "service_latency.json").read_text())
    base = 15
    s = prs.slides[base]
    heading(s, "Implementation and Results", "Outcome 1: conversation behavior decides safe reuse")
    picture(s, FIG / "wrong_reuse_by_act.png", LEFT, 1.05, 6.1, 3.5)
    stat(s, 6.6, 1.1, 3.1, "56.3%", "of 7,360 near-duplicate requests are answered wrongly by a similarity cache", color=ALERT)
    stat(s, 6.6, 2.3, 3.1, "75.7%", "wrong when the request depends on context", color=ALERT, size=26)
    stat(s, 6.6, 3.4, 3.1, "37.1%", "wrong when it is self-contained", color=TEAL, size=26)
    text(s, LEFT, 4.6, RIGHT - LEFT, 0.4, "Novel finding: similarity is necessary but not sufficient — the role of the turn on "
                                         "both sides of a reuse governs safety.", size=12, bold=True, color=MAROON)

    s = prs.slides[base + 1]
    heading(s, "Implementation and Results", "Outcome 2: behavior-aware admission serves ~240× more")
    cats = ["P1 Similarity threshold (GPTCache-style)", "P2 Per-intent thresholds", "P5 Context embedding (ContextCache-style)",
            "Ours: behavior-aware (dialogue acts)", "Ours: behavior-aware + mined patterns"]
    pols = ["P1_fixed", "P2_per_intent", "P5_context", "P3_per_query", "P4_patterns"]
    text(s, LEFT, 1.08, 6.0, 0.3, "Requests served from cache at ≤ 10% wrong answers (held-out week)", size=11.5, color=MUTED)
    bars(s, LEFT, 1.35, 6.1, 3.2, cats, [summ.loc[p, "hit_at_wr10"] * 100 for p in pols], [GREY, GREY, GREY, GOOD, PINK],
         size=11, vmax=5.8)
    stat(s, 6.7, 1.15, 3.0, "4.49%", "of all requests served safely vs 0.02% for a standard semantic cache", color=PINK, size=30)
    stat(s, 6.7, 2.45, 3.0, "+4.47 pts", "gain over the fixed threshold, significant at both levels (p ≤ 0.002, Holm)",
         color=MAROON, size=24)
    stat(s, 6.7, 3.6, 3.0, "Robust", "gain holds with a stricter similarity floor (+4.34 pts)", color=TEAL, size=22)

    s = prs.slides[base + 2]
    heading(s, "Implementation and Results", "Outcome 3: dominates similarity caching at every operating point")
    picture(s, FIG / "confirm_curves.png", LEFT, 1.05, 6.0, 3.75)
    text(s, 6.45, 1.15, 3.25, 3.7, [
        "Each curve = one policy as its threshold is loosened",
        "Higher and further left is better",
        "Similarity baselines (blue, orange) stay near zero until wrong answers are very high",
        "Behavior-aware policies serve 4–5% at ≤10% wrong and up to ~9% at 30%",
        "Operators pick their own risk level"], size=11.5, bullet=True, after=7)

    s = prs.slides[base + 3]
    heading(s, "Implementation and Results", "Outcome 4: mined patterns make reuse safer")
    picture(s, REP / "mechanism_all.png", LEFT, 1.05, 6.2, 3.4)
    stat(s, 6.75, 1.1, 2.95, "66.7% → 0%", "wrong reuse on correction turns, per-turn model → with mined patterns", color=PINK, size=22)
    stat(s, 6.75, 2.35, 2.95, "15.4% → 13.3%", "wrong reuse on follow-ups", color=MAROON, size=20)
    stat(s, 6.75, 3.4, 2.95, "30%", "follow-ups served wrongly by the context-embedding baseline", color=ALERT, size=20)
    text(s, LEFT, 4.55, RIGHT - LEFT, 0.4, "Patterns refuse reuse in behavioral states where it historically failed "
                                         "(at the ≤10% operating point).", size=11.5, color=MUTED)

    s = prs.slides[base + 4]
    heading(s, "Implementation and Results", "Outcome 5: interpretable behavioral rules")
    picture(s, REP / "rules_bar.png", LEFT, 1.05, 6.3, 3.6)
    card(s, 6.8, 1.1, 2.9, 1.65)
    text(s, 6.9, 1.15, 2.7, 1.6, [[("0% acceptable", {"bold": True, "color": ALERT, "size": 16})],
                                  "fresh question ↔ answer from a chain of corrections (34 pairs)"], size=11.5)
    card(s, 6.8, 2.95, 2.9, 1.65)
    text(s, 6.9, 3.0, 2.7, 1.6, [[("47% acceptable", {"bold": True, "color": GOOD, "size": 16})],
                                 "fresh question ↔ fresh question (2,643 pairs) — the safest reuse"], size=11.5)
    text(s, LEFT, 4.65, RIGHT - LEFT, 0.35, "Rules are learned automatically and explain every decision — something a "
                                          "similarity score cannot.", size=11.5, color=MUTED)

    s = prs.slides[base + 5]
    heading(s, "Implementation and Results", "Outcome 6: validated results")
    picture(s, REP / "positive_control.png", LEFT, 1.05, 4.6, 3.0)
    text(s, LEFT, 4.1, 4.6, 0.8, "Positive control: a planted behavioral effect is recovered — 24.0% vs 5.7% hit rate.",
         size=11.5, color=MUTED)
    text(s, 5.15, 1.1, 4.55, 3.8, [
        [("Pre-registered: ", {"bold": True}), ("claims and metrics fixed before testing", {})],
        [("Frozen & single run: ", {"bold": True}), ("code tagged, held-out week evaluated once", {})],
        [("Matched error rates: ", {"bold": True}), ("every policy compared at the same wrong-answer level", {})],
        [("Statistics: ", {"bold": True}), ("1,000 session bootstraps, Holm correction", {})],
        [("Stable models: ", {"bold": True}), ("cross-validated F1 0.63–0.64, spread ≤ 0.075", {})],
        [("No leakage: ", {"bold": True}), ("patterns mined from past traffic only; 19 automated tests", {})]],
         size=12, bullet=True, after=8)

    s = prs.slides[base + 6]
    heading(s, "Implementation and Results", "Outcome 7: deployable, fast admission service")
    picture(s, REP / "latency.png", LEFT, 1.05, 4.6, 2.6)
    stat(s, LEFT, 3.75, 2.2, f"{lat['engine_ms_p50']:.0f} ms", "median decision", size=26)
    stat(s, 2.6, 3.75, 2.3, f"{lat['cache_entries']:,}", "cached entries, laptop CPU", size=26)
    screenshot(s, DEMO / "api_docs.png", 5.15, 1.05, 4.55, 3.9, left=0.0)
    notes(s, "REST API: POST /admit before a model call, POST /record after. OpenAPI documentation is generated.")

    s = prs.slides[base + 7]
    heading(s, "Implementation and Results", "User Interface: replay and decision inspector")
    screenshot(s, DEMO / "demo_replay_end.png", LEFT, 1.05, 4.6, 3.6)
    screenshot(s, DEMO / "demo_inspect_blocked.png", 5.1, 1.05, 4.6, 3.6)
    text(s, LEFT, 4.7, 4.6, 0.3, "Replay of the held-out week reproduces the reported results", size=10.5, color=MUTED)
    text(s, 5.1, 4.7, 4.6, 0.3, "Identical text, unsafe reuse: blocked by the mined rule", size=10.5, color=MUTED)

    s = prs.slides[base + 8]
    heading(s, "Implementation and Results", "User Interface: live admission and operating point")
    screenshot(s, DEMO / "demo_live.png", LEFT, 1.05, 4.6, 3.6)
    screenshot(s, DEMO / "demo_operating_10.png", 5.1, 1.05, 4.6, 3.6)
    text(s, LEFT, 4.7, 4.6, 0.3, "Fresh repeats served; “make it shorter” blocked as a follow-up", size=10.5, color=MUTED)
    text(s, 5.1, 4.7, 4.6, 0.3, "Choose an error budget, read hit rates off real curves", size=10.5, color=MUTED)


# summary slide: findings, limitations, future directions
def summary(prs, index):
    s = prs.slides[index]
    body = shape(s, "TextShape 2")
    body._element.getparent().remove(body._element)
    cols = [("Key Findings", MAROON, [
        "Behavior, not similarity, decides whether a cached LLM answer is safe to reuse",
        "Behavior-aware admission serves ~240× more requests than a standard semantic cache at equal error",
        "Mined patterns remove wrong reuse on corrections and yield readable rules",
        "Deployable: 43 ms decisions through a REST API"]),
        ("Limitations", TEAL, [
            "One public dataset over two weeks",
            "Labels from an LLM judge (3 models agree 85–88%); human rating in progress",
            "Live dialogue-act tagger can be made more accurate"]),
        ("Future Directions", GOOD, [
            "Extend behavioral signals to model routing and conversation-level fast-tracking (explored)",
            "Larger, more repetitive workloads (support desks, FAQs)",
            "Live deployment inside a production gateway"])]
    for i, (h, c, items) in enumerate(cols):
        x = LEFT + i * 3.15
        card(s, x, 0.85, 3.0, 4.1)
        text(s, x + 0.15, 0.92, 2.7, 0.4, h, size=15, bold=True, color=c, font=HEAD)
        text(s, x + 0.15, 1.45, 2.75, 3.45, items, size=13, bullet=True, after=10)


# bibliography slide
def bibliography(prs, index):
    s = prs.slides[index]
    refs = ["F. Bang, “GPTCache: An open-source semantic cache for LLM applications,” NLP-OSS, 2023.",
            "W. Gill et al., “MeanCache: User-centric semantic caching for LLM web services,” IEEE IPDPS, 2025.",
            "L. G. Schroeder et al., “Adaptive semantic prompt caching with VectorQ,” arXiv:2502.03771, 2025.",
            "C. Wang et al., “Category-aware semantic caching for heterogeneous LLM workloads,” arXiv:2510.26835, 2025.",
            "J. Yan et al., “ContextCache: Context-aware semantic cache for multi-turn queries,” PVLDB 18(12), 2025.",
            "L. Chen, M. Zaharia, J. Zou, “FrugalGPT,” Trans. Machine Learning Research, 2024.",
            "I. Ong et al., “RouteLLM: Learning to route LLMs with preference data,” ICLR, 2025.",
            "W. Zhao et al., “WildChat: 1M ChatGPT interaction logs in the wild,” ICLR, 2024.",
            "L. Zheng et al., “Judging LLM-as-a-judge with MT-Bench and Chatbot Arena,” NeurIPS, 2023.",
            "J. Han, J. Pei, Y. Yin, “Mining frequent patterns without candidate generation,” ACM SIGMOD, 2000.",
            "J. Pei et al., “PrefixSpan: Mining sequential patterns by prefix-projected pattern growth,” ICDE, 2001.",
            "B. Liu, W. Hsu, Y. Ma, “Integrating classification and association rule mining,” KDD, 1998.",
            "G. Ke et al., “LightGBM: A highly efficient gradient boosting decision tree,” NeurIPS, 2017.",
            "N. Reimers, I. Gurevych, “Sentence-BERT,” EMNLP-IJCNLP, 2019."]
    text(s, LEFT, 1.0, RIGHT - LEFT, 4.0, [f"[{i}] {r}" for i, r in enumerate(refs, 1)], size=10, after=3)


# builds the whole deck in template order
def main():
    prs = Presentation(str(TEMPLATE))
    # copies are made from the untouched template slides first, from the back so indices stay valid
    for _ in range(8):
        duplicate(prs, 12)
    duplicate(prs, 10)
    duplicate(prs, 9)
    duplicate(prs, 7)
    title_slide(prs.slides[0])
    introduction(prs)
    background(prs)
    solution(prs)
    implementation(prs)
    outcomes(prs)
    summary(prs, 24)
    bibliography(prs, 25)
    prs.save(OUT)
    print("saved", OUT, len(prs.slides), "slides")


if __name__ == "__main__":
    main()
