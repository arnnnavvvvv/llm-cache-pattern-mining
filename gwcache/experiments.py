# policy sets, placebo scorers, the positive control and the mechanism breakdown
import numpy as np
import pandas as pd

from gwcache import config, decision, metrics, patterns
from gwcache.features import CONTEXT, PER_QUERY

FEATURE_SETS = {
    "P3_per_query": PER_QUERY,
    "P5_context": PER_QUERY + CONTEXT,
    "P4_patterns": PER_QUERY + patterns.ALL,
    "P4plus_context_patterns": PER_QUERY + CONTEXT + patterns.ALL,
}
ABLATIONS = {
    "abl_frequent_only": PER_QUERY + patterns.SESSION_FREQ,
    "abl_sequential_only": PER_QUERY + patterns.SESSION_SEQ,
    "abl_session_only": PER_QUERY + patterns.SESSION_SEQ + patterns.SESSION_FREQ,
    "abl_user_only": PER_QUERY + patterns.USER_SEQ,
}


# scorer that trains the verifier on the given columns and scores every pair
def learned(cols: list[str]):
    # closure used by the replay comparison
    def scorer(train: pd.DataFrame, pairs: pd.DataFrame) -> np.ndarray:
        return decision.score_learned(decision.fit_verifier(train, cols), pairs, cols)
    return scorer


# scorer for a placebo: same training rows and columns, but features taken from a scrambled-history table
def placebo(table: pd.DataFrame, cols: list[str]):
    # closure that swaps in the placebo features by (turn, candidate) key
    def scorer(train: pd.DataFrame, pairs: pd.DataFrame) -> np.ndarray:
        assert (table["turn_id"].to_numpy() == pairs["turn_id"].to_numpy()).all()
        tr = table.merge(train[["turn_id", "cand_turn_id", "acceptable"]], on=["turn_id", "cand_turn_id"])
        return decision.score_learned(decision.fit_verifier(tr, cols), table, cols)
    return scorer


# the main comparison set: fixed threshold, per-intent thresholds and the learned policies
def main_policies() -> dict:
    pol = {"P1_fixed": lambda tr, p: decision.score_fixed(p), "P2_per_intent": lambda tr, p: decision.score_per_intent(p, tr)}
    pol.update({name: learned(cols) for name, cols in FEATURE_SETS.items()})
    return pol


# per-group hit rate and wrong-reuse for two policies at their best threshold under the given wrong-reuse level
def mechanism(result: dict, strata: pd.DataFrame, turns: pd.DataFrame, policies: list[str], level: float) -> pd.DataFrame:
    rows_idx, w = result["rows"], result["weights"]
    info = turns.iloc[rows_idx][["turn_index", "act"]].reset_index(drop=True)
    info["group_position"] = np.where(info["turn_index"] == 0, "first_turn", "later_turn")
    out = []
    n_total = result["summary"]["period_turns"].iloc[0]
    for name in policies:
        s, wrong = result["outcomes"][name]
        c = metrics.curve(s, wrong, w, n_total)
        ok = c[(c["wrong_reuse"] <= level) & (c["hit_rate"] > 0)]
        if ok.empty:
            continue
        ti = int(ok["hit_rate"].idxmax())
        for col in ["group_position", "act"]:
            for g, idx in info.groupby(col).groups.items():
                idx = np.asarray(idx)
                served_w = (s[ti, idx] * w[idx]).sum()
                out.append({"policy": name, "split_by": col, "group": g, "labeled_turns": len(idx),
                            "served_weight": served_w, "wrong_reuse": (wrong[ti, idx] * w[idx]).sum() / served_w if served_w else np.nan,
                            "group_hit_rate": served_w / w[idx].sum()})
    return pd.DataFrame(out)


# semi-synthetic traffic where reuse is only safe on turns that do not depend on context, and that dependence
# follows the session's behavior; similarity carries no signal and the observed act is noisy
def positive_control(n_sessions: int = 3000, act_noise: float = 0.4, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    acts = ["new_request", "follow_up", "continuation", "correction"]
    rows = []
    for s in range(n_sessions):
        refiner = rng.random() < 0.5
        day = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=int(s * 10 / n_sessions))
        for k in range(int(rng.integers(3, 7))):
            dependent = k > 0 and (rng.random() < (0.85 if refiner else 0.15))
            true_act = acts[int(rng.integers(1, 4))] if dependent else "new_request"
            seen = true_act if rng.random() > act_noise else acts[int(rng.integers(0, 4))]
            rows.append({"turn_id": f"s{s}-{k}", "session_id": f"s{s}", "user_id": f"u{s % 400}", "turn_index": k,
                         "timestamp": day + pd.Timedelta(seconds=int(rng.integers(0, 80000)) + k * 60),
                         "intent": int(rng.integers(0, 5)), "act": seen, "acceptable": int(not dependent),
                         "sim": float(rng.uniform(0.85, 1.0))})
    return pd.DataFrame(rows)


# runs per-query vs pattern-aware verifiers on the positive control and reports hit at matched wrong-reuse
def run_positive_control() -> pd.DataFrame:
    cfg = config.load()
    turns = positive_control(seed=cfg["seed"])
    daily = patterns.mine_daily(turns)
    tf = patterns.turn_features(turns, daily)
    turns = turns.join(tf[["pat_act_conf", "pat_dep_prior", "pat_intent_conf", "pat_freq_support", "pat_freq_matches"]], on="turn_id")
    turns = turns[turns["turn_index"] > 0].copy()
    turns["act"] = turns["act"].astype("category")
    turns["gap_days"] = 0.0
    day = turns["timestamp"].dt.floor("D")
    train, test = turns[day < day.quantile(0.6)], turns[day >= day.quantile(0.6)]
    sets = {"per_query": ["sim", "turn_index", "act"],
            "patterns": ["sim", "turn_index", "act", "pat_act_conf", "pat_dep_prior", "pat_freq_support", "pat_freq_matches"]}
    out = []
    for name, cols in sets.items():
        score = decision.score_learned(decision.fit_verifier(train, cols), test, cols)
        order = np.argsort(-score)
        y = test["acceptable"].to_numpy()[order]
        served = np.arange(1, len(y) + 1)
        wr = np.cumsum(1 - y) / served
        row = {"policy": name, "test_turns": len(test), "safe_share": float(test["acceptable"].mean())}
        for level in cfg["eval"]["wrong_reuse_levels"]:
            ok = served[wr <= level]
            row[f"hit_at_wr{int(level * 100)}"] = float(ok.max() / len(y)) if len(ok) else 0.0
        out.append(row)
    return pd.DataFrame(out)
