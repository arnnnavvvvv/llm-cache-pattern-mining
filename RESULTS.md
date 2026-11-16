# Results

Every number below comes from a file in `results/`; `results/REGISTER.md` indexes all of them. The confirmation run used frozen code at tag `freeze-confirm-2026-11-16` and was run once.

## Data and labels

- **Turns:** 30,015 WildChat turns, each with the real answer: 6,828 sessions from 2,501 users, Apr 9–23 2023.
- **Split:** train / dev / confirm = 18,007 / 6,004 / 6,004 turns, by session start time.
- **Candidates:** 12,124 turns have at least one earlier neighbour at similarity ≥ 0.70 (25,345 candidate pairs).
- **Judge selection:** Haiku 5.5, Sonnet 5.5 and Opus 5.5 labeled the same 199 pairs and agreed pairwise on 85–88%. Sonnet 5.5 labeled the queue.
- **Labeled:** 10,776 turns (88.9%), stratified, with 88.5–89.3% coverage in every period × similarity band. Metrics are reweighted to the full population.
- **Dialogue acts:** every turn's act is LLM-tagged (98% of first turns are new requests).

## Finding: behavior decides whether reuse is safe (`near_duplicate_behavior.csv`, `figures/wrong_reuse_by_act.png`)

Among 7,360 near-duplicate pairs (similarity ≥ 0.97), a similarity cache serves an unacceptable answer **56.3%** of the time.

| Near-duplicates, split by | Self-contained | Context-dependent |
|---|---|---|
| The new request | 37.1% wrong | **75.7% wrong** |
| The cached entry | 42.2% wrong | **73.2% wrong** |

Below 0.90 similarity almost every reuse is wrong whatever the act. Above it, behavior is what separates safe reuse from unsafe reuse.

## H1a: admission on the held-out confirmation period (`confirm_summary.csv`, `confirm_comparisons.csv`)

| Policy | Hit @ ≤5% wrong-reuse | Hit @ ≤10% wrong-reuse |
|---|---|---|
| P1 fixed threshold (GPTCache-style) | 0.02% | 0.02% |
| P2 per-intent thresholds | 0.80% | 0.80% |
| P3 per-turn verifier (similarity + acts) | 1.46% | 4.62% |
| P5 + context embedding (ContextCache-style) | 1.27% | 3.87% |
| **P4 + mined patterns and behavioral rules** | 1.12% | **4.49%** |
| P4+ context and patterns | 1.83% | 3.80% |

- **P4 vs P1:** +1.10 and +4.47 points, **significant at both levels** (Holm). It holds again at a 0.80 similarity floor.
- **P4 vs P2, P3 and P5:** not significant. The pre-registered H1a criterion (beat every comparator) is **not met** (`confirm_verdict.json`).
- **Mechanism** (`confirm_mechanism.csv`), at the ≤10% operating point, P4 vs P3:
  - wrong reuse on **corrections: 66.7% → 0%**;
  - on follow-ups: 15.4% → 13.3%;
  - on later turns: 11.4% → 10.2%.

  Patterns change *which* requests are served, not how many.
- **All policies, per act** (`exploratory_mechanism_all.csv`, descriptive, added after the run from the same frozen models): at ≤10% wrong reuse, P3 and P5 each served 3 corrections and got 2 wrong; P4 and P4+ served 1 and got it right. On follow-ups P5 was wrong on 3 of 10, P3 on 2 of 13 and P4 on 2 of 15. Counts are small.
- **Placebos and ablations** (`confirm_controls_*.csv`): none differ from P3.
- **Positive control** (`positive_control.csv`): 24.0% vs 5.7%. The pipeline detects pattern effects when they exist.
- **CV spread** (`confirm_cv_spread.csv`): F1 0.63–0.64 for every learned policy, spread ≤ 0.075.

**Reading.** Behavior-aware admission (dialogue acts plus mined patterns) serves two orders of magnitude more requests than a fixed-threshold cache at the same wrong-reuse level. Most of the volume gain comes from per-turn acts. Mined patterns add safety on context-dependent turns rather than extra volume, at this scale.

## H1b: routing (`routing_summary.csv`, `routing_comparisons.csv`)

1,377 human-voted strong-vs-weak multi-turn conversations; the weak model was at least as good in 45.8%.

| Strong-model budget | Per-query router | Context router | Pattern router | Random routing |
|---|---|---|---|---|
| 30% | 61.1% | 62.7% | 61.9% | 62.1% |
| 50% | 73.3% | 73.1% | 72.3% | 72.9% |

Every router performs about the same as random routing, so **H1b is not supported**. Conversation-level votes carry little routing signal at this sample size.

## Stretch: trajectory fast-tracking (`trajectory_summary.json`, `trajectory_curve.csv`)

- **Coverage:** all 710 satisfied confirm sessions had a stored trajectory with the same opening intent; the 83 closest were judged.
- **Outcome:** only 4.8% of fast-tracks would have satisfied the user. Even with an identical opening request, 96% ended needing something else.

Exploratory finding: conversations that open the same way diverge, so trajectory caching must track behavior turn by turn.

## System (`service_latency.json`)

The admission API decides in **43 ms (median) / 79 ms (p95)** with 3,000 cached entries, including embedding, on a laptop CPU.

## Pending (needs people)

- **Gold sheets** (`results/human_checks/gold_sheet_rater_{a,b}.csv`): two raters. Then run `python scripts/06_gold.py score`.
- **Act sheet** (`act_sheet.csv`): one rater. Re-running step 3 scores the tagger against it.
- **Satisfaction sheet** (`satisfaction_sheet.csv`): one rater, to validate the trajectory proxy.

## Report, deck, poster and demo

- **Report:** `report/Capstone_Report.docx` (and `.pdf`), 54 pages in the VIT-AP thesis format, built by `report/build_report.py`. Names and registration numbers of members 2–4, the amount actually billed by the gateway, and biodata are placeholders.
- **Slides and poster:** `report/Review3_Presentation.pptx` (18 slides) and `report/Poster_A1.pptx`.
- **Demo:** `streamlit run demo/app.py`; screenshots in `results/figures/demo/`.
- **Model usage** (`llm_usage_cost.csv`): ₹2,481.62 at the gateway's listed rates, from logged token counts.

## Paper

`paper/` contains the IEEEtran conference source:

- `main.tex` and `refs.bib`;
- generated `numbers.tex` and tables, from `scripts/15_paper.py`;
- the figures.

Upload the folder to Overleaf and compile with pdfLaTeX and BibTeX. Fill in author names and emails in `main.tex`.
