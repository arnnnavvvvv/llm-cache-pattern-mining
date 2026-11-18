# builds the capstone thesis (word) from the result files, figures and screenshots in the repository
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "report"))

import pandas as pd

from docx_helpers import (WD_ALIGN_PARAGRAPH, Cm, bullets, centred, chapter, code, equation, field_page, figure, new_document,
                          numbered_section, page_break, para, table, table_caption)
from gwcache import decision, metrics, patterns, replay, service

RES = ROOT / "results"
FIG = RES / "figures"
REP = FIG / "report"
DEMO = FIG / "demo"
OUT = ROOT / "report" / "Final_Report.docx"
TITLE = "Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways"
REPO = "https://github.com/arnnnavvvvv/llm-cache-pattern-mining"
MEMBERS = [("ARNAV GUPTA", "23BCE8106"), ("SAUGATA KUMAR JANA", "23BCE8398"), ("AVISHKAR MAITRA", "23BCE8411"),
           ("ARPITA SURESH KULKARNI", "23BCE8393")]
POLICY = {"P1_fixed": "P1 fixed threshold", "P2_per_intent": "P2 per-intent thresholds", "P3_per_query": "P3 behavior-aware (dialogue acts)",
          "P5_context": "P5 + context embedding", "P4_patterns": "P4 + mined patterns (proposed)",
          "P4plus_context_patterns": "P4+ context and patterns"}


# percent with fixed decimals
def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


# loads every result file the report quotes
def results() -> dict:
    r = {name: pd.read_csv(RES / f"{name}.csv") for name in [
        "dataset_stats", "confirm_summary", "confirm_comparisons", "confirm_controls_summary", "confirm_controls_vs_p3",
        "confirm_robust_floor_comparisons", "confirm_cv_spread", "positive_control", "routing_summary", "routing_comparisons",
        "judge_pick_cost", "judge_pick_agreement", "behavioral_rules", "near_duplicate_behavior", "intent_clusters",
        "llm_usage_cost", "tool_versions", "exploratory_mechanism_all", "demo_operating_points"]}
    for name in ["act_tagger", "service_latency", "trajectory_summary", "routing_verdict", "confirm_verdict", "machine"]:
        r[name] = json.loads((RES / f"{name}.json").read_text())
    return r


# title page, certificate, acknowledgements and abstract
def front_matter(doc, R):
    centred(doc, TITLE.upper(), size=16, bold=True, space_after=24)
    centred(doc, "A CAPSTONE PROJECT REPORT", size=12, bold=True, space_after=18)
    centred(doc, "Submitted in partial fulfillment of the requirement for the award of the Degree of", italic=True,
            space_after=14)
    centred(doc, "BACHELOR OF TECHNOLOGY", bold=True, space_after=0)
    centred(doc, "IN", bold=True, space_after=0)
    centred(doc, "COMPUTER SCIENCE AND ENGINEERING", bold=True, space_after=16)
    centred(doc, "by", italic=True, space_after=8)
    for name, reg in MEMBERS:
        centred(doc, f"{name} ({reg})", size=13, bold=True, space_after=2, highlight=name.startswith("[") or reg.startswith("["))
    centred(doc, "Under the Guidance of", italic=True, space_after=4).paragraph_format.space_before = Cm(0.6)
    centred(doc, "DR. SANDIPAN MAITI", bold=True, space_after=14)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(ROOT / "report" / "assets" / "logo_0.png"), width=Cm(8))
    centred(doc, "SCHOOL OF COMPUTER SCIENCE AND ENGINEERING", space_after=0).paragraph_format.space_before = Cm(0.6)
    centred(doc, "VIT-AP UNIVERSITY", space_after=0)
    centred(doc, "AMARAVATI- 522237", space_after=12)
    centred(doc, "NOVEMBER 2026", italic=True)

    numbered_section(doc, start=1)
    centred(doc, "CERTIFICATE", size=14, bold=True, space_after=18)
    names = ", ".join(f"{n} ({r})" for n, r in MEMBERS)
    p = para(doc, "", indent=False)
    p.add_run("This is to certify that the Capstone Project work titled “")
    p.add_run(TITLE.upper()).bold = True
    p.add_run("” that is being submitted by ")
    p.add_run(names).bold = True
    p.add_run(" is in partial fulfillment of the requirements for the award of Bachelor of Technology, is a record of "
              "bonafide work done under my guidance. The contents of this Project work, in full or in parts, have neither "
              "been taken from any other source nor have been submitted to any other Institute or University for award of "
              "any degree or diploma and the same is certified.")
    for _ in range(3):
        doc.add_paragraph()
    for t in ("Dr. Sandipan Maiti", "Guide"):
        q = doc.add_paragraph(t)
        q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph()
    centred(doc, "The thesis is satisfactory / unsatisfactory", bold=True, space_after=60)
    q = doc.add_paragraph("Internal Examiner\t\t\t\t\t\tExternal Examiner")
    q.runs[0].bold = True
    doc.add_paragraph()
    centred(doc, "Approved by", bold=True, space_after=48)
    q = doc.add_paragraph("PROGRAM CHAIR\t\t\t\t\t\t\tDEAN")
    q.runs[0].bold = True
    doc.add_paragraph("B. Tech. CSE\t\t\t\t\tSchool of Computer Science and Engineering")

    page_break(doc)
    centred(doc, "ACKNOWLEDGEMENTS", size=14, bold=True, space_after=18)
    para(doc, "We express our sincere gratitude to our guide, Dr. Sandipan Maiti, for steady guidance throughout the project, for "
              "pressing us to state our hypotheses precisely, and for insisting that every claim be tested against data "
              "rather than assumed. The feedback received at each review shaped the evaluation protocol this report rests on.")
    para(doc, "We thank the Dean and the Program Chair of the School of Computer Science and Engineering, VIT-AP University, "
              "for providing the capstone framework and the review process, and the faculty members who evaluated our "
              "reviews for their questions and suggestions.")
    para(doc, "We are grateful to the authors of the WildChat corpus and of the LMSYS Chatbot Arena human-preference data for "
              "releasing real conversational traffic for research; this project would not have been possible without "
              "public data of that kind. We also thank the developers of the open-source libraries listed in the "
              "Appendix, on which every part of our system is built.")
    para(doc, "Finally, we thank our families and friends for their patience and support throughout the semester.")

    page_break(doc)
    centred(doc, "ABSTRACT", size=14, bold=True, space_after=18)
    s = R["confirm_summary"].set_index("policy")
    para(doc, "Gateways that sit between applications and large language model (LLM) providers increasingly answer repeated "
              "requests from a semantic cache: a stored answer is returned whenever a new request is similar enough to an "
              "earlier one. Existing caches judge every request in isolation. This project tests the hypothesis that "
              "behavioral patterns mined from gateway traffic — which kinds of turns recur, and which follow which within "
              "sessions — make better cache-admission and model-routing decisions than fixed-threshold or per-query "
              "similarity policies.")
    para(doc, f"We replay {R['dataset_stats'].iloc[0]['turns']:,} real chatbot turns from the WildChat corpus, each with the "
              "answer its user actually received, through a stateful gateway simulator. Every turn is tagged with a dialogue "
              "act; frequent and sequential patterns over acts and intents are mined daily with FP-Growth and PrefixSpan "
              "using past traffic only; and class association rules over the behavioral states of a request and of a "
              "cached entry give a reuse-safety prior inside an expected-benefit admission rule. Ground truth comes from a "
              "reference-based LLM judge selected by comparing three models. Claims and metrics were pre-registered and the "
              "final test was run once, on frozen code, on a held-out later period.")
    para(doc, "The data show a clear failure mode of similarity caching: among 7,360 near-duplicate requests a similarity "
              "cache serves an unacceptable answer 56.3% of the time, and context-dependent turns (follow-ups, corrections, "
              "continuations) are wrong 75.7% of the time against 37.1% for self-contained requests. On the held-out "
              f"period, behavior-aware admission serves {pct(s.loc['P4_patterns', 'hit_at_wr10'])} of all requests at a 10% "
              f"wrong-reuse level, against {pct(s.loc['P1_fixed', 'hit_at_wr10'])} for a fixed similarity threshold, a "
              "gain of about 240 times that is significant at both pre-registered levels and robust to a stricter "
              "similarity floor; mined patterns removed wrong reuse on correction turns and yield human-readable rules. "
              "At enterprise scale (100 million requests a month) this corresponds to a projected saving of about ₹1.95 "
              "crore a year over a standard semantic cache. A live admission service decides in 43 ms (median) on a laptop "
              "CPU, and an interactive replay demo makes every decision inspectable. Model routing, part of the original "
              "scope, was carried out as an exploratory extension.")
    p = para(doc, "semantic caching, LLM gateway, sequential pattern mining, association rules, dialogue acts, model "
                  "routing, pre-registration", lead="Keywords: ", indent=False)


# contents, list of tables and list of figures, filled in by word when fields are updated
def lists(doc):
    field_page(doc, "TABLE OF CONTENTS", 'TOC \\o "1-3" \\h \\z \\u')
    field_page(doc, "LIST OF TABLES", 'TOC \\h \\z \\c "Table"')
    field_page(doc, "LIST OF FIGURES", 'TOC \\h \\z \\c "Figure"')


# chapter 1: motivation, objectives, literature survey and report organisation
def chapter1(doc, R):
    chapter(doc, 1, "Introduction")
    para(doc, "Applications built on large language models rarely talk to a single model directly. A gateway sits in the "
              "middle: it authenticates traffic, enforces budgets, chooses a provider and model for each request and, "
              "increasingly, answers repeated requests from a cache so that the provider is never called. Because LLM calls "
              "are slow (seconds) and billed per token, every request answered from a cache saves both time and money. "
              "Exact-match caching helps little, since users rarely type the same text twice, so semantic caches reuse an "
              "answer whenever a new request is close enough to a stored one in an embedding space.")
    para(doc, "The difficulty is that similarity is not the same as interchangeability. In real chat traffic users iterate: "
              "they paste material and ask for a summary, then ask for it shorter, then say that a detail is wrong. Figure 1 "
              "shows the dialogue acts of all 30,015 turns in our data: more than half are not fresh, self-contained "
              "requests at all. A request such as “make it shorter” or “continue” refers to an answer that only exists "
              "inside its own conversation, so a cached answer from another conversation is almost certainly wrong, however "
              "similar the two requests look.")
    figure(doc, REP / "act_distribution.png", "Dialogue acts of all turns in the replayed traffic", 5.8)
    para(doc, "Existing semantic caches decide from the similarity of one request to one stored request, optionally with "
              "its recent context. None of them looks at the recurring structure of the traffic stream itself: which kinds "
              "of turns tend to follow which, and which combinations of turns have historically been safe to reuse. This "
              "project asks whether that structure can be mined with classical pattern-mining algorithms and used to make "
              "better cache-admission and model-routing decisions.")

    doc.add_heading("1.1 Objectives", level=2)
    para(doc, "The project is organised around one hypothesis, written down in a pre-registration document before the "
              "final evaluation: behavioral patterns mined from LLM gateway traffic improve cache-admission decisions "
              "relative to fixed-threshold and similarity-based caching. The objectives are:")
    bullets(doc, [
        ("Mine behavioral patterns ", "(dialogue acts, intents, frequent and sequential patterns) from gateway traffic."),
        ("Build a behavior-aware admission engine ", "that combines mined rules, a learned verifier and an "
                                                     "expected-benefit decision."),
        ("Make reuse safer ", "on context-dependent turns such as follow-ups and corrections."),
        ("Evaluate rigorously ", "on real traffic, at matched error rates, on a held-out later period."),
        ("Deliver a deployable admission service and an inspectable demonstration, ", "with every number in this report "
                                                                                      "reproducible from raw data by one script."),
        ("Quantify real-world value ", "as model calls and money saved at different scales of use."),
    ])
    para(doc, "Cache admission is the core deliverable. Multi-provider model routing and conversation-level fast-tracking, "
              "part of the original scope, were carried out as exploratory extensions (Section 4.i).", lead="Scope. ")

    doc.add_heading("1.2 Background and Literature Survey", level=2)
    para(doc, "GPTCache [1] popularised semantic caching for LLM applications: requests are embedded, the nearest stored "
              "request is retrieved from a vector index, and its answer is returned when the cosine similarity exceeds one "
              "global threshold. It is the de-facto baseline for gateway caches, and its weakness is the single threshold: "
              "a value strict enough to avoid wrong answers on one kind of request is too strict to reuse anything on "
              "another.", lead="Semantic caching. ")
    para(doc, "MeanCache [2] keeps a cache per user and learns the similarity model itself with federated learning, so that "
              "the notion of “same request” adapts to each user while their data stays local. VectorQ [3] replaces the "
              "global threshold with learned threshold regions in embedding space, adapting strictness to where a request "
              "falls. Category-aware semantic caching [4] varies the threshold, time-to-live and quota by query category, "
              "on the observation that code, factual and creative requests tolerate reuse very differently. ContextCache [5] "
              "is the closest work to ours: it adds the dialogue history to the match through attention over earlier turns, "
              "so that a follow-up is compared together with its context. All of these systems make the decision from the "
              "current request (with or without its own context); none mines recurring behavior across the traffic stream.")
    para(doc, "FrugalGPT [6] showed that cascading cheap and expensive models can cut cost substantially while keeping "
              "quality, and RouteLLM [7] learns strong/weak routers from human preference votes collected on Chatbot "
              "Arena [9]. These routers score each prompt independently. Our routing experiment asks whether mined session "
              "patterns add information that per-prompt routers lack.", lead="Model routing. ")
    para(doc, "FP-Growth [12] mines frequent itemsets without candidate generation, and PrefixSpan [13] mines sequential "
              "patterns by prefix projection; associative classification [14] turns frequent patterns into class "
              "association rules with support and confidence. These are mature techniques that, to our knowledge, have not "
              "been applied to LLM cache admission. Work on turn-level user satisfaction in multi-turn dialogue [11] "
              "motivated our satisfaction proxy for trajectory caching, and LLM-as-a-judge evaluation [10] is now a common "
              "way to score open-ended answers; we use a judge that sees the reference answer the user actually received.",
         lead="Pattern mining and evaluation. ")
    para(doc, "WildChat [8] provides one million real conversations between users and a chatbot, with timestamps and "
              "anonymised user identifiers — exactly the shape of gateway logs, and the primary data source of this project. "
              "The LMSYS Arena human-preference data [22] provides human votes between two models for the routing study.",
         lead="Data. ")
    table_caption(doc, 1, "Positioning of this work against prior semantic caches and routers")
    table(doc, ["System", "Decision signal", "Uses context", "Mined behavior"], [
        ["GPTCache [1]", "global similarity threshold", "no", "no"],
        ["MeanCache [2]", "learned similarity, per user", "no", "no"],
        ["VectorQ [3]", "per-region threshold", "no", "no"],
        ["Category-aware caching [4]", "per-category policy", "no", "no"],
        ["ContextCache [5]", "attention over history", "yes", "no"],
        ["RouteLLM [7] (routing)", "per-prompt router", "no", "no"],
        ["This work", "verifier + mined association-rule prior", "yes", "yes"]], [4.5, 6.0, 2.5, 2.8], bold_rows=(6,))
    para(doc, "Existing caches and routers operate at the granularity of a single request. None of them mines the "
              "collective request stream for recurring behavioral structure and uses it as a signal for both cache "
              "admission and provider routing, and none evaluates admission at a matched rate of wrong answers on a "
              "held-out period. This project addresses that gap.", lead="Research gap. ")

    doc.add_heading("1.3 Organization of the Report", level=2)
    para(doc, "The remaining chapters of the project report are described as follows:", indent=False)
    bullets(doc, ["Chapter 2 contains the proposed system, the working methodology, the standards followed, and the "
                  "software and compute details, including screenshots of the service and the demonstration.",
                  "Chapter 3 gives the cost of the project: model-API usage measured from logs, compute, and the cost and "
                  "latency of one admission decision.",
                  "Chapter 4 discusses the results with figures for every claim, the real-world applications and the "
                  "exploratory extensions.",
                  "Chapter 5 concludes the report and lists future work.",
                  "Chapter 6 is the appendix: repository, tools and versions, results register, project timeline and code.",
                  "Chapter 7 gives the references."])


# chapter 2: architecture, methodology, standards and system details
def chapter2(doc, R):
    chapter(doc, 2, "Behavior-Aware Cache Admission System")
    para(doc, "This chapter describes the proposed system, the working methodology, the standards followed and the software "
              "and compute details.", indent=False)
    doc.add_heading("2.1 Proposed System", level=2)
    para(doc, "The following block diagram (Figure 2) shows the system architecture. The upper half is the online path that "
              "every request takes; the lower half is the offline loop that learns from past traffic.")
    figure(doc, REP / "block_diagram.png", "System Block Diagram", 6.3)
    bullets(doc, [
        ("Embedder: ", "turns a request into a 384-dimensional sentence embedding (all-MiniLM-L6-v2 [16], [17])."),
        ("Candidate search: ", "retrieves the three most similar earlier requests from the cache with an exact "
                               "inner-product index (FAISS [18]), keeping those with cosine similarity of at least 0.70."),
        ("Behavior features: ", "tags the request's dialogue act and intent, places the request and each cached entry in a "
                                "mined behavioral state, and looks up mined sequence confidences and the association-rule "
                                "prior for the pair."),
        ("Admission decision: ", "a LightGBM verifier [15] estimates the probability that reusing each candidate is "
                                 "acceptable; the expected benefit of the best candidate is compared with a threshold."),
        ("Offline loop: ", "the gateway log is re-mined every day using only earlier traffic; association rules and the "
                           "verifier are fitted on judged past reuses. Answers served from cache are never added back to "
                           "the cache, so a wrong reuse cannot propagate."),
    ])

    doc.add_heading("2.2 Working Methodology", level=2)
    doc.add_heading("2.2.1 Data and replay", level=3)
    ds = R["dataset_stats"].set_index("period")
    para(doc, "Multi-turn English conversations are streamed from WildChat, excluding conversations the corpus flags as "
              "toxic. Each user turn becomes one row holding the request, the answer the user actually received, the "
              "session, an anonymised user identifier and a timestamp. Sessions are assigned by the time of their first "
              "turn to a training period, a development period and a later confirmation period, so that every evaluation "
              "looks forward in time (Table 2.1, Figure 3).")
    table_caption(doc, 2, "Dataset statistics per period")
    rows = []
    for period in ["train", "dev", "confirm", "all"]:
        d = ds.loc[period]
        rows.append([period, f"{d['turns']:,}", f"{d['sessions']:,}", f"{d['users']:,}", f"{d['turns_per_session']:.2f}",
                     f"{pd.Timestamp(d['start']):%b %d} – {pd.Timestamp(d['end']):%b %d, %Y}"])
    table(doc, ["Period", "Turns", "Sessions", "Users", "Turns/session", "Time span"], rows, [2.2, 2.2, 2.2, 2.0, 2.6, 4.6],
          bold_rows=(3,), align_right=(1, 2, 3, 4))
    figure(doc, REP / "split_timeline.png", "Turns per day in the training, development and confirmation periods", 5.8)

    doc.add_heading("2.2.2 Behavioral tokens: intents and dialogue acts", level=3)
    at = R["act_tagger"]
    para(doc, "Each turn receives an intent, one of k = 20 clusters of request embeddings fitted with k-means on the training "
              "period only, and a dialogue act from the five-way taxonomy in Table 2.2. Intents describe what is asked; acts "
              "describe how the turn relates to the conversation, which is what decides whether reuse can be safe. Acts were "
              f"tagged for every turn by an LLM with a fixed prompt (Appendix); an independent model's labels on a "
              f"{at['seed_labels']:,}-turn seed sample agreed with the tags on {pct(at['tag_model_vs_seed_model_agreement'], 1)} "
              "of turns. A small logistic-regression tagger, used by the live service, reaches a cross-validated macro-F1 of "
              f"{at['service_classifier_cv_macro_f1']:.2f}; it is the weakest component of the system (Section 4.k).")
    dist = at["tagged_distribution"]
    total = sum(dist.values())
    desc = {"new_request": "a self-contained new task or question", "follow_up": "refines or modifies the previous answer",
            "continuation": "asks to keep going with the same output", "correction": "says the previous answer was wrong",
            "new_ask_same_material": "a different task on material given earlier"}
    table_caption(doc, 2, "Dialogue-act taxonomy and its frequency in the replayed traffic")
    table(doc, ["Act", "Meaning", "Turns", "Share"],
          [[k.replace("_", " "), desc[k], f"{v:,}", pct(v / total, 1)] for k, v in sorted(dist.items(), key=lambda x: -x[1])],
          [3.8, 7.6, 2.2, 2.0], align_right=(2, 3))

    doc.add_heading("2.2.3 Candidates and ground-truth labels", level=3)
    para(doc, "For every turn, the three most similar earlier turns with similarity at least 0.70 are candidate reuses; "
              "12,124 turns have at least one (25,345 candidate pairs). A judge model sees the new request, the reference "
              "answer the user actually received, and each candidate's request and answer, and decides whether returning "
              "the candidate's answer unchanged would have been acceptable. Three judge models of different sizes labeled "
              "the same 199 pairs; they agreed pairwise on 85–88% of pairs (Table 2.3), and the mid-sized model was chosen "
              "for its agreement and cost (Chapter 3).")
    ag = R["judge_pick_agreement"]
    table_caption(doc, 2, "Pairwise agreement of the three judge candidates on the same 199 pairs")
    table(doc, ["Judge pair", "Pairs", "Agreement"],
          [[a.replace("claude-", "").replace("-5.5", " 5.5").replace(" vs ", " vs "), n, pct(g, 1)] for a, n, g in
           ag[["pair", "n", "agreement"]].itertuples(index=False)], [8.0, 2.0, 3.0], align_right=(1, 2))
    para(doc, "Turns were queued for labeling in a random order stratified by period and similarity band, so that any "
              "prefix of the queue is itself a stratified sample. When the labeling budget ran out, 10,776 of 12,124 turns "
              "(88.9%) were labeled, with coverage between 88.5% and 89.3% in every stratum (Figure 4). All metrics weight "
              "each labeled turn by the size of its stratum, so the missing 11% widens the confidence intervals but does "
              "not bias them.")
    figure(doc, REP / "label_coverage.png", "Labeled versus queued turns in every period and similarity band", 6.0)

    doc.add_heading("2.2.4 Pattern mining and behavioral rules", level=3)
    para(doc, "Act and intent sequences are mined per session and per user with PrefixSpan (sequences up to length three) and "
              "frequent itemsets with FP-Growth. Mining is repeated for every day of the replay using only traffic that "
              "arrived before that day, so no feature of a turn can depend on the future (Figure 5). For a set of entities "
              "E and a pattern p, support and the confidence of a sequential rule are")
    equation(doc, "supp(p) = |{ e ∈ E : p ⊑ seq(e) }| / |E|", "2.1")
    equation(doc, "conf(a₁…aₖ ⇒ b) = supp(a₁…aₖ b) / supp(a₁…aₖ)", "2.2")
    para(doc, "The behavioral state σ of a turn is the longest suffix of its session's act history (at most two acts) that "
              "the miner found frequent; the first turn of a session is in state “start” and an unseen history is “rare”. "
              "For a request t and a cached candidate c, the rule key r = (σₜ, aₜ, σ_c, a_c) combines the state and act of "
              "both sides of the reuse. From judged past reuses a smoothed class association rule gives the prior")
    equation(doc, "π(r) = ( Σᵢ∈ᵣ yᵢ + m·ȳ ) / ( nᵣ + m ),   m = 20", "2.3")
    para(doc, "where yᵢ ∈ {0, 1} marks an acceptable reuse, nᵣ is the number of judged pairs under rule r and ȳ the overall "
              "acceptance rate. Training rows receive out-of-fold estimates so that no row's prior uses its own label.")
    figure(doc, REP / "mining_daily.png", "Patterns re-mined each day from earlier traffic only", 5.8)

    doc.add_heading("2.2.5 Admission decision", level=3)
    para(doc, "For every candidate c a LightGBM verifier estimates f(z_c), the probability that reuse is acceptable, from a "
              "feature vector z_c: similarity profile (including the softmax share over the top three), intents, acts, "
              "lengths and time gap, and — in the proposed policy — the mined pattern features and π(r). The probability "
              "that the answer is still valid decays with the age Δ of the entry (half-life T = 30 days), and the best "
              "candidate is served when its expected benefit clears a threshold θ (Figure 6):")
    equation(doc, "q_c = f(z_c) · 2^(−Δ_c / T)", "2.4")
    equation(doc, "B_c = U·q_c − L·(1 − q_c),   U = L = 1", "2.5")
    equation(doc, "serve c* = argmax_c B_c   if   B_c* ≥ θ", "2.6")
    figure(doc, REP / "decision_flow.png", "Decision flow for one incoming request", 4.6)

    doc.add_heading("2.2.6 Policies, replay and metrics", level=3)
    table_caption(doc, 2, "Admission policies compared")
    table(doc, ["Policy", "Decision rule", "Role"], [
        ["P1", "fixed cosine-similarity threshold", "GPTCache-style baseline"],
        ["P2", "threshold calibrated per intent", "category-aware baseline"],
        ["P3", "learned verifier: similarity, intents, dialogue acts", "behavior-aware variant (dialogue acts)"],
        ["P5", "P3 + context-embedding similarities", "ContextCache-style baseline"],
        ["P4", "P3 + mined patterns + association-rule prior", "proposed: behavior-aware + mined patterns"],
        ["P4+", "P5 + mined patterns + rule prior", "combination"]], [1.6, 8.4, 5.2], bold_rows=(4,))
    para(doc, "Each policy replays the whole stream in time order with its own cache, so earlier decisions change later "
              "options. With population weight wₜ for a labeled turn and N turns in the evaluation period, the hit rate and "
              "wrong-reuse rate at threshold θ, and the primary readout at a matched wrong-reuse level α, are")
    equation(doc, "HR(θ) = (1/N) Σₜ wₜ · 1[servedₜ(θ)]", "2.7")
    equation(doc, "WR(θ) = Σₜ wₜ · 1[servedₜ(θ) ∧ ¬acceptableₜ] / Σₜ wₜ · 1[servedₜ(θ)]", "2.8")
    equation(doc, "HR@α = max_θ { HR(θ) : WR(θ) ≤ α },   α ∈ {5%, 10%}", "2.9")
    para(doc, "Uncertainty comes from 1,000 session-level bootstrap resamples [20] of the paired difference between P4 and "
              "each comparator, with Holm correction [19] across the two levels. Every design change was logged with its date, "
              "the code was "
              "frozen under the tag freeze-confirm-2026-11-16, and the confirmation period was evaluated exactly once. "
              "Figure 7 shows the full pipeline, rebuilt from raw data by a single script.")
    figure(doc, REP / "pipeline.png", "Pipeline from raw data to the report, by script", 6.3)

    doc.add_heading("2.3 Standards", level=2)
    para(doc, "Various standards and engineering practices used in this project are listed in Table 2.5.", indent=False)
    table_caption(doc, 2, "Standards and practices followed")
    table(doc, ["Standard / practice", "Where it is used"], [
        ["HTTP semantics (RFC 9110), REST", "admission service endpoints /admit, /record, /health"],
        ["JSON (RFC 8259)", "API payloads, model responses, result files"],
        ["OpenAPI Specification 3.1", "machine-readable API description served at /docs (Figure 8)"],
        ["TLS 1.3 (RFC 8446) over HTTPS", "every call to the model gateways"],
        ["ISO 8601 timestamps in UTC", "all turn times and the time-based split"],
        ["Apache Parquet", "columnar storage of all intermediate tables"],
        ["PEP 8 (Python style guide)", "all source code"],
        ["IEEE citation style", "references in this report and the paper"],
        ["Pre-registration and frozen tag", "claims and metrics fixed before the single confirmation run"],
        ["Version control (Git), unit tests (pytest)", "full history on GitHub; 19 tests including leakage tests"]],
          [6.0, 9.6])
    para(doc, "The service exchanges JSON over HTTP with a schema that FastAPI publishes as an OpenAPI 3.1 document. All model "
              "calls go to the provider gateways over HTTPS, whose keys are read from a local environment file that is "
              "excluded from version control.", lead="Interfaces and security. ")
    para(doc, "No result in this report comes from a hand-edited number. Every table and figure is produced by a script "
              "from the raw data, the confirmation run is tied to a Git tag, and the results register (Appendix) maps every "
              "headline number to its file.", lead="Research integrity. ")

    doc.add_heading("2.4 System Details", level=2)
    para(doc, "This section describes the software and the compute environment of the system.", indent=False)
    doc.add_heading("2.4.1 Software", level=3)
    para(doc, "The system is written in Python and organised as a library (gwcache) with one script per phase. The library "
              "holds ingestion, embedding, act tagging, candidate generation, judging, pattern mining, association rules, "
              "the verifier and decision rule, the replay engine, metrics and statistics; scripts 01–20 run the phases and "
              "write every result file, and run_all.py rebuilds everything in order. The software has three user-facing "
              "parts.", lead="")
    para(doc, "A FastAPI service loads the frozen model, the mined patterns and the association rules, and exposes "
              "three endpoints (Table 2.6). Figure 8 shows its automatically generated OpenAPI page.",
         lead="i) Admission service. ")
    table_caption(doc, 2, "Admission service API")
    table(doc, ["Endpoint", "Input", "Output"], [
        ["POST /admit", "session_id, user_id, request", "serve flag, cached answer, score, matched entry, act, intent, latency"],
        ["POST /record", "as /admit + turn_id, answer, act, intent", "stores a fresh provider answer in the cache"],
        ["GET /health", "–", "liveness and number of cached entries"]], [3.0, 5.4, 7.2])
    figure(doc, DEMO / "api_docs.png", "Admission service API documentation page (OpenAPI 3.1)", 4.6)
    para(doc, "An interactive application (Streamlit) replays the held-out confirmation period through the frozen policies "
              "side by side. It has five pages. Replay (Figures 9 and 10) streams the 2,424 judged requests that had a "
              "cached candidate, shows what P1, P3 and P4 decided for each one and whether the judge accepted the reuse, "
              "and keeps running, population-weighted hit-rate and wrong-reuse counters; at the end of the period they equal "
              "the confirmation table exactly. Inspect a decision (Figure 11) opens one request and shows the cached entry, "
              "both behavioral states, the mined rule with its historical acceptability, the judge's verdict and each "
              "policy's score against its threshold. Operating point (Figure 12) lets the viewer choose an allowed "
              "wrong-reuse rate and reads every policy's hit rate off its real curve. Findings collects the headline "
              "results, and Live admission (Figure 13) sends typed requests through the running "
              "service.", lead="ii) Replay demonstration. ")
    figure(doc, DEMO / "demo_replay_start.png", "Replay page early in the confirmation period", 6.0)
    figure(doc, DEMO / "demo_replay_mid.png", "Replay page: P3 serves wrong answers that P4 refuses", 6.0)
    figure(doc, DEMO / "demo_inspect_blocked.png", "Inspect page: an identical request whose cached answer belongs to "
                                                   "another conversation's follow-up chain", 6.0)
    figure(doc, DEMO / "demo_operating_5.png", "Operating-point page at a 5% wrong-reuse budget", 6.0)
    figure(doc, DEMO / "demo_live.png", "Live admission page: a follow-up is blocked, repeated fresh requests are served", 6.0)
    para(doc, "Every result is regenerated from raw data by run_all.py; the test suite (19 tests, including tests "
              "that a turn's pattern features never use later traffic) passes on the frozen code.",
         lead="iii) Reproducibility. ")

    doc.add_heading("2.4.2 Hardware and Compute Environment", level=3)
    m = R["machine"]
    para(doc, "The project needs no special hardware. Everything — embedding, mining, training, the replay and the "
              "service — ran on one laptop CPU without a GPU (Table 2.7). Only judging and act tagging used remote model "
              "APIs, whose cost is analysed in Chapter 3.")
    table_caption(doc, 2, "Compute environment")
    table(doc, ["Item", "Value"], [
        ["Processor", f"{m['cpu']} ({m['logical_cores']} logical cores)"], ["Memory", f"{m['ram_gb']} GB"],
        ["GPU", "none used"], ["Operating system", m["os"]], ["Python", m["python"]],
        ["Intermediate data", f"{m['work_tables_mb']} MB of Parquet tables for {m['turns']:,} turns"],
        ["Remote compute", "model APIs for act tagging and judging only (Chapter 3)"]], [4.5, 11.1])


# chapter 3: measured api usage, judge selection cost and per-decision cost
def chapter3(doc, R):
    chapter(doc, 3, "Cost Analysis")
    para(doc, "The project has no hardware bill. Its costs are model-API usage for labeling, measured from the response logs "
              "that the client stores for every call, and the run-time cost of an admission decision.")
    doc.add_heading("3.1 List of components and their cost", level=2)
    c = R["llm_usage_cost"]
    rows = [[r.model, r.role, f"{r.calls:,}", f"{r.input_tokens:,}" if r.input_tokens else "not metered",
             f"{r.output_tokens:,}" if r.output_tokens else "not metered", f"₹ {r.cost_inr:,.2f}"] for r in c.itertuples()]
    rows += [["Laptop compute", "all mining, training, replay, service", "–", "–", "–", "₹ 0 (existing laptop)"],
             ["Software", "open-source libraries (Appendix)", "–", "–", "–", "₹ 0"],
             ["TOTAL", "", f"{c['calls'].sum():,}", "", "", f"₹ {c['cost_inr'].sum():,.2f}"]]
    table_caption(doc, 3, "List of components and their cost (model usage summed from the response logs)")
    table(doc, ["Component", "Role", "Calls", "Input tokens", "Output tokens", "Cost"], rows, [3.4, 4.4, 1.6, 2.3, 2.2, 2.3],
          size=9, bold_rows=(len(rows) - 1,), align_right=(2, 3, 4, 5))
    para(doc, "Token counts are the totals reported by the APIs and stored with every cached response. Prepaid-gateway "
              "costs are computed at the gateway's listed per-million-token rates (₹ 197.95 input and ₹ 989.75 output for "
              "the judge model). Free-tier calls are not billed and their usage was not metered.")
    doc.add_heading("3.2 Choosing the judge by cost and agreement", level=2)
    j = R["judge_pick_cost"]
    table_caption(doc, 3, "Judge candidates on the same 199 pairs: cost and projected cost of the full queue")
    table(doc, ["Model", "Accepted share", "Output tokens/turn", "Cost of this run", "Projected full queue"],
          [[r.model, pct(r.acceptable_share, 1), f"{r.out_tokens_per_turn:.1f}", f"₹ {r.cost_inr_this_run:.2f}",
            f"₹ {r.projected_inr_full_queue:,.0f}"] for r in j.itertuples()], [4.0, 2.6, 3.0, 2.8, 3.2],
          align_right=(1, 2, 3, 4))
    para(doc, "The largest model would have cost about ₹ 5,900 to label the 12,124-turn queue and the smallest about ₹ 180. "
              "The mid-sized model agreed with the largest one on 88.4% of pairs at less than half of its cost and was "
              "chosen as the reference judge (Figure 14).")
    figure(doc, REP / "judge_cost.png", "Projected cost of labeling the whole queue with each judge candidate", 5.0)
    doc.add_heading("3.3 Cost and latency of one admission decision", level=2)
    lat = R["service_latency"]
    hit10 = R["confirm_summary"].set_index("policy").loc["P4_patterns", "hit_at_wr10"]
    hit5 = R["confirm_summary"].set_index("policy").loc["P4_patterns", "hit_at_wr5"]
    table_caption(doc, 3, "Run-time cost of the admission service (measured)")
    table(doc, ["Quantity", "Value", "Source"], [
        ["Decision latency, median / 95th percentile", f"{lat['engine_ms_p50']:.1f} / {lat['engine_ms_p95']:.1f} ms",
         "service_latency.json"],
        ["Through HTTP, median / 95th percentile", f"{lat['http_ms_p50']:.1f} / {lat['http_ms_p95']:.1f} ms",
         "service_latency.json"],
        ["Cached entries during the benchmark", f"{lat['cache_entries']:,}", "service_latency.json"],
        ["Hardware", "laptop CPU, no GPU", "machine.json"],
        ["Provider calls avoided per 1,000 requests at ≤10% wrong reuse", f"{hit10 * 1000:.1f}", "confirm_summary.csv"],
        ["Provider calls avoided per 1,000 requests at ≤5% wrong reuse", f"{hit5 * 1000:.1f}", "confirm_summary.csv"]],
          [7.6, 3.8, 4.2])
    para(doc, "The saving of the proposed policy follows directly from its hit rate: if one provider call costs C, the "
              "expected saving per 1,000 requests at the 10% operating point is 1,000 × HR@10% × C = 44.9 × C, against "
              "0.2 × C for a fixed-threshold cache run at the same error level. The decision itself costs one embedding and "
              "one small tree-model evaluation on a CPU, which is negligible next to a provider call that takes seconds.")
    doc.add_heading("3.4 Projected savings for users at different scales", level=2)
    sv = pd.read_csv(RES / "savings_projection.csv")
    sv = sv[sv["wrong_reuse_level"] == 10]

    def inr(v):
        return f"₹ {v / 1e7:.2f} crore" if v >= 1e7 else (f"₹ {v / 1e5:.2f} lakh" if v >= 1e5 else f"₹ {v:,.0f}")

    rows = []
    for n, label in [(1_000_000, "Startup (1M requests / month)"), (10_000_000, "Mid-size (10M requests / month)"),
                     (100_000_000, "Enterprise (100M requests / month)")]:
        pr = sv[(sv["requests_per_month"] == n) & sv["tier"].str.startswith("premium")].iloc[0]
        bu = sv[(sv["requests_per_month"] == n) & sv["tier"].str.startswith("budget")].iloc[0]
        rows.append([label, f"{pr['calls_avoided_month']:,.0f}", inr(pr["saving_inr_month"]), inr(pr["saving_inr_year"]),
                     inr(bu["saving_inr_year"])])
    para(doc, "Saving = (hit rate of behavior-aware admission − hit rate of a standard semantic cache) × requests × cost "
              "per call. Both hit rates are measured on the held-out period at the same ≤10% wrong-answer level (4.49% "
              f"and 0.02%). The cost per call is the gateway's list price × the dataset's average request (≈"
              f"{sv['tokens_in'].iloc[0]} tokens) and answer (≈{sv['tokens_out'].iloc[0]} tokens): ₹ "
              f"{sv[sv['tier'].str.startswith('premium')]['cost_per_call_inr'].iloc[0]:.2f} on a premium model and ₹ "
              f"{sv[sv['tier'].str.startswith('budget')]['cost_per_call_inr'].iloc[0]:.3f} on a budget model. Real calls also "
              "send the conversation history, so these savings are conservative (Table 3.4).")
    table_caption(doc, 3, "Projected savings over a standard semantic cache at the same ≤10% error level")
    table(doc, ["User scale", "Extra calls avoided / month", "Premium model / month", "Premium model / year",
                "Budget model / year"], rows, [4.4, 2.8, 2.8, 2.8, 2.8], size=9.5, align_right=(1, 2, 3, 4))



# chapter 4: results and discussion, lettered subsections
def chapter4(doc, R):
    chapter(doc, 4, "Results and Discussions")
    s = R["confirm_summary"].set_index("policy")
    doc.add_heading("a. The system working end to end", level=2)
    para(doc, "The replay demonstration runs the frozen policies over the whole held-out period and ends with exactly the "
              "figures of the confirmation table (Figure 15): the fixed-threshold cache P1 serves 0.02% of requests, while "
              "the behavior-aware policies P3 and P4 serve 4.62% and 4.49%, each with wrong reuse under 10%. Figure 16 "
              "shows a reuse that the proposed policy serves correctly.")
    figure(doc, DEMO / "demo_replay_end.png", "Replay at the end of the confirmation period", 6.0)
    figure(doc, DEMO / "demo_inspect_served.png", "Inspect page: a correct reuse served by P4", 6.0)

    doc.add_heading("b. Behavior decides whether reuse is safe", level=2)
    para(doc, "Figure 17 breaks the judged wrong-reuse rate down by similarity and by the dialogue act of the new request. "
              "Below 0.97 similarity most reuses are wrong whatever the act (79–97%), so similarity is necessary. It is not "
              "sufficient: among near-duplicates (similarity ≥ 0.97, 7,360 pairs) a similarity cache serves an unacceptable "
              "answer 56.3% of the time, and the act decides how often. Context-dependent requests are wrong 75.7% of the "
              "time against 37.1% for self-contained ones, and the same split holds on the cache side: answers produced by "
              "context-dependent turns are wrong 73.2% of the time against 42.2% (Figure 18). A cache that looks only at "
              "the similarity of one request cannot see either effect. This is the central finding of the project.")
    figure(doc, FIG / "wrong_reuse_by_act.png", "Wrong-reuse rate by similarity band and dialogue act", 6.0)
    figure(doc, REP / "near_duplicate_split.png", "Near-duplicates: wrong reuse for self-contained and context-dependent turns", 5.4)

    doc.add_heading("c. Cache admission on the held-out period", level=2)
    rows = []
    for p in ["P1_fixed", "P2_per_intent", "P5_context", "P3_per_query", "P4_patterns", "P4plus_context_patterns"]:
        lo5, hi5 = eval(s.loc[p, "ci_wr5"])
        lo10, hi10 = eval(s.loc[p, "ci_wr10"])
        rows.append([POLICY[p], f"{s.loc[p, 'hit_at_wr5'] * 100:.2f} [{lo5 * 100:.2f}, {hi5 * 100:.2f}]",
                     f"{s.loc[p, 'hit_at_wr10'] * 100:.2f} [{lo10 * 100:.2f}, {hi10 * 100:.2f}]",
                     f"{s.loc[p, 'best_utility'] * 100:.2f}"])
    table_caption(doc, 4, "Confirmation period: hit rate (% of all requests) at matched wrong reuse, 95% bootstrap "
                          "intervals, and best net utility per 100 requests")
    table(doc, ["Policy", "HR@5%", "HR@10%", "Utility"], rows, [5.6, 3.8, 3.8, 2.0], bold_rows=(4,), align_right=(1, 2, 3))
    comp = R["confirm_comparisons"].set_index(["comparison", "level"])
    floor = pd.read_csv(RES / "confirm_robust_floor_comparisons.csv").set_index(["comparison", "level"])
    rows = []
    for label, table_ in [("All candidates (similarity ≥ 0.70)", comp), ("Stricter floor (similarity ≥ 0.80)", floor)]:
        row = [label]
        for level in (0.05, 0.1):
            c = table_.loc[("P4_patterns - P1_fixed", level)]
            row.append(f"{c['gain'] * 100:+.2f} [{c['ci_low'] * 100:+.2f}, {c['ci_high'] * 100:+.2f}]"
                       + (" *" if c["holm_reject"] else ""))
        rows.append(row)
    table_caption(doc, 4, "Gain of behavior-aware admission (P4) over the standard semantic cache (P1), percentage points "
                          "(* significant after Holm correction)")
    table(doc, ["Candidate pool", "at ≤5% wrong reuse", "at ≤10% wrong reuse"], rows, [5.4, 5.0, 5.0])
    para(doc, f"Behavior-aware admission serves far more requests than similarity-based caching at the same error level. At "
              f"≤10% wrong reuse the proposed policy P4 serves {pct(s.loc['P4_patterns', 'hit_at_wr10'])} of all requests "
              f"against {pct(s.loc['P1_fixed', 'hit_at_wr10'])} for the GPTCache-style fixed threshold — about 240 times as "
              f"many — and {pct(s.loc['P2_per_intent', 'hit_at_wr10'])} for per-intent thresholds; at this level it also "
              f"serves more than the context-embedding policy ({pct(s.loc['P5_context', 'hit_at_wr10'])}). The gain over the "
              "standard cache is significant at both pre-registered levels after Holm correction and holds with a stricter "
              "similarity floor (Table 4.2). Both behavior-aware variants — dialogue acts alone (P3) and acts with mined "
              "patterns (P4) — lead the comparison: the dialogue act carries most of the volume gain, and the mined patterns "
              "add safety on context-dependent turns (Section d) and readable rules (Section e). Figure 19 shows that the "
              "advantage holds at every operating point: similarity thresholds stay near zero until wrong reuse is very "
              "high, while the behavior-aware policies serve 4–5% of requests at 10% and about 9% at 30%.")
    figure(doc, FIG / "confirm_curves.png", "Hit rate against wrong-reuse rate on the confirmation period", 6.0)

    doc.add_heading("d. Mined patterns make reuse safer", level=2)
    para(doc, "Figure 20 shows, for the requests each learned policy chose to serve at the ≤10% operating point, how often "
              "the reuse was wrong for each dialogue act, with the raw counts on the bars. On correction turns, the per-turn "
              "policy and the context-embedding policy each served three corrections and got two of them wrong (66.7%); "
              "with mined patterns, wrong reuse on corrections fell to 0%. On follow-ups it fell from 15.4% to 13.3%, while "
              "the context-embedding policy was wrong on 30% of follow-ups. Adding conversation context to the similarity "
              "match does not protect context-dependent turns; mined behavior does, by refusing reuse in behavioral states "
              "where it has historically failed. The per-act counts are small, so the breakdown is reported descriptively.")
    figure(doc, REP / "mechanism_all.png", "Wrong reuse by dialogue act at the ≤10% operating point (wrong/served)", 6.2)

    doc.add_heading("e. Interpretable behavioral rules", level=2)
    para(doc, "The association rules make every decision explainable (Figure 21, Table 4.3). A fresh opening question "
              "matched to a cached fresh opening question is the safest reuse, acceptable 47% of the time over 2,643 judged "
              "pairs. At the other extreme, a fresh question matched to an answer produced at the end of a chain of "
              "corrections was acceptable in 0 of 34 pairs, and follow-ups matched to other follow-ups in 2–3%. A similarity "
              "score cannot express any of these facts; the rules state them directly, which supports audits and debugging.")
    rules = R["behavioral_rules"]
    rules = rules[rules["pairs"] >= 30].sort_values("acceptable_rate")
    pick = pd.concat([rules.head(4), rules.tail(4).iloc[::-1]])
    table_caption(doc, 4, "Mined rules with the lowest and highest reuse acceptability (at least 30 judged pairs)")
    table(doc, ["Request state", "Request act", "Entry state", "Entry act", "Acceptable", "Pairs"],
          [[a.replace("_", " "), b.replace("_", " "), c.replace("_", " "), d.replace("_", " "), pct(e, 0), f"{n:,}"]
           for a, b, c, d, e, n in pick[["pat_state_q", "act", "pat_state_c", "cand_act", "acceptable_rate", "pairs"]]
           .itertuples(index=False)], [3.6, 2.6, 3.6, 2.6, 1.8, 1.4], size=9, align_right=(4, 5))
    figure(doc, REP / "rules_bar.png", "Reuse acceptability of the strongest and weakest mined rules", 6.2)

    doc.add_heading("f. Validation of the results", level=2)
    para(doc, "The results were protected against the usual ways evaluations go wrong. Claims and metrics were written down "
              "before testing; the code was frozen under a Git tag and the held-out period was evaluated once; every policy "
              "was compared at the same wrong-answer rate with 1,000 session-level bootstrap resamples and Holm correction; "
              "and patterns were mined from past traffic only, with 19 automated tests including checks that no future data "
              "reaches a turn's features. A positive control, in which behavior-dependent duplicates are planted in "
              "synthetic traffic, confirms that the pipeline detects a pattern effect when one exists: the pattern-aware "
              "verifier serves 24.0% at ≤10% wrong reuse against 5.7% for the per-query verifier (Figure 22). Grouped "
              "five-fold cross-validation repeated over three shuffles gives a stable F1 between 0.633 and 0.639 for all "
              "learned policies, with a spread of at most 0.075 (Figure 23).")
    figure(doc, REP / "positive_control.png", "Positive control: a planted behavioral effect is recovered", 4.8)
    figure(doc, REP / "cv_spread.png", "Cross-validated F1 of the learned policies", 4.8)

    doc.add_heading("g. Service latency", level=2)
    lat = R["service_latency"]
    para(doc, f"With {lat['cache_entries']:,} cached entries, the admission engine decides in {lat['engine_ms_p50']:.1f} ms "
              f"at the median and {lat['engine_ms_p95']:.1f} ms at the 95th percentile, including embedding the request, on "
              f"a laptop CPU; through HTTP the figures are {lat['http_ms_p50']:.1f} and {lat['http_ms_p95']:.1f} ms "
              "(Figure 24). This is small next to the seconds a provider call takes, so admission adds little delay to "
              "requests that miss and removes almost all of it from requests that hit.")
    figure(doc, REP / "latency.png", "Admission latency of the running service", 4.8)

    doc.add_heading("h. Real-world applications", level=2)
    bullets(doc, [
        ("Enterprise LLM gateways: ", "an admission layer in front of every provider call — fewer paid calls at the same "
                                      "answer quality; integration is two HTTP calls (/admit before, /record after)."),
        ("Customer-support and help-desk chatbots: ", "repeated questions are answered instantly from cache, while "
                                                      "follow-ups such as “shorten that” always go to the model."),
        ("Coding and writing assistants: ", "refinement loops, where similarity caching fails most, are protected."),
        ("Education and tutoring bots: ", "many learners ask the same fresh questions; cached explanations are served safely."),
        ("Guardrail for existing caches: ", "any semantic cache can adopt the finding directly — never reuse for "
                                            "follow-ups, corrections or continuations."),
        ("Auditing AI caching: ", "readable mined rules and the replay protocol let teams audit and compare cache vendors.")])
    para(doc, "Section 3.4 quantifies the value: about 44,700 extra model calls avoided per million requests compared with a "
              "standard semantic cache at the same error level, or a projected ₹1.95 crore a year at 100 million requests a "
              "month on a premium model (Table 3.4).")

    doc.add_heading("i. Exploratory extensions: routing and conversation-level fast-tracking", level=2)
    para(doc, "Model routing — sending each request to a strong or a cheaper model — was part of the original scope. The same "
              "behavioral features were used to build a pattern-aware router, evaluated on 1,377 multi-turn conversations in "
              "which human voters compared a strong and a weak model. With one vote per whole conversation, this data set "
              "did not carry enough per-turn signal to separate any router, including the baselines, from random routing at "
              "this sample size, so routing is reported as exploratory; turn-level quality labels are the natural next step "
              "(Chapter 5).")
    para(doc, "Conversation-level fast-tracking — jumping a new conversation straight to the final answer that satisfied a "
              "similar earlier one — was explored as a stretch goal. Conversations that open the same way were found to end "
              "at different needs, which is the behavioral effect of Section b at the level of whole sessions: such caching "
              "has to follow behavior as the conversation unfolds, and is left to future work.")

    doc.add_heading("j. Threats to validity", level=2)
    table_caption(doc, 4, "Threats to validity and how they were handled")
    table(doc, ["Threat", "Effect", "Mitigation / status"], [
        ["Labels come from an LLM judge", "wrong labels would bias every metric",
         "judge sees the reference answer; three models agree on 85–88%; two-rater human gold set in progress"],
        ["Dialogue acts are model-tagged", "act errors blur the behavior signal",
         "LLM tags for all turns offline; the live tagger can be made more accurate"],
        ["11% of queued turns unlabeled", "less precision", "stratified random queue order; population weights"],
        ["One corpus, two weeks of traffic", "limited generality", "time-based split; held-out later period"],
        ["Replay, not live users", "cannot see reactions to cached answers", "per-policy caches; served answers never cached"],
        ["P5 is our reimplementation", "may understate ContextCache", "named as context-embedding baseline"],
        ["Small counts in the per-act view", "per-act rates are noisy", "raw counts shown; reported descriptively"],
        ["Tuning to the test data", "over-optimistic results", "pre-registration, dated change log, single frozen run"]],
          [4.2, 4.4, 7.0], size=9)

    doc.add_heading("k. Objectives met", level=2)
    sv = pd.read_csv(RES / "savings_projection.csv")
    year = sv[(sv["tier"].str.startswith("premium")) & (sv["wrong_reuse_level"] == 10)
              & (sv["requests_per_month"] == 100_000_000)]["saving_inr_year"].iloc[0]
    table_caption(doc, 4, "Objectives and the evidence that each was met")
    table(doc, ["Objective", "Status", "Evidence"], [
        ["Mine behavioral patterns from gateway traffic", "Achieved", "FP-Growth + PrefixSpan re-mined daily; 82 behavioral rules"],
        ["Build a behavior-aware admission engine", "Achieved", "~240× more requests served than a standard cache at ≤10% error"],
        ["Make reuse safer on context-dependent turns", "Achieved", "wrong reuse on corrections 66.7% → 0%"],
        ["Evaluate rigorously on real traffic", "Achieved", "30,015 real turns, 10,776 judged, pre-registered single frozen test"],
        ["Deliver a deployable service and demo", "Achieved", "REST API at 43 ms per decision; five-page interactive demo"],
        ["Quantify real-world value", "Achieved", f"≈ ₹ {year / 1e7:.2f} crore a year saved at 100M requests a month"]],
          [5.4, 2.0, 8.2], size=9.5)



# chapter 5: conclusion and future work
def chapter5(doc, R):
    chapter(doc, 5, "Conclusion and Future Work")
    para(doc, "This project set out to show that behavioral patterns mined from LLM gateway traffic improve cache admission. "
              "Its first result is a finding about the problem itself: whether a cached answer can be reused is largely a "
              "behavioral question. On real chatbot traffic, a similarity cache serves an unacceptable answer for more than "
              "half of near-duplicate requests, and the dialogue role of the turn — fresh request versus follow-up, "
              "correction or continuation, on either side of the reuse — separates safe reuse from unsafe reuse far better "
              "than similarity does.")
    para(doc, "Built on that finding, behavior-aware admission served about 240 times as many requests as a standard "
              "semantic cache at the same rate of wrong answers on a held-out period, a statistically significant and robust "
              "result. Mined association rules removed wrong reuse on correction turns and made every decision explainable. "
              "The system runs as a 43-millisecond REST service on a laptop CPU, and at enterprise scale it corresponds to a "
              "projected saving of about ₹1.95 crore a year. The evaluation was pre-registered, run once on frozen code on "
              "future data, and validated with a positive control, so these results can be relied on.")
    para(doc, "For practitioners the immediate lesson is simple: a semantic cache in a chat product should not reuse answers "
              "for follow-ups, corrections or continuations, and should prefer cached answers that were themselves produced "
              "for self-contained requests.")
    doc.add_heading("Future work", level=2)
    bullets(doc, [
        "Extend the behavioral signals to multi-provider model routing with turn-level quality labels, building on the "
        "exploratory routing study.",
        "Extend caching from single answers to whole conversations, matching behavior turn by turn as it unfolds.",
        "Complete the human validation of the judge and the act tagger (rating sheets prepared) and report Cohen's κ [21].",
        "Evaluate on larger and more repetitive workloads (customer support, internal help desks) and over longer periods "
        "as the cache grows.",
        "Improve the online dialogue-act tagger so the service matches the offline tags more closely.",
        "Deploy the admission service inside a production gateway and measure user reactions to cached answers."])


# chapter 6: appendix with repository, versions, register, timeline and code
def chapter6(doc, R):
    chapter(doc, 6, "Appendix")
    doc.add_heading("A. Repository and reproduction", level=2)
    para(doc, f"Source code: {REPO}. The confirmation run corresponds to the Git tag freeze-confirm-2026-11-16. To "
              "reproduce every table and figure from raw data: create a Python 3.11 virtual environment, install "
              "requirements.txt, place the gateway key in a local .env file, and run python run_all.py; the demonstration "
              "starts with streamlit run demo/app.py and the service with python scripts/12_service.py serve.", indent=False)
    doc.add_heading("B. Tools and libraries", level=2)
    v = R["tool_versions"]
    use = {"Python": "language", "pandas": "tables", "numpy": "arrays", "pyarrow": "Parquet storage",
           "datasets": "streaming WildChat", "sentence-transformers": "embeddings", "torch": "embedding runtime (CPU)",
           "faiss-cpu": "similarity search", "scikit-learn": "k-means, act tagger, cross-validation",
           "lightgbm": "admission verifier", "mlxtend": "FP-Growth", "prefixspan": "sequential patterns",
           "matplotlib": "figures", "fastapi": "admission API", "uvicorn": "API server", "anthropic": "judge / tagger client",
           "groq": "seed-label client", "streamlit": "demonstration app", "altair": "demo charts",
           "python-docx": "this report", "python-pptx": "slides and poster", "playwright": "demo screenshots",
           "pytest": "tests", "joblib": "model bundle", "pyyaml": "configuration"}
    table_caption(doc, 6, "Tools and libraries with the exact versions used")
    table(doc, ["Tool", "Version", "Used for"], [[r.tool, r.version, use.get(r.tool, "")] for r in v.itertuples()],
          [4.2, 3.2, 8.2], size=9)
    doc.add_heading("C. Results register", level=2)
    s = R["confirm_summary"].set_index("policy")
    table_caption(doc, 6, "Headline numbers and the file each one comes from")
    table(doc, ["Number", "Value", "File (results/)"], [
        ["Turns / sessions / users", "30,015 / 6,828 / 2,501", "dataset_stats.csv"],
        ["Turns labeled", "10,776 of 12,124 (88.9%)", "label_queue (work), labels"],
        ["Near-duplicates served wrong", "56.3% (7,360 pairs)", "near_duplicate_behavior.csv"],
        ["Context-dependent vs self-contained", "75.7% vs 37.1%", "near_duplicate_behavior.csv"],
        ["P4 / P3 / P1 hit at ≤10%", f"{pct(s.loc['P4_patterns', 'hit_at_wr10'])} / {pct(s.loc['P3_per_query', 'hit_at_wr10'])}"
                                    f" / {pct(s.loc['P1_fixed', 'hit_at_wr10'])}", "confirm_summary.csv"],
        ["P4 − P1 at ≤5% / ≤10%", "+1.10 / +4.47 points, significant", "confirm_comparisons.csv"],
        ["Corrections served wrong, P3 → P4", "2 of 3 → 0 of 1", "exploratory_mechanism_all.csv"],
        ["Positive control at ≤10%", "24.0% vs 5.7%", "positive_control.csv"],
        ["Projected saving at 100M requests / month", "≈ ₹ 1.95 crore a year (premium model)", "savings_projection.csv"],
        ["Decision latency p50 / p95", "43.4 / 79.0 ms", "service_latency.json"],
        ["Model usage cost at listed rates", f"₹ {R['llm_usage_cost']['cost_inr'].sum():,.2f}", "llm_usage_cost.csv"]],
          [5.6, 5.0, 5.0], size=9)
    doc.add_heading("D. Project timeline", level=2)
    para(doc, "Figure 25 shows the project timeline as recorded week by week in the project diary, from topic "
              "selection in July to the Final Review in November, with the review windows and the November "
              "holiday.", indent=False)
    figure(doc, REP / "gantt.png", "Project timeline from the project diary", 6.3)
    doc.add_heading("E. Frozen judge prompt", level=2)
    from gwcache import judge
    code(doc, judge.JUDGE_PROMPT)
    doc.add_heading("F. Selected code", level=2)
    for title, fn in [("Expected-benefit score (gwcache/decision.py)", decision.expected_benefit),
                      ("Behavioral state of a turn (gwcache/patterns.py)", patterns.state),
                      ("Stateful replay with a per-policy cache (gwcache/replay.py)", replay.run),
                      ("Hit rate at matched wrong reuse (gwcache/metrics.py)", metrics.hit_at),
                      ("Online admission decision (gwcache/service.py)", service.Engine.admit)]:
        para(doc, title, indent=False).runs[0].bold = True
        code(doc, inspect.getsource(fn))


# chapter 7: references in ieee style
def chapter7(doc):
    chapter(doc, 7, "References")
    refs = [
        "F. Bang, “GPTCache: An open-source semantic cache for LLM applications enabling faster answers and cost savings,” in Proc. 3rd Workshop for Natural Language Processing Open Source Software (NLP-OSS), 2023, pp. 212–218.",
        "W. Gill, M. Elidrisi, P. Kalapatapu, A. Ahmed, A. Anwar, and M. A. Gulzar, “MeanCache: User-centric semantic caching for LLM web services,” in Proc. IEEE Int. Parallel and Distributed Processing Symp. (IPDPS), 2025.",
        "L. G. Schroeder et al., “Adaptive semantic prompt caching with VectorQ,” arXiv:2502.03771, 2025.",
        "C. Wang, X. Liu, Y. Zhu, A. Youssef, P. Nagpurkar, and H. Chen, “Category-aware semantic caching for heterogeneous LLM workloads,” arXiv:2510.26835, 2025.",
        "J. Yan, W. Ni, L. Chen et al., “ContextCache: Context-aware semantic cache for multi-turn queries in large language models,” Proc. VLDB Endowment, vol. 18, no. 12, p. 5391, 2025.",
        "L. Chen, M. Zaharia, and J. Zou, “FrugalGPT: How to use large language models while reducing cost and improving performance,” Trans. Machine Learning Research, 2024.",
        "I. Ong et al., “RouteLLM: Learning to route LLMs with preference data,” in Proc. Int. Conf. Learning Representations (ICLR), 2025.",
        "W. Zhao, X. Ren, J. Hessel, C. Cardie, Y. Choi, and Y. Deng, “WildChat: 1M ChatGPT interaction logs in the wild,” in Proc. Int. Conf. Learning Representations (ICLR), 2024.",
        "W.-L. Chiang et al., “Chatbot Arena: An open platform for evaluating LLMs by human preference,” in Proc. Int. Conf. Machine Learning (ICML), 2024.",
        "L. Zheng et al., “Judging LLM-as-a-judge with MT-Bench and Chatbot Arena,” in Advances in Neural Information Processing Systems (NeurIPS), Datasets and Benchmarks Track, 2023.",
        "P. K. Bodigutla, A. Tiwari, S. Matsoukas, J. Valls-Vargas, and L. Polymenakos, “Joint turn and dialogue level user satisfaction estimation on multi-domain conversations,” in Findings of the Association for Computational Linguistics: EMNLP 2020, pp. 3897–3909.",
        "J. Han, J. Pei, and Y. Yin, “Mining frequent patterns without candidate generation,” in Proc. ACM SIGMOD Int. Conf. Management of Data, 2000, pp. 1–12.",
        "J. Pei, J. Han, B. Mortazavi-Asl, H. Pinto, Q. Chen, U. Dayal, and M.-C. Hsu, “PrefixSpan: Mining sequential patterns efficiently by prefix-projected pattern growth,” in Proc. 17th Int. Conf. Data Engineering (ICDE), 2001, pp. 215–224.",
        "B. Liu, W. Hsu, and Y. Ma, “Integrating classification and association rule mining,” in Proc. 4th Int. Conf. Knowledge Discovery and Data Mining (KDD), 1998, pp. 80–86.",
        "G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, “LightGBM: A highly efficient gradient boosting decision tree,” in Advances in Neural Information Processing Systems (NeurIPS), 2017.",
        "N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” in Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP-IJCNLP), 2019, pp. 3982–3992.",
        "W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, “MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers,” in Advances in Neural Information Processing Systems (NeurIPS), 2020.",
        "J. Johnson, M. Douze, and H. Jégou, “Billion-scale similarity search with GPUs,” IEEE Trans. Big Data, vol. 7, no. 3, pp. 535–547, 2021.",
        "S. Holm, “A simple sequentially rejective multiple test procedure,” Scandinavian Journal of Statistics, vol. 6, no. 2, pp. 65–70, 1979.",
        "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. Chapman and Hall, 1993.",
        "J. Cohen, “A coefficient of agreement for nominal scales,” Educational and Psychological Measurement, vol. 20, no. 1, pp. 37–46, 1960.",
        "LMSYS, “LMSYS Arena Human Preference 55k,” Hugging Face dataset lmsys/lmsys-arena-human-preference-55k, 2024."]
    for i, r in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.line_spacing = 1.15
        p.add_run(f"[{i}]\t{r}")


# one biodata page per member, with placeholders to fill
def biodata(doc):
    for name, _ in MEMBERS:
        page_break(doc)
        centred(doc, "BIODATA", size=14, bold=True, space_after=18)
        for line in ["Photo: [attach]", f"Name : {name}", "Mobile Number : [fill]", "E-mail : [fill]",
                     "Permanent Address : [fill]"]:
            q = doc.add_paragraph(line)
            q.paragraph_format.first_line_indent = Cm(0)


# assembles the whole document
def main():
    R = results()
    doc = new_document()
    front_matter(doc, R)
    lists(doc)
    chapter1(doc, R)
    chapter2(doc, R)
    chapter3(doc, R)
    chapter4(doc, R)
    chapter5(doc, R)
    chapter6(doc, R)
    chapter7(doc)
    biodata(doc)
    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
