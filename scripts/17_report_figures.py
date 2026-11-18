# report figures beyond the paper set: data, labeling, gains, mechanism, controls, routing, trajectory, latency, timeline
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from gwcache import config, storage
from gwcache.plotstyle import (ACCENT, ACTS, ALERT, COLORS, GOOD, GRID, INK, LABELS, MUTED, NEUTRAL, SHORT, figure,
                               save, style)

RES = config.path("results")
OUT = config.path("figures") / "report"


# share of every dialogue act across all tagged turns, the motivating chart for chapter 1
def act_distribution():
    dist = json.loads((RES / "act_tagger.json").read_text())["tagged_distribution"]
    s = pd.Series(dist).sort_values()
    total = s.sum()
    fig, ax = figure(8, 3.8)
    colors = [NEUTRAL if k == "new_request" else ACCENT for k in s.index]
    ax.barh([ACTS[k] for k in s.index], s.values / total * 100, color=colors, height=0.6)
    for i, v in enumerate(s.values):
        ax.text(v / total * 100 + 0.6, i, f"{v / total * 100:.1f}%  ({v:,})", va="center", color=INK, fontsize=9)
    dependent = total - dist["new_request"]
    style(ax, f"{dependent / total * 100:.1f}% of {total:,} real chat turns are not fresh, self-contained requests",
          "Share of all turns (%)", "", grid_axis="x")
    ax.set_xlim(0, 60)
    save(fig, OUT / "act_distribution.png")


# turns per day coloured by split, showing the time-ordered train/dev/confirm cut
def split_timeline():
    turns = storage.load("turns")
    day = turns["timestamp"].dt.floor("D").dt.tz_localize(None)
    counts = turns.assign(day=day).groupby(["day", "period"]).size().unstack(fill_value=0)
    fig, ax = figure(8, 3.6)
    bottom = np.zeros(len(counts))
    for period, color in [("train", ACCENT), ("dev", "#eda100"), ("confirm", "#e87ba4")]:
        if period in counts:
            ax.bar(counts.index, counts[period], bottom=bottom, color=color, width=0.8, label=period)
            bottom += counts[period].to_numpy()
    style(ax, "Turns per day by split (sessions assigned by start time)", "", "Turns", grid_axis="y")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(frameon=False, labelcolor=INK)
    save(fig, OUT / "split_timeline.png")


# queued vs labeled turns in every period x similarity band, showing the even label coverage
def label_coverage():
    queue, labels = storage.load("label_queue"), storage.load("labels")
    queue = queue.assign(labeled=queue["turn_id"].isin(set(labels["turn_id"])))
    bands = config.load()["labels"]["sim_bins"]
    names = [f"{bands[i]:.2f}-{min(bands[i + 1], 1):.2f}" for i in range(len(bands) - 1)]
    g = queue.groupby(["period", "sim_bin"]).agg(queued=("turn_id", "size"), labeled=("labeled", "sum")).reset_index()
    g["label"] = g["period"] + "\n" + g["sim_bin"].map(lambda b: names[int(b)])
    order = {"train": 0, "dev": 1, "confirm": 2}
    g = g.sort_values(["period", "sim_bin"], key=lambda c: c.map(order) if c.name == "period" else c)
    fig, ax = figure(9, 4)
    x = np.arange(len(g))
    ax.bar(x, g["queued"], color=GRID, width=0.7, label="queued")
    ax.bar(x, g["labeled"], color=ACCENT, width=0.45, label="labeled")
    for i, (q, l) in enumerate(zip(g["queued"], g["labeled"])):
        ax.text(i, q + 30, f"{l / q * 100:.1f}%", ha="center", color=INK, fontsize=8)
    ax.set_xticks(x, g["label"], fontsize=7)
    style(ax, f"Label coverage per period and similarity band ({int(g['labeled'].sum()):,} of {int(g['queued'].sum()):,} turns)",
          "", "Turns", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK)
    save(fig, OUT / "label_coverage.png")


# number of patterns mined each day from past-only traffic
def mining_daily():
    m = pd.read_csv(RES / "pattern_mining_summary.csv")
    m["day"] = pd.to_datetime(m["day"]).dt.tz_localize(None)
    fig, ax = figure(8, 3.8)
    for col, color, name in [("act_seqs", ACCENT, "act sequences"), ("intent_seqs", "#eda100", "intent sequences"),
                             ("itemsets", GOOD, "frequent itemsets")]:
        ax.plot(m["day"], m[col], color=color, marker="o", markersize=3, linewidth=1.6, label=name)
    ax2 = ax.twinx()
    ax2.bar(m["day"], m["sessions_mined"], color=GRID, width=0.6, alpha=0.6, zorder=0)
    ax2.set_ylabel("Past sessions mined", color=MUTED)
    ax2.tick_params(colors=MUTED)
    for side in ("top", "right", "left", "bottom"):
        ax2.spines[side].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    style(ax, "Patterns re-mined each day from earlier traffic only", "", "Patterns found")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(frameon=False, labelcolor=INK, loc="upper left")
    save(fig, OUT / "mining_daily.png")


# near-duplicate wrong reuse split by whether the request or the cached entry depends on context
def near_duplicate_split():
    nd = pd.read_csv(RES / "near_duplicate_behavior.csv")
    overall = nd[nd["behavior"] == "all"]["wrong_reuse"].iloc[0]
    fig, ax = figure(7, 3.8)
    x = np.arange(2)
    for j, (beh, color) in enumerate([("self_contained", NEUTRAL), ("context_dependent", ALERT)]):
        vals = [nd[(nd["behavior"] == beh) & (nd["side"] == side)]["wrong_reuse"].iloc[0] * 100 for side in ["request", "cache_entry"]]
        ns = [nd[(nd["behavior"] == beh) & (nd["side"] == side)]["count"].iloc[0] for side in ["request", "cache_entry"]]
        ax.bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=color, label=beh.replace("_", "-"))
        for xi, v, n in zip(x + (j - 0.5) * 0.36, vals, ns):
            ax.text(xi, v + 1.5, f"{v:.1f}%\nn={n:,}", ha="center", color=INK, fontsize=8)
    ax.axhline(overall * 100, color=MUTED, linestyle="--", linewidth=1)
    ax.text(1.55, overall * 100 + 1, f"all near-duplicates {overall * 100:.1f}%", color=MUTED, fontsize=8, ha="right")
    ax.set_xticks(x, ["split by the new request", "split by the cached entry"])
    ax.set_ylim(0, 100)
    style(ax, "Near-duplicates (similarity >= 0.97): wrong reuse by behavior", "", "Wrong-reuse rate (%)", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK, loc="upper left")
    save(fig, OUT / "near_duplicate_split.png")


# paired gains with bootstrap intervals, one row per comparison and level
def forest(df: pd.DataFrame, label_fn, title: str, name: str):
    df = df.copy().iloc[::-1].reset_index(drop=True)
    fig, ax = figure(8, 0.42 * len(df) + 1.4)
    for i, r in df.iterrows():
        color = GOOD if r["holm_reject"] and r["gain"] > 0 else (ALERT if r["holm_reject"] else NEUTRAL)
        ax.plot([r["ci_low"] * 100, r["ci_high"] * 100], [i, i], color=color, linewidth=2.2)
        ax.plot(r["gain"] * 100, i, "o", color=color, markersize=6)
        tag = "  significant" if r["holm_reject"] else ""
        ax.text(r["ci_high"] * 100 + 0.15, i, f"{r['gain'] * 100:+.2f}{tag}", va="center", fontsize=8, color=INK)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(range(len(df)), [label_fn(r) for _, r in df.iterrows()], fontsize=8)
    style(ax, title, "Difference in hit rate (percentage points, 95% session-bootstrap interval)", "", grid_axis="x")
    lo, hi = df["ci_low"].min() * 100, df["ci_high"].max() * 100
    ax.set_xlim(lo - 0.5, hi + 2.2)
    save(fig, OUT / name)


# p4 against every comparator on the confirmation period
def forest_main():
    c = pd.read_csv(RES / "confirm_comparisons.csv")
    c = c[~c["comparison"].str.endswith("P4plus_context_patterns")]
    fn = lambda r: f"P4 vs {SHORT[r['comparison'].split(' - ')[1]]}  @ <= {int(r['level'] * 100)}% wrong"
    forest(c, fn, "Confirmation period: P4 gains over each comparator", "forest_main.png")


# placebos and ablations against p3 on the confirmation period
def forest_controls():
    c = pd.read_csv(RES / "confirm_controls_vs_p3.csv")
    c = c[c["level"] == 0.1].copy()
    c[["gain", "ci_low", "ci_high"]] = -c[["gain", "ci_high", "ci_low"]].to_numpy()
    names = {"placebo_shuffled": "placebo: shuffled history", "placebo_borrowed": "placebo: borrowed history",
             "abl_frequent_only": "ablation: frequent only", "abl_sequential_only": "ablation: sequential only",
             "abl_session_only": "ablation: session only", "abl_user_only": "ablation: user only",
             "abl_rules_only": "ablation: rule prior only", "abl_no_rules": "ablation: no rule prior"}
    fn = lambda r: names[r["comparison"].split(" - ")[1]]
    forest(c, fn, "Placebos and ablations minus P3, at <= 10% wrong reuse", "forest_controls.png")


# wrong reuse on each dialogue act at the 10% operating point for the learned policies, with served counts
def mechanism_all():
    m = pd.read_csv(RES / "exploratory_mechanism_all.csv")
    m = m[(m["level"] == 0.1) & (m["split_by"] == "act")]
    pols = ["P3_per_query", "P5_context", "P4_patterns", "P4plus_context_patterns"]
    acts = ["correction", "follow_up", "new_request", "new_ask_same_material", "continuation"]
    fig, ax = figure(9, 4.4)
    width = 0.2
    x = np.arange(len(acts))
    for j, p in enumerate(pols):
        rows = m[m["policy"] == p].set_index("group")
        vals = [rows.loc[a, "wrong_reuse"] * 100 if a in rows.index and rows.loc[a, "served_turns"] else 0 for a in acts]
        xs = x + (j - 1.5) * width
        ax.bar(xs, vals, width=width * 0.92, color=COLORS[p], label=LABELS[p])
        for xi, a in zip(xs, acts):
            r = rows.loc[a]
            ax.text(xi, (r["wrong_reuse"] * 100 if r["served_turns"] else 0) + 1.5,
                    f"{int(r['wrong_turns'])}/{int(r['served_turns'])}", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(x, [ACTS[a] for a in acts])
    ax.set_ylim(0, 80)
    style(ax, "Wrong reuse by dialogue act at <= 10% overall wrong reuse (labels: wrong/served turns)", "",
          "Wrong-reuse rate among served (%)", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK, fontsize=8, ncol=2)
    save(fig, OUT / "mechanism_all.png")


# pipeline detects a planted pattern effect: positive control
def positive_control():
    pc = pd.read_csv(RES / "positive_control.csv")
    fig, ax = figure(6.5, 3.6)
    x = np.arange(2)
    for j, (pol, color, name) in enumerate([("per_query", COLORS["P3_per_query"], "per-turn verifier"),
                                            ("patterns", COLORS["P4_patterns"], "with mined patterns")]):
        r = pc[pc["policy"] == pol].iloc[0]
        vals = [r["hit_at_wr5"] * 100, r["hit_at_wr10"] * 100]
        ax.bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=color, label=name)
        for xi, v in zip(x + (j - 0.5) * 0.36, vals):
            ax.text(xi, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9, color=INK)
    ax.set_xticks(x, ["<= 5% wrong reuse", "<= 10% wrong reuse"])
    style(ax, "Positive control: planted behavioral effect is recovered", "", "Hit rate (%)", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK)
    save(fig, OUT / "positive_control.png")


# five-fold x three-shuffle f1 for each learned policy on the development data
def cv_spread():
    f = pd.read_csv(RES / "dev_cv_folds.csv")
    pols = ["P3_per_query", "P5_context", "P4_patterns", "P4plus_context_patterns"]
    fig, ax = figure(7, 3.6)
    rng = np.random.default_rng(0)
    for i, p in enumerate(pols):
        v = f[f["policy"] == p]["f1"].to_numpy()
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, color=COLORS[p], s=18, alpha=0.8)
        ax.plot([i - 0.25, i + 0.25], [v.mean()] * 2, color=INK, linewidth=1.6)
        ax.text(i + 0.28, v.mean(), f"{v.mean():.3f}", va="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(pols)), [SHORT[p] for p in pols])
    style(ax, "Grouped 5-fold x 3-shuffle F1 per learned policy (bar = mean)", "", "F1", grid_axis="y")
    save(fig, OUT / "cv_spread.png")


# fast-tracking a whole stored conversation is almost always wrong, at every threshold
def trajectory():
    t = pd.read_csv(RES / "trajectory_curve.csv").sort_values("threshold")
    fig, ax = figure(7, 3.6)
    ax.plot(t["threshold"], t["false_fast_track_rate"] * 100, color=ALERT, linewidth=1.8)
    ax2 = ax.twinx()
    ax2.plot(t["threshold"], t["fired"], color=NEUTRAL, linewidth=1.2, linestyle="--")
    ax2.set_ylabel("Sessions fast-tracked (dashed)", color=MUTED)
    ax2.tick_params(colors=MUTED)
    for side in ("top", "right", "left", "bottom"):
        ax2.spines[side].set_visible(False)
    ax.set_ylim(0, 105)
    style(ax, "Trajectory fast-tracking: false fast-track rate vs match threshold", "Opening-request similarity threshold",
          "False fast-track rate (%)")
    save(fig, OUT / "trajectory_curve.png")


# admission latency of the running service, engine-only and over http
def latency():
    lat = json.loads((RES / "service_latency.json").read_text())
    fig, ax = figure(6.5, 3.4)
    x = np.arange(2)
    for j, (k, color) in enumerate([("p50", ACCENT), ("p95", "#eda100")]):
        vals = [lat[f"engine_ms_{k}"], lat[f"http_ms_{k}"]]
        ax.bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=color, label=k)
        for xi, v in zip(x + (j - 0.5) * 0.36, vals):
            ax.text(xi, v + 1.5, f"{v:.0f} ms", ha="center", fontsize=9, color=INK)
    ax.set_xticks(x, ["decision engine", "over HTTP (/admit)"])
    style(ax, f"Admission latency, {lat['cache_entries']:,} cached entries, {lat['admit_calls']} calls, laptop CPU", "",
          "Milliseconds", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK)
    save(fig, OUT / "latency.png")


# acceptability of the strongest and weakest mined behavioral rules
def rules_bar():
    r = pd.read_csv(RES / "behavioral_rules.csv")
    r = r[r["pairs"] >= 30].sort_values("acceptable_rate")
    pick = pd.concat([r.head(5), r.tail(5)])
    short = lambda s: str(s).replace("new_ask_same_material", "same-material").replace("new_request", "new").replace(
        "follow_up", "follow-up").replace("continuation", "continue").replace("correction", "correct").replace(">", ">")
    names = [f"{short(a)} [{short(b)}]  ->  {short(c)} [{short(d)}]" for a, b, c, d in
             pick[["pat_state_q", "act", "pat_state_c", "cand_act"]].itertuples(index=False)]
    fig, ax = figure(9, 4.6)
    colors = [ALERT if v < 0.2 else GOOD for v in pick["acceptable_rate"]]
    ax.barh(range(len(pick)), pick["acceptable_rate"] * 100, color=colors, height=0.6)
    for i, (v, n) in enumerate(zip(pick["acceptable_rate"], pick["pairs"])):
        ax.text(v * 100 + 0.8, i, f"{v * 100:.0f}%  (n={n})", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(pick)), names, fontsize=7)
    style(ax, "Mined rules: request state [act] -> cached entry state [act]", "Acceptable reuse (%)",
          "", grid_axis="x")
    ax.set_xlim(0, 60)
    save(fig, OUT / "rules_bar.png")


# judge candidates: projected cost of labeling the whole queue and agreement with each other
def judge_cost():
    c = pd.read_csv(RES / "judge_pick_cost.csv")
    fig, ax = figure(6.5, 3.4)
    names = [m.replace("claude-", "").replace("-5.5", " 5.5").title() for m in c["model"]]
    ax.bar(names, c["projected_inr_full_queue"], color=[NEUTRAL, ACCENT, NEUTRAL], width=0.5)
    for i, v in enumerate(c["projected_inr_full_queue"]):
        ax.text(i, v + 80, f"Rs {v:,.0f}", ha="center", fontsize=9, color=INK)
    style(ax, "Projected cost to label the full 12,124-turn queue (judge pick run)", "", "INR", grid_axis="y")
    save(fig, OUT / "judge_cost.png")


# routing quality at the two strong-model budgets against random routing
def routing_bars():
    s = pd.read_csv(RES / "routing_summary.csv")
    cheap = s[s["router"] == "always_cheap"]["quality"].iloc[0]
    fig, ax = figure(7, 3.6)
    x = np.arange(2)
    names = [("per_query", COLORS["P3_per_query"], "per-query router"), ("context", COLORS["P5_context"], "context router"),
             ("patterns", COLORS["P4_patterns"], "pattern router")]
    for j, (r, color, name) in enumerate(names):
        row = s[s["router"] == r].iloc[0]
        vals = [row["quality_at_strong30"] * 100, row["quality_at_strong50"] * 100]
        ax.bar(x + (j - 1) * 0.22, vals, width=0.2, color=color, label=name)
    for xi, share in zip(x, [0.3, 0.5]):
        rand = (cheap + share * (1 - cheap)) * 100
        ax.plot([xi - 0.36, xi + 0.36], [rand, rand], color=INK, linestyle=":", linewidth=1.6)
        ax.text(xi + 0.37, rand, f"random {rand:.1f}%", va="center", fontsize=8, color=INK)
    ax.set_xticks(x, ["30% sent to strong model", "50% sent to strong model"])
    ax.set_ylim(40, 80)
    style(ax, "Routing quality vs random routing (1,377 conversations)", "", "No worse than strong model (%)", grid_axis="y")
    ax.legend(frameon=False, labelcolor=INK, fontsize=8, loc="upper left")
    save(fig, OUT / "routing_bars.png")


# project timeline from the weekly project diary (weeks run tuesday to saturday), with the review windows
def gantt():
    d = pd.Timestamp
    rows = [("Topic selection, team formation, guide approval (wk 1–3)", "2026-07-14", "2026-08-01", "plan"),
            ("Literature survey, research gap, hypothesis, proposals (wk 4–5)", "2026-08-04", "2026-08-15", "plan"),
            ("First Review", "2026-08-18", "2026-08-22", "review"),
            ("Dataset selection, log schema, technical specification (wk 7–8)", "2026-08-25", "2026-09-05", "work"),
            ("Environment setup, Review 2 deliverables defined (wk 9)", "2026-09-15", "2026-09-19", "work"),
            ("Review 2 pipeline: ingest, mining, baseline, judge pilot (wk 10–11)", "2026-09-22", "2026-10-01", "work"),
            ("Second Review", "2026-09-29", "2026-10-03", "review"),
            ("Scaled data with real answers, embeddings, intents, leakage fix (wk 12)", "2026-10-06", "2026-10-10", "work"),
            ("Dialogue acts, candidate pool, stratified labeling queue (wk 13)", "2026-10-13", "2026-10-17", "work"),
            ("Judge selection, gold sheets, pre-registration (wk 14)", "2026-10-20", "2026-10-24", "work"),
            ("Pattern mining, rules, verifier, replay engine, baselines (wk 15)", "2026-10-27", "2026-10-31", "work"),
            ("Labeling complete, dev evaluation, admission service (wk 16)", "2026-11-03", "2026-11-06", "work"),
            ("Holiday", "2026-11-07", "2026-11-10", "holiday"),
            ("Behavior analysis, routing and trajectory set-up, documentation (wk 17)", "2026-11-11", "2026-11-14", "work"),
            ("Frozen confirmation run, demo, report and presentation", "2026-11-15", "2026-11-20", "work"),
            ("Final Review", "2026-11-17", "2026-11-21", "review")]
    colors = {"plan": NEUTRAL, "review": ALERT, "work": ACCENT, "holiday": GRID}
    fig, ax = figure(11, 6.2)
    for i, (name, a, b, kind) in enumerate(rows[::-1]):
        a, b = d(a), d(b)
        ax.barh(i, (b - a).days + 1, left=a, color=colors[kind], height=0.6)
        ax.text(b + pd.Timedelta(days=2), i, f"{a:%b %d} – {b:%b %d}", va="center", fontsize=7.5, color=MUTED)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], fontsize=7.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_xlim(d("2026-07-10"), d("2026-12-12"))
    style(ax, "Project timeline from the weekly project diary", "", "", grid_axis="x")
    save(fig, OUT / "gantt.png")


# builds every report figure
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in [act_distribution, split_timeline, label_coverage, mining_daily, near_duplicate_split, forest_main,
               forest_controls, mechanism_all, positive_control, cv_spread, trajectory, latency, rules_bar, judge_cost,
               routing_bars, gantt]:
        fn()
        print("ok", fn.__name__)


if __name__ == "__main__":
    main()
