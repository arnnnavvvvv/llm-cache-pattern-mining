# interactive demo: replays the held-out confirmation period through the frozen admission policies side by side
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from gwcache import config, storage
from gwcache.plotstyle import ACTS, COLORS, LABELS, SHORT

RES = config.path("results")
FIG = config.path("figures")
DEMO = ["P1_fixed", "P3_per_query", "P4_patterns"]
PAGES = ["Replay", "Inspect a decision", "Operating point", "Findings", "Live admission"]

st.set_page_config(page_title="Behavior-aware cache admission", layout="wide")


# decision table, operating points, turn texts and judge labels, loaded once and shared by every session
@st.cache_resource
def load():
    table = storage.load("demo_decisions")
    turns = storage.load("turns")
    confirm_times = np.sort(turns.loc[turns["period"] == "confirm", "timestamp"].to_numpy())
    table["period_turns_so_far"] = np.searchsorted(confirm_times, table["timestamp"].to_numpy(), side="right")
    points = pd.read_csv(RES / "demo_operating_points.csv").set_index("policy")
    labels = storage.load("labels")
    label_map = {(a, b): int(v) for a, b, v in labels[["turn_id", "cand_turn_id", "acceptable"]].itertuples(index=False)}
    text = turns.set_index("turn_id")[["request", "answer", "act", "turn_index", "session_id"]]
    rules = pd.read_csv(RES / "behavioral_rules.csv")
    return table, points, label_map, text, rules, len(confirm_times)


# short single-line preview of a long text
def clip(s: str, n: int = 110) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


# weighted hit rate and wrong reuse for one policy over the first k replayed turns
def running(table: pd.DataFrame, k: int, policy: str) -> dict:
    t = table.iloc[:k]
    served_w = (t[f"{policy}_served"] * t["weight"]).sum()
    wrong_w = (t[f"{policy}_wrong"] * t["weight"]).sum()
    return {"hit": served_w / max(t["period_turns_so_far"].iloc[-1], 1), "wrong": wrong_w / served_w if served_w else 0.0,
            "served": int(t[f"{policy}_served"].sum()), "wrong_n": int(t[f"{policy}_wrong"].sum())}


# outcome label for one policy on one turn
def outcome(row, policy: str) -> str:
    if not row[f"{policy}_served"]:
        return "call LLM"
    return "served, WRONG" if row[f"{policy}_wrong"] else "served, ok"


# cell colours for the outcome columns
def colour(v: str) -> str:
    if v == "served, ok":
        return "background-color: #e3f5ec; color: #0b5b3c"
    if v == "served, WRONG":
        return "background-color: #fbe3e3; color: #8c1d1d; font-weight: 600"
    return "color: #7a7975"


# page: step through the confirmation period and watch the three policies decide
def page_replay(table, points, n_confirm):
    st.subheader("Replay of the held-out confirmation period")
    st.caption(f"{len(table):,} judged requests that had a cached candidate (out of {n_confirm:,} confirm-period requests). "
               "Each policy runs at its own operating point for at most 10% wrong reuse, using the frozen models.")
    qp = st.query_params
    k0 = int(qp.get("step", len(table) // 3))
    c1, c2 = st.columns([4, 1])
    if "next_step" in st.session_state:
        st.session_state["step"] = st.session_state.pop("next_step")
    elif "step" not in st.session_state:
        st.session_state["step"] = min(k0, len(table))
    k = c1.slider("Requests replayed", 1, len(table), key="step")
    play = c2.toggle("Play", value=False)
    cols = st.columns(3)
    for col, p in zip(cols, DEMO):
        r = running(table, k, p)
        col.markdown(f"<div style='border-left:6px solid {COLORS[p]};padding-left:10px'><b>{LABELS[p]}</b></div>",
                     unsafe_allow_html=True)
        a, b = col.columns(2)
        a.metric("Hit rate (all requests)", f"{r['hit'] * 100:.2f}%")
        b.metric("Wrong reuse (of served)", f"{r['wrong'] * 100:.1f}%")
        col.caption(f"{r['served']} served, {r['wrong_n']} judged wrong (raw counts; rates are population-weighted)")
    recent = table.iloc[max(0, k - 12):k].iloc[::-1]
    view = pd.DataFrame({"time": recent["timestamp"].dt.strftime("%b %d %H:%M"),
                         "act": recent["act"].map(ACTS), "request": recent["request"].map(clip),
                         "similarity": recent["sim"].round(3)})
    for p in DEMO:
        view[SHORT[p]] = [outcome(r, p) for _, r in recent.iterrows()]
    st.markdown("**Latest requests** (newest first)")
    st.dataframe(view.style.map(colour, subset=[SHORT[p] for p in DEMO]).format({"similarity": "{:.3f}"}), hide_index=True, width="stretch")
    steps = np.unique(np.linspace(20, k, min(k, 120)).astype(int))
    hist = pd.DataFrame([{"replayed": s, "policy": LABELS[p], "hit rate (%)": running(table, s, p)["hit"] * 100}
                         for s in steps for p in DEMO])
    chart = alt.Chart(hist).mark_line(strokeWidth=2).encode(
        x="replayed:Q", y="hit rate (%):Q",
        color=alt.Color("policy:N", scale=alt.Scale(domain=[LABELS[p] for p in DEMO], range=[COLORS[p] for p in DEMO])))
    st.altair_chart(chart.properties(height=220), width="stretch")
    if k == len(table):
        st.success("End of the period: " + ", ".join(f"{SHORT[p]} {points.loc[p, 'hit_rate'] * 100:.2f}% hit" for p in DEMO)
                   + " — the same figures as the confirmation table.")
    if play and k < len(table):
        time.sleep(0.15)
        st.session_state["next_step"] = min(k + 15, len(table))
        st.rerun()


# matched association rule for a request/entry state pair, if one was mined with enough support
def find_rule(rules, row):
    m = rules[(rules["pat_state_q"] == row["pat_state_q"]) & (rules["act"] == row["act"]) &
              (rules["pat_state_c"] == row["pat_state_c"]) & (rules["cand_act"] == row["cand_act"])]
    return m.iloc[0] if len(m) else None


# page: open one decision and see why each policy served or refused it
def page_inspect(table, points, label_map, text, rules):
    st.subheader("Why was this served or blocked?")
    filters = {"P3 served a wrong answer, P4 refused": (table["P3_per_query_wrong"]) & (~table["P4_patterns_served"]),
               "P4 served a correct answer": table["P4_patterns_served"] & ~table["P4_patterns_wrong"],
               "corrections and follow-ups with a near-duplicate": table["act"].isin(["correction", "follow_up"]) & (table["sim"] >= 0.97),
               "all judged requests": pd.Series(True, index=table.index)}
    names = list(filters)
    f = st.radio("Show", names, index=int(st.query_params.get("filter", 0)), horizontal=True)
    sub = table[filters[f]]
    if sub.empty:
        st.info("No requests in this group.")
        return
    options = sub.index.tolist()
    pick = st.selectbox("Request", options, index=min(int(st.query_params.get("pick", 0)), len(options) - 1),
                        format_func=lambda i: f"{table.loc[i, 'timestamp']:%b %d %H:%M} · {ACTS.get(table.loc[i, 'act'], table.loc[i, 'act'])} · {clip(table.loc[i, 'request'], 70)}")
    row = table.loc[pick]
    cand = row["cand_turn_id"]
    left, right = st.columns(2)
    with left:
        st.markdown("**New request**")
        st.info(clip(row["request"], 600))
        st.markdown(f"Dialogue act: **{ACTS.get(row['act'], row['act'])}** · turn {int(row['turn_index']) + 1} of its session · "
                    f"behavioral state: `{row['pat_state_q']}`")
        st.markdown("**What the model actually answered (reference)**")
        st.caption(clip(row["answer"], 500))
    with right:
        st.markdown(f"**Closest cached entry** (similarity {row['sim']:.3f})")
        st.warning(clip(text.loc[cand, "request"], 600))
        st.markdown(f"Its act: **{ACTS.get(row['cand_act'], row['cand_act'])}** · its state when asked: `{row['pat_state_c']}` · "
                    f"{'same session' if row['same_session'] else 'different session'}")
        st.markdown("**Cached answer that would be served**")
        st.caption(clip(text.loc[cand, "answer"], 500))
    verdict = label_map.get((row["turn_id"], cand))
    st.markdown("---")
    a, b, c = st.columns([1.2, 1.4, 2])
    a.metric("Judge verdict on reusing it", {1: "acceptable", 0: "not acceptable"}.get(verdict, "not judged"))
    rule = find_rule(rules, row)
    if rule is not None:
        b.metric("Mined rule: past reuse acceptable", f"{rule['acceptable_rate'] * 100:.0f}%")
        b.caption(f"rule ({row['pat_state_q']}, {row['act']}) -> ({row['pat_state_c']}, {row['cand_act']}), {int(rule['pairs'])} past judged pairs")
    else:
        b.metric("Mined rule", "no rule with enough support")
    decisions = pd.DataFrame([{"policy": LABELS[p], "score": round(float(row[f"{p}_score"]), 3),
                               "threshold": round(float(points.loc[p, "threshold"]), 3), "decision": outcome(row, p)} for p in DEMO])
    c.dataframe(decisions.style.map(colour, subset=["decision"]).format({"score": "{:.3f}", "threshold": "{:.3f}"}), hide_index=True, width="stretch")
    st.caption("P1 compares raw similarity with one global threshold; P3 and P4 compare the verifier score with the threshold that "
               "keeps their wrong reuse at or under 10% on this period. P4 also sees the mined behavioral state and rule prior.")


# page: drag the wrong-reuse budget and read each policy's hit rate off its real curve
def page_operating():
    st.subheader("Pick an operating point")
    curves = pd.read_csv(RES / "confirm_curves.csv")
    target = st.slider("Allowed wrong reuse (% of served answers)", 1, 30, int(st.query_params.get("target", 10)))
    rows = []
    for p in LABELS:
        c = curves[(curves["policy"] == p) & (curves["wrong_reuse"] <= target / 100) & (curves["hit_rate"] > 0)]
        rows.append({"policy": LABELS[p], "hit rate (%)": c["hit_rate"].max() * 100 if len(c) else 0.0})
    best = pd.DataFrame(rows)
    best["per 1,000 requests"] = (best["hit rate (%)"] * 10).round(1)
    best["hit rate (%)"] = best["hit rate (%)"].round(2)
    left, right = st.columns([1, 1.3])
    bars = alt.Chart(best).mark_bar().encode(
        y=alt.Y("policy:N", sort=list(LABELS.values()), title=None), x="hit rate (%):Q",
        color=alt.Color("policy:N", scale=alt.Scale(domain=list(LABELS.values()), range=list(COLORS.values())), legend=None))
    left.altair_chart(bars.properties(height=260), width="stretch")
    left.dataframe(best, hide_index=True, width="stretch")
    c = curves[(curves["wrong_reuse"] <= 0.30) & (curves["hit_rate"] > 0)].copy()
    c["wrong reuse (%)"], c["hit rate (%)"] = c["wrong_reuse"] * 100, c["hit_rate"] * 100
    c["policy"] = c["policy"].map(LABELS)
    lines = alt.Chart(c).mark_line(strokeWidth=1.6).encode(
        x="wrong reuse (%):Q", y="hit rate (%):Q", order="hit rate (%):Q",
        color=alt.Color("policy:N", scale=alt.Scale(domain=list(LABELS.values()), range=list(COLORS.values()))))
    rule = alt.Chart(pd.DataFrame({"x": [target]})).mark_rule(strokeDash=[4, 4], color="#52514e").encode(x="x:Q")
    right.altair_chart((lines + rule).properties(height=380), width="stretch")
    st.caption("Curves are the confirmation-period replay (results/confirm_curves.csv); every point is a real threshold.")


# page: the headline finding and the honest negative results
def page_findings():
    st.subheader("What the data says")
    nd = pd.read_csv(RES / "near_duplicate_behavior.csv").set_index(["behavior", "side"])
    a, b, c = st.columns(3)
    a.metric("Near-duplicates served wrong by a similarity cache", f"{nd.loc[('all', 'all'), 'wrong_reuse'] * 100:.1f}%")
    b.metric("…when the request depends on context", f"{nd.loc[('context_dependent', 'request'), 'wrong_reuse'] * 100:.1f}%")
    c.metric("…when it is self-contained", f"{nd.loc[('self_contained', 'request'), 'wrong_reuse'] * 100:.1f}%")
    left, right = st.columns(2)
    left.image(str(FIG / "wrong_reuse_by_act.png"), caption="Wrong reuse by similarity band and dialogue act")
    right.image(str(FIG / "report" / "forest_main.png"), caption="P4 beats the fixed threshold; ties the learned comparators")
    st.markdown("#### Results that did not work")
    r = pd.read_csv(RES / "routing_summary.csv").set_index("router")
    traj = pd.read_json(RES / "trajectory_summary.json", typ="series")
    x, y = st.columns(2)
    x.metric("Pattern router quality at 30% strong-model budget", f"{r.loc['patterns', 'quality_at_strong30'] * 100:.1f}%",
             "random routing: 62.1%", delta_color="off")
    y.metric("Trajectory fast-tracks that would satisfy the user", "4.8%", f"{int(traj['judged'])} judged sessions", delta_color="off")
    x.image(str(FIG / "routing_curves.png"))
    y.image(str(FIG / "report" / "trajectory_curve.png"))


# admission engine loaded with the frozen bundle and seeded with the latest real development-period traffic
@st.cache_resource
def engine(n_seed: int):
    import importlib.util

    spec = importlib.util.spec_from_file_location("svc", ROOT / "scripts" / "12_service.py")
    svc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(svc)
    eng = svc.build_engine()
    turns = storage.load("turns")
    for r in turns[turns["period"] == "dev"].tail(n_seed).itertuples():
        eng.record(r.session_id, r.user_id, r.turn_id, r.request, r.answer, r.act, int(r.intent))
    return eng, turns.set_index("turn_id")["request"]


# page: type requests into a session and watch the running admission service decide
def page_live():
    st.subheader("Live admission service")
    n_seed = 3000
    with st.spinner(f"Loading the frozen model and seeding {n_seed:,} real cached requests…"):
        eng, req_text = engine(n_seed)
    th = float(pd.read_csv(RES / "demo_operating_points.csv").set_index("policy").loc["P4_patterns", "threshold"])
    st.caption(f"{len(eng.cache_meta):,} cached entries from the end of the development period. Each request goes through the "
               f"same code path as the /admit endpoint; a cached answer is served when the expected-benefit score B = 2q - 1 "
               f"reaches {th:.2f}, P4's operating point for at most 10% wrong reuse on the held-out period.")
    if "live_session" not in st.session_state:
        st.session_state["live_session"] = f"demo-{int(time.time())}"
        st.session_state["live_log"] = []
    text = st.text_input("Request", st.query_params.get("q", ""))
    a, b = st.columns([1, 5])
    if a.button("Send", type="primary") and text.strip():
        out = eng.admit(st.session_state["live_session"], "demo-user", text.strip())
        st.session_state["live_log"].insert(0, (text.strip(), out))
    if b.button("New session"):
        st.session_state["live_session"] = f"demo-{int(time.time())}"
        st.session_state["live_log"] = []
    for req, out in st.session_state["live_log"]:
        serve = "score" in out and out["score"] >= th
        verdict = "SERVE" if serve else ("BLOCK" if "candidate" in out else "NO MATCH")
        st.markdown(f"**{req}**")
        cols = st.columns(4)
        cols[0].metric("Decision", verdict)
        cols[1].metric("Dialogue act", ACTS.get(out["act"], out["act"]))
        cols[2].metric("Score B vs threshold", f"{out['score']:.2f} / {th:.2f}" if "score" in out else "–")
        cols[3].metric("Latency", f"{out['latency_ms']:.0f} ms")
        if "candidate" in out:
            st.caption(("Serving the answer cached for: " if serve else "Closest cached request (not reused): ")
                       + clip(req_text.get(out["candidate"], ""), 200))
        else:
            st.caption("No cached request with similarity >= 0.70, so the request goes to the LLM.")
        st.markdown("---")


# sidebar navigation, with the page also selectable from the url
def main():
    table, points, label_map, text, rules, n_confirm = load()
    st.sidebar.title("Cache admission demo")
    st.sidebar.caption("WildChat, held-out period Apr 20–23 2023 · frozen models (tag freeze-confirm-2026-11-16)")
    page = st.sidebar.radio("Page", PAGES, index=PAGES.index(st.query_params.get("page", "Replay")))
    st.sidebar.markdown("---")
    st.sidebar.caption("P1: one similarity threshold (GPTCache-style)\n\nP3: learned verifier with dialogue acts\n\n"
                       "P4: P3 plus mined behavioral patterns and rules")
    if page == "Replay":
        page_replay(table, points, n_confirm)
    elif page == "Inspect a decision":
        page_inspect(table, points, label_map, text, rules)
    elif page == "Operating point":
        page_operating()
    elif page == "Findings":
        page_findings()
    else:
        page_live()


main()
