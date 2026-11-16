# builds the a1 portrait project poster from the result files, figures and demo screenshots
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "report"))

import pandas as pd
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from pptx_helpers import (ALERT, CARD, GOOD, HEAD, INK, MUTED, PINK, TEAL, TEAL_LIGHT, WHITE, background, badge, bar_chart,
                          card, picture, screenshot, stat, text)

RES = ROOT / "results"
FIG, REP, DEMO = RES / "figures", RES / "figures" / "report", RES / "figures" / "demo"
OUT = ROOT / "report" / "Poster_A1.pptx"
W, H = 23.39, 33.11
M = 0.9


# section heading with a numbered badge
def section(s, x, y, w, n, title):
    badge(s, x, y + 0.05, n, d=0.75)
    text(s, x + 1.0, y, w - 1.0, 0.9, title, size=40, color=TEAL, bold=True, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)


# lays out every block of the poster
def main():
    summ = pd.read_csv(RES / "confirm_summary.csv").set_index("policy")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, WHITE)
    col = (W - 3 * M) / 2

    card(s, 0, 0, W, 4.0, fill=TEAL)
    card(s, M, 0.7, 5.2, 1.6, fill=WHITE)
    picture(s, ROOT / "report" / "assets" / "logo_0.png", M + 0.15, 0.8, 4.9, 1.4)
    text(s, M + 5.7, 0.55, W - 2 * M - 5.7, 2.4,
         "Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways", size=48, color=WHITE,
         bold=True, font=HEAD)
    text(s, M, 3.0, W - 2 * M, 0.6, "Arnav Gupta · Saugata Kumar Jana · Avishkar Maitra · Arpita Suresh Kulkarni   |   Guide: Dr. Sandipan Maiti   |   "
                                     "School of Computer Science and Engineering, VIT-AP University", size=24, color=TEAL_LIGHT)

    y = 5.0
    section(s, M, y, col, 1, "The problem")
    text(s, M, y + 1.1, col, 3.2, [
        "LLM gateways answer repeated requests from a semantic cache to save cost and seconds per call",
        "Existing caches (GPTCache, MeanCache, VectorQ, ContextCache) reuse an answer when one request looks similar enough",
        "But more than half of real chat turns refer to their own conversation: “make it shorter”, “continue”, “that is wrong”"],
         size=24, bullet=True, space_after=10)
    picture(s, REP / "act_distribution.png", M, y + 4.3, col, 3.9)
    x2 = 2 * M + col
    section(s, x2, y, col, 2, "Key finding: behavior decides reuse")
    stat(s, x2, y + 1.1, col / 2, "56.3%", "of 7,360 near-duplicates a similarity cache answers wrongly", color=ALERT,
         size=88, label_size=22)
    stat(s, x2 + col / 2 + 0.3, y + 1.35, col / 2 - 0.3, "75.7% vs 37.1%", "wrong for context-dependent vs self-contained "
         "requests", color=ALERT, size=40, label_size=22)
    picture(s, FIG / "wrong_reuse_by_act.png", x2, y + 4.0, col, 4.2)

    y = 13.6
    section(s, M, y, W - 2 * M, 3, "Method: mine behavior, decide by expected benefit")
    picture(s, REP / "block_diagram.png", M, y + 1.1, 13.0, 5.6)
    text(s, M + 13.4, y + 1.3, W - 2 * M - 13.4, 6.0, [
        [("Mine ", {"bold": True, "color": TEAL}), ("FP-Growth + PrefixSpan over dialogue acts and intents, daily, past traffic only", {})],
        [("State ", {"bold": True, "color": TEAL}), ("σ = longest frequent suffix of the session's act history", {})],
        [("Rule ", {"bold": True, "color": TEAL}), ("π(r) = (Σyᵢ + m·ȳ)/(nᵣ + m), r = (σ, act) of request and entry", {})],
        [("Decide ", {"bold": True, "color": TEAL}), ("B = U·q − L·(1 − q), serve if B ≥ θ", {})],
        [("Evaluate ", {"bold": True, "color": TEAL}), ("pre-registered, per-policy replay, matched wrong reuse, one frozen run", {})]],
         size=24, space_after=14)

    y = 20.7
    section(s, M, y, col, 4, "Result on the held-out period")
    pols = ["P1_fixed", "P2_per_intent", "P3_per_query", "P5_context", "P4_patterns"]
    bar_chart(s, M, y + 1.2, col, 3.6, ["P1 fixed threshold", "P2 per-intent", "P3 per-turn verifier",
                                        "P5 context embedding", "P4 mined patterns"],
              [summ.loc[p, "hit_at_wr10"] * 100 for p in pols], [MUTED, MUTED, GOOD, MUTED, PINK], size=20, max_value=6)
    text(s, M, y + 4.95, col, 1.8, [[("Hit rate at ≤10% wrong reuse. ", {"bold": True}),
                                    ("P4 vs P1: +1.10 / +4.47 points, significant (≈240×). P4 vs P3, P5: not significant, so "
                                     "the strict pre-registered criterion is not met.", {})]], size=22)
    section(s, x2, y, col, 5, "What the patterns change")
    picture(s, REP / "mechanism_all.png", x2, y + 1.1, col, 4.0)
    text(s, x2, y + 5.2, col, 1.6, [[("Corrections served wrong: ", {"bold": True}),
                                     ("2 of 3 for the per-turn and context policies, 0 of 1 with mined patterns. Context "
                                      "embedding was worst on follow-ups (3 of 10).", {})]], size=22)

    y = 27.6
    section(s, M, y, col, 6, "Demo: inspect every decision")
    screenshot(s, DEMO / "demo_inspect_blocked.png", M, y + 1.1, col, 3.4)
    section(s, x2, y, col, 7, "Honest negatives and checks")
    text(s, x2, y + 1.1, col, 3.4, [
        [("Routing: ", {"bold": True, "color": ALERT}), ("pattern router 61.9% vs random 62.1% (H1b not supported)", {})],
        [("Trajectory fast-track: ", {"bold": True, "color": ALERT}), ("only 4.8% would satisfy the user", {})],
        [("Positive control: ", {"bold": True, "color": GOOD}), ("planted effect recovered, 24.0% vs 5.7%", {})],
        [("Service: ", {"bold": True, "color": GOOD}), ("43 ms median decision on a laptop CPU", {})]], size=22, space_after=8)
    text(s, M, H - 0.7, W - 2 * M, 0.5, "Code and every result: github.com/arnnnavvvvv/llm-cache-pattern-mining · "
                                          "data: WildChat, LMSYS Arena · tag freeze-confirm-2026-11-16", size=18,
         color=MUTED, align=PP_ALIGN.CENTER)
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
