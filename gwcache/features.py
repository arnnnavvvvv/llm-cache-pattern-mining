# per-candidate features for the learned admission policies (per-query and context, no mining)
import numpy as np
import pandas as pd

from gwcache import config

PER_QUERY = ["sim", "rank", "turn_index", "sim_1", "sim_2", "sim_3", "sim_margin", "sim_softmax", "intent", "cand_intent",
             "same_intent", "act", "cand_act", "same_session", "same_user", "log_gap", "log_req_len",
             "log_cand_req_len", "log_cand_ans_len"]
CONTEXT = ["ctx_sim", "ctx_to_cand_req", "req_to_cand_ctx", "has_ctx"]
CATEGORICAL = ["intent", "cand_intent", "act", "cand_act"]


# restores categorical dtypes with fixed category lists (parquet round-trips can drop them)
def as_categorical(df: pd.DataFrame) -> pd.DataFrame:
    cfg = config.load()
    cats = {"intent": list(range(cfg["intents"]["k"])), "act": cfg["acts"]["labels"]}
    df = df.copy()
    for col in CATEGORICAL:
        df[col] = pd.Categorical(df[col].astype(object if "act" in col else int), categories=cats["act" if "act" in col else "intent"])
    return df


# mean embedding of each turn's previous (up to two) turns in its session, zeros for first turns
def context_vectors(turns: pd.DataFrame, vecs: np.ndarray) -> np.ndarray:
    pos = np.arange(len(turns))
    ctx = np.zeros_like(vecs)
    order = turns.assign(pos=pos).sort_values(["session_id", "turn_index"])
    for _, g in order.groupby("session_id"):
        p = g["pos"].to_numpy()
        for j in range(1, len(p)):
            v = vecs[p[max(0, j - 2) : j]].mean(axis=0)
            ctx[p[j]] = v / (np.linalg.norm(v) or 1.0)
    return ctx


# one row per (turn, candidate) with every feature a policy might use
def pair_table(turns: pd.DataFrame, cands: pd.DataFrame, vecs: np.ndarray) -> pd.DataFrame:
    tau = config.load()["decision"]["softmax_temperature"]
    pos = pd.Series(np.arange(len(turns)), index=turns["turn_id"])
    t = turns.set_index("turn_id")
    p = cands.copy()
    p["pos"] = pos.loc[p["turn_id"]].to_numpy()
    p["cand_pos"] = pos.loc[p["cand_turn_id"]].to_numpy()

    wide = p.pivot(index="turn_id", columns="rank", values="sim")
    for k in (1, 2, 3):
        p[f"sim_{k}"] = p["turn_id"].map(wide[k]) if k in wide.columns else np.nan
    p["sim_margin"] = p["sim_1"] - p["sim_2"].fillna(0)
    expo = np.exp((p["sim"] - p["sim_1"]) / tau)
    p["sim_softmax"] = expo / expo.groupby(p["turn_id"]).transform("sum")

    for col, src in [("intent", "intent"), ("act", "act"), ("session_id", "session_id"), ("user_id", "user_id")]:
        p[col] = t.loc[p["turn_id"], src].to_numpy()
        p[f"cand_{col}"] = t.loc[p["cand_turn_id"], src].to_numpy()
    p["same_intent"] = (p["intent"] == p["cand_intent"]).astype(int)
    p["same_session"] = (p["session_id"] == p["cand_session_id"]).astype(int)
    p["same_user"] = (p["user_id"] == p["cand_user_id"]).astype(int)
    gap = (t.loc[p["turn_id"], "timestamp"].reset_index(drop=True)
           - t.loc[p["cand_turn_id"], "timestamp"].reset_index(drop=True)).dt.total_seconds().to_numpy(dtype=float)
    p["gap_days"] = np.clip(gap, 0, None) / 86400
    p["log_gap"] = np.log1p(np.clip(gap, 0, None))
    p["turn_index"] = t.loc[p["turn_id"], "turn_index"].to_numpy()
    p["log_req_len"] = np.log1p(t.loc[p["turn_id"], "request"].str.len().to_numpy())
    p["log_cand_req_len"] = np.log1p(t.loc[p["cand_turn_id"], "request"].str.len().to_numpy())
    p["log_cand_ans_len"] = np.log1p(t.loc[p["cand_turn_id"], "answer"].str.len().to_numpy())

    ctx = context_vectors(turns, vecs)
    a, b = p["pos"].to_numpy(), p["cand_pos"].to_numpy()
    p["has_ctx"] = (np.linalg.norm(ctx[a], axis=1) > 0).astype(int)
    p["ctx_sim"] = np.einsum("ij,ij->i", ctx[a], ctx[b])
    p["ctx_to_cand_req"] = np.einsum("ij,ij->i", ctx[a], vecs[b])
    p["req_to_cand_ctx"] = np.einsum("ij,ij->i", vecs[a], ctx[b])
    return as_categorical(p).drop(columns=["session_id", "cand_session_id", "user_id", "cand_user_id"])
