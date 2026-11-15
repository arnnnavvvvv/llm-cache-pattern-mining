# candidate pool (top-k earlier turns per turn) and the stratified labeling queue
import numpy as np
import pandas as pd

from gwcache import config, embed


# top-k strictly-earlier neighbours of every turn above the similarity floor, as long rows
def build(turns: pd.DataFrame, vecs: np.ndarray) -> pd.DataFrame:
    cfg = config.load()["candidates"]
    sims, ids = embed.causal_top_k(vecs, cfg["top_k"])
    rows = []
    turn_ids = turns["turn_id"].to_numpy()
    for i in range(len(turns)):
        for r in range(cfg["top_k"]):
            if ids[i, r] >= 0 and sims[i, r] >= cfg["sim_floor"]:
                rows.append({"turn_id": turn_ids[i], "rank": r + 1, "cand_turn_id": turn_ids[ids[i, r]], "sim": float(sims[i, r])})
    return pd.DataFrame(rows)


# wide view: one row per turn that has candidates, with its sim_1..sim_k
def top_sims(cands: pd.DataFrame) -> pd.DataFrame:
    wide = cands.pivot(index="turn_id", columns="rank", values="sim")
    wide.columns = [f"sim_{c}" for c in wide.columns]
    return wide.reset_index()


# stratum of each turn: its period and the bin of its best candidate's similarity
def strata(turns: pd.DataFrame, cands: pd.DataFrame) -> pd.DataFrame:
    bins = config.load()["labels"]["sim_bins"]
    best = cands[cands["rank"] == 1][["turn_id", "sim"]]
    s = turns[["turn_id", "period", "session_id"]].merge(best, on="turn_id")
    s["sim_bin"] = pd.cut(s["sim"], bins, right=False, labels=False)
    return s.dropna(subset=["sim_bin"]).astype({"sim_bin": int})


# random order inside every (period, bin) stratum, interleaved so any prefix is a stratified sample
def queue(st: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(config.load()["seed"])
    st = st.copy()
    st["rank_in_stratum"] = 0.0
    for _, idx in st.groupby(["period", "sim_bin"]).groups.items():
        idx = np.asarray(idx)
        # fractional rank, so strata of different sizes interleave in proportion to their size
        st.loc[rng.permutation(idx), "rank_in_stratum"] = (np.arange(len(idx)) + rng.random()) / len(idx)
    st = st.sort_values("rank_in_stratum").reset_index(drop=True)
    st["queue_order"] = np.arange(len(st))
    return st.drop(columns=["rank_in_stratum"])
