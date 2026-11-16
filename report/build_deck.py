# builds the final review (review 3) slide deck from the result files, figures and demo screenshots
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "report"))

import pandas as pd
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from pptx_helpers import (ALERT, BODY, CARD, GOOD, HEAD, INK, MUTED, PINK, TEAL, TEAL_LIGHT, WHITE, background, badge,
                          bar_chart, card, picture, screenshot, stat, text)

RES = ROOT / "results"
FIG, REP, DEMO = RES / "figures", RES / "figures" / "report", RES / "figures" / "demo"
OUT = ROOT / "report" / "Review3_Presentation.pptx"
TITLE = "Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways"
TEAM = "Arnav Gupta · Saugata Kumar Jana · Avishkar Maitra · Arpita Suresh Kulkarni"


# new content slide with the shared title position and a small page footer
def slide(prs, title, notes=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, WHITE)
    text(s, 0.6, 0.35, 12.1, 0.9, title, size=32, color=TEAL, bold=True, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 10.6, 7.0, 2.3, 0.35, f"Final Review · {len(prs.slides)}", size=10, color=MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


# dark slide used for the title, the conclusion and the closing
def dark(prs, notes=""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    background(s, TEAL)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


# the whole deck, one function per slide group
def main():
    summ = pd.read_csv(RES / "confirm_summary.csv").set_index("policy")
    lat = json.loads((RES / "service_latency.json").read_text())
    cost = pd.read_csv(RES / "llm_usage_cost.csv")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    s = dark(prs, "Introduce the team and the one-line idea: decide cache reuse from mined conversation behavior, not "
                  "just text similarity.")
    text(s, 0.8, 1.5, 11.7, 2.2, TITLE, size=40, color=WHITE, bold=True, font=HEAD)
    text(s, 0.8, 3.9, 11.7, 0.6, "Final Review (Review 3) · CAP4001 Capstone · Fall 2026-27", size=20, color=TEAL_LIGHT)
    text(s, 0.8, 5.0, 11.7, 0.5, TEAM, size=18, color=WHITE)
    text(s, 0.8, 5.5, 11.7, 0.5, "Guide: Dr. Sandipan Maiti · School of Computer Science and Engineering, VIT-AP University",
         size=16, color=TEAL_LIGHT)

    s = slide(prs, "Semantic caches reuse answers by similarity alone",
              "Gateways answer repeated requests from a cache to save cost and time. Every existing cache decides from "
              "similarity of one request. But over half of real chat turns depend on their conversation.")
    text(s, 0.6, 1.5, 5.6, 4.6, [
        "LLM gateways cache answers: a cache hit skips a provider call that costs money and seconds",
        "Semantic caches (GPTCache and successors) reuse an answer when a new request is similar enough to an old one",
        "But users iterate: “make it shorter”, “continue”, “that is wrong” only make sense inside their own conversation",
        "Question: can patterns mined from the traffic stream tell safe reuse from unsafe reuse?"],
         size=17, bullet=True, space_after=12)
    picture(s, REP / "act_distribution.png", 6.5, 1.5, 6.3, 4.6)

    s = slide(prs, "Hypothesis and what we set out to show",
              "H1 was pre-registered with two predictions and a stretch goal. Pass rule fixed before the final run.")
    items = [("H1a · Cache admission", "At the same rate of wrong cached answers (5%, 10%), mined patterns serve more "
                                       "requests than a fixed threshold, per-intent thresholds, a learned per-turn "
                                       "verifier and a context-embedding policy."),
             ("H1b · Model routing", "At the same budget for the expensive model, a pattern-aware router gives higher "
                                     "answer quality than per-query and context routers."),
             ("Stretch · Trajectory cache", "Fast-track a new conversation to the answer that satisfied users who started "
                                            "the same way.")]
    for i, (h, b) in enumerate(items):
        x = 0.6 + i * 4.1
        card(s, x, 1.6, 3.8, 4.4)
        badge(s, x + 0.3, 1.85, i + 1)
        text(s, x + 0.3, 2.5, 3.3, 0.8, h, size=19, color=TEAL, bold=True, font=HEAD)
        text(s, x + 0.3, 3.35, 3.3, 2.6, b, size=15)
    text(s, 0.6, 6.25, 12.1, 0.5, "Pass rule for H1a: P4 must beat P1, P2, P3 and P5 at both levels, after Holm correction, "
                                  "in one run on frozen code.", size=14, color=MUTED, align=PP_ALIGN.CENTER)

    s = slide(prs, "Real traffic, real answers, judged labels",
              "WildChat gives real conversations with the answer each user got. The judge sees that reference answer. "
              "Labels were stratified so the 89% we could afford is still a fair sample.")
    for i, (v, l) in enumerate([("30,015", "WildChat turns · 6,828 sessions"), ("10,776", "turns judged (88.9%, stratified)"),
                                ("85–88%", "agreement between three judge models")]):
        stat(s, 0.6, 1.5 + i * 1.65, 4.6, v, l, size=46)
    picture(s, REP / "label_coverage.png", 5.4, 1.5, 7.4, 3.5)
    text(s, 5.4, 5.15, 7.4, 1.4, ["Time-ordered split: train 60% · dev 20% · held-out confirm 20%",
                                  "Coverage 88.5–89.3% in every stratum; metrics reweighted to the full population"],
         size=14, bullet=True)

    s = slide(prs, "System: behavior-aware admission in the gateway",
              "Walk the online path left to right, then the offline loop that re-mines patterns daily from past traffic only.")
    picture(s, REP / "block_diagram.png", 0.6, 1.4, 12.1, 5.5)

    s = slide(prs, "From mined patterns to an admission decision",
              "Patterns give each turn a behavioral state. Rules over (state, act) of both sides of a reuse give a prior. "
              "The verifier turns everything into an expected benefit.")
    steps = [("Mine", "FP-Growth itemsets and PrefixSpan sequences over dialogue acts and intents, daily, past traffic only"),
             ("Place", "behavioral state σ = longest frequent suffix of the session's act history (start / … / rare)"),
             ("Rule", "π(r) = (Σ yᵢ + m·ȳ) / (nᵣ + m) for r = (σ request, act, σ entry, act)"),
             ("Decide", "q = f(z)·2^(−age/T),  B = U·q − L·(1 − q),  serve if B ≥ θ")]
    for i, (h, b) in enumerate(steps):
        y = 1.55 + i * 1.3
        badge(s, 0.6, y, i + 1)
        text(s, 1.3, y - 0.05, 1.4, 0.5, h, size=18, color=TEAL, bold=True, font=HEAD)
        text(s, 2.7, y - 0.05, 3.9, 1.2, b, size=14)
    picture(s, REP / "rules_bar.png", 6.8, 1.4, 6.0, 5.3)

    s = slide(prs, "A protocol built so the answer can be trusted",
              "Same stream, separate caches per policy, matched error levels, one frozen run. This is why negative results "
              "are reported as they are.")
    steps = [("Pre-register", "claims, comparators, pass rule and analyses written down first"),
             ("Replay", "every policy replays the stream with its own cache; served answers never re-enter it"),
             ("Match errors", "compare hit rate at the same wrong-reuse level (5%, 10%)"),
             ("Test", "1,000 session bootstraps, Holm correction, placebos, ablations, positive control"),
             ("Freeze", "code tagged freeze-confirm-2026-11-16; confirmation period evaluated once")]
    for i, (h, b) in enumerate(steps):
        x = 0.6 + i * 2.5
        card(s, x, 1.8, 2.3, 3.6)
        badge(s, x + 0.2, 2.0, i + 1)
        text(s, x + 0.2, 2.65, 2.0, 0.6, h, size=17, color=TEAL, bold=True, font=HEAD)
        text(s, x + 0.2, 3.25, 2.0, 2.1, b, size=14)
    text(s, 0.6, 5.8, 12.1, 0.8, "HR@α = max over thresholds of hit rate with wrong reuse ≤ α", size=18, color=INK,
         align=PP_ALIGN.CENTER, font=HEAD)

    s = slide(prs, "Finding: behavior, not similarity, decides safe reuse",
              "Below 0.97 similarity almost all reuse is wrong. Among near-duplicates the dialogue act splits safe from "
              "unsafe. This is the main novelty of the project.")
    picture(s, FIG / "wrong_reuse_by_act.png", 0.5, 1.4, 7.6, 4.3)
    stat(s, 8.5, 1.5, 4.3, "56.3%", "of 7,360 near-duplicates are served wrongly by a similarity cache", color=ALERT)
    stat(s, 8.5, 3.15, 4.3, "75.7%", "wrong when the request depends on context", color=ALERT, size=44)
    stat(s, 8.5, 4.6, 4.3, "37.1%", "wrong when it is self-contained", color=TEAL, size=44)
    text(s, 0.6, 6.0, 12.1, 0.6, "Same split on the cache side: answers from context-dependent turns are wrong 73.2% vs 42.2%.",
         size=14, color=MUTED)

    s = slide(prs, "H1a: 240× a fixed threshold, tied with learned policies",
              "P4 vs P1 is significant at both levels. Against P3 and P5 the intervals include zero, so the strict "
              "pre-registered criterion is not met.")
    pols = ["P1_fixed", "P2_per_intent", "P3_per_query", "P5_context", "P4_patterns"]
    names = ["P1 fixed threshold", "P2 per-intent", "P3 per-turn verifier", "P5 context embedding", "P4 mined patterns"]
    text(s, 0.6, 1.4, 5.8, 0.4, "Hit rate at ≤10% wrong reuse (held-out period)", size=14, color=MUTED)
    bar_chart(s, 0.6, 1.8, 5.8, 3.6, names, [summ.loc[p, "hit_at_wr10"] * 100 for p in pols],
              [MUTED, MUTED, GOOD, MUTED, PINK], size=13, max_value=6)
    picture(s, REP / "forest_main.png", 6.6, 1.4, 6.2, 4.2)
    card(s, 0.6, 5.75, 12.1, 0.95, fill=TEAL_LIGHT)
    text(s, 0.8, 5.8, 11.7, 0.85, [[("Verdict: ", {"bold": True, "color": TEAL}),
                                    ("P4 − P1 = +1.10 and +4.47 points (significant). P4 vs P3 / P5: not significant → "
                                     "H1a criterion not met. Per-turn dialogue acts already carry most of the gain.", {})]],
         size=15, anchor=MSO_ANCHOR.MIDDLE)

    s = slide(prs, "Mechanism: patterns change which requests are served",
              "Same volume, different requests. Corrections: P3 and P5 got 2 of 3 wrong, both pattern policies served one "
              "and got it right. Context embedding did worst on follow-ups. Counts are small, so this is descriptive.")
    picture(s, REP / "mechanism_all.png", 0.5, 1.4, 8.2, 4.6)
    stat(s, 9.0, 1.5, 3.8, "2/3 → 0/1", "corrections served wrong: per-turn and context policies vs pattern policies",
         color=PINK, size=40)
    stat(s, 9.0, 3.5, 3.8, "3/10", "follow-ups served wrong by the context-embedding policy", color=ALERT, size=40)
    text(s, 0.6, 6.2, 12.1, 0.6, "Adding context to similarity did not protect follow-ups; mined behavior refused reuse "
                                 "in states where it had historically failed.", size=14, color=MUTED)

    s = slide(prs, "Checks: placebos, ablations and a positive control",
              "No placebo or ablation differs from P3, consistent with the tie. The positive control proves the pipeline "
              "would have found a pattern effect if one existed.")
    picture(s, REP / "forest_controls.png", 0.5, 1.4, 6.6, 4.6)
    picture(s, REP / "positive_control.png", 7.3, 1.4, 5.5, 3.6)
    text(s, 7.3, 5.1, 5.5, 1.2, ["Planted effect recovered: 24.0% vs 5.7% hit at ≤10%",
                                 "Stricter similarity floor 0.80: P4 still beats P1 (+1.59 / +4.34)"], size=14, bullet=True)

    s = slide(prs, "What did not work: routing and trajectory fast-tracking",
              "Report the negatives plainly. Routing: all routers equal random. Trajectories: conversations that start "
              "alike end differently, the same behavioral effect at session level.")
    picture(s, REP / "routing_bars.png", 0.5, 1.4, 6.1, 3.6)
    picture(s, REP / "trajectory_curve.png", 6.8, 1.4, 6.0, 3.6)
    text(s, 0.6, 5.2, 6.0, 1.4, [[("H1b not supported: ", {"bold": True, "color": ALERT}),
                                  ("pattern router 61.9% vs random 62.1% at a 30% strong-model budget (1,377 conversations).", {})]],
         size=15)
    text(s, 6.8, 5.2, 6.0, 1.4, [[("Stretch not viable: ", {"bold": True, "color": ALERT}),
                                  ("only 4.8% of 83 judged fast-tracks would satisfy the user.", {})]], size=15)

    s = slide(prs, "Demo: replaying the held-out period",
              "Run streamlit run demo/app.py. Replay ends with exactly the confirmation-table numbers. Inspect shows an "
              "identical request that P3 served wrongly and P4 refused because of the mined rule.")
    screenshot(s, DEMO / "demo_replay_end.png", 0.6, 1.4, 5.9, 5.3)
    screenshot(s, DEMO / "demo_inspect_blocked.png", 6.8, 1.4, 5.9, 5.3)

    s = slide(prs, "Demo: live admission and operating point",
              "Type a fresh question and a follow-up into the live service; drag the wrong-reuse budget and read hit rates "
              "off the real curves.")
    screenshot(s, DEMO / "demo_live.png", 0.6, 1.4, 5.9, 5.3)
    screenshot(s, DEMO / "demo_operating_10.png", 6.8, 1.4, 5.9, 5.3)

    s = slide(prs, "Cost and latency",
              "All compute on one laptop CPU. Model cost is computed from logged token counts at the gateway's listed "
              "rates. Decision latency is tiny next to a provider call.")
    stat(s, 0.6, 1.5, 4.0, f"{lat['engine_ms_p50']:.0f} ms", "median admission decision (p95 79 ms), 3,000 cached entries")
    stat(s, 0.6, 3.25, 4.0, f"₹{cost['cost_inr'].sum():,.0f}", "model usage for labeling, at listed gateway rates", size=46)
    stat(s, 0.6, 4.95, 4.0, "₹0", "hardware: one laptop, no GPU", size=46)
    picture(s, REP / "judge_cost.png", 4.9, 1.4, 7.9, 4.4)
    text(s, 4.9, 5.9, 7.9, 0.8, "Mid-size judge chosen: 88.4% agreement with the largest model at under half its cost.",
         size=14, color=MUTED)

    s = slide(prs, "Threats to validity, stated up front",
              "Each threat and what we did about it. Human validation sheets are prepared and being filled by the team.")
    rows = [("LLM judge labels", "reference answer shown; 3 judges agree 85–88%; human gold set pending"),
            ("Act tagger", "LLM tags offline; live tagger macro-F1 0.55, below our 0.70 gate"),
            ("11% unlabeled", "stratified random order and population weights"),
            ("One corpus, two weeks", "time-based split, held-out later period"),
            ("Replay, not live users", "per-policy caches; served answers never cached"),
            ("Small per-act counts", "raw counts shown; mechanism labeled descriptive")]
    for i, (a, b) in enumerate(rows):
        y = 1.5 + i * 0.85
        card(s, 0.6, y, 12.1, 0.72, fill=CARD)
        text(s, 0.8, y, 3.6, 0.72, a, size=16, color=TEAL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 4.4, y, 8.2, 0.72, b, size=15, anchor=MSO_ANCHOR.MIDDLE)

    s = dark(prs, "Close with the finding and the practical rule, then future work.")
    text(s, 0.8, 0.6, 11.7, 0.9, "Conclusion", size=36, color=WHITE, bold=True, font=HEAD)
    text(s, 0.8, 1.6, 6.6, 4.8, [
        "Reuse safety is a behavioral question: near-duplicates are wrong 56.3% of the time, 75.7% for context-dependent turns",
        "Behavior-aware admission serves ~240× a fixed-threshold cache at the same error rate (significant)",
        "Mined patterns tie per-turn acts on volume but stop wrong reuse on corrections",
        "Routing and trajectory fast-tracking did not work at this scale — reported as such"],
         size=17, color=WHITE, bullet=True, space_after=14)
    card(s, 7.8, 1.6, 4.8, 4.6, fill=RGBColorDark())
    text(s, 8.1, 1.8, 4.3, 0.6, "Future work", size=20, color=WHITE, bold=True, font=HEAD)
    text(s, 8.1, 2.5, 4.3, 3.6, ["Human validation of judge and tagger", "Repetitive workloads and longer periods",
                                 "Better online act tagger", "Turn-level routing labels", "Live gateway deployment"],
         size=15, color=WHITE, bullet=True, space_after=8)

    s = dark(prs, "Questions.")
    text(s, 0.8, 2.6, 11.7, 1.2, "Thank you", size=54, color=WHITE, bold=True, font=HEAD, align=PP_ALIGN.CENTER)
    text(s, 0.8, 4.0, 11.7, 0.6, "github.com/arnnnavvvvv/llm-cache-pattern-mining", size=18, color=TEAL_LIGHT,
         align=PP_ALIGN.CENTER)
    prs.save(OUT)
    print("saved", OUT, len(prs.slides), "slides")


# slightly lighter teal for a card on the dark slides
def RGBColorDark():
    from pptx.dml.color import RGBColor
    return RGBColor(0x1A, 0x52, 0x53)


if __name__ == "__main__":
    main()
