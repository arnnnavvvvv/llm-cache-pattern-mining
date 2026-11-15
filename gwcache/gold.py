# human gold set: blind rating sheets for two raters and judge-human agreement
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from gwcache import config
from gwcache.acts import head_tail


# picks gold pairs from already-judged training/dev turns, spread across similarity bins
def pick(labels: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    cfg = config.load()
    pool = labels.merge(st[["turn_id", "period", "sim_bin"]], on="turn_id")
    pool = pool[pool["period"] != "confirm"].drop_duplicates(["turn_id", "cand_turn_id"])
    per_bin = cfg["labels"]["gold_size"] // max(pool["sim_bin"].nunique(), 1)
    gold = pool.groupby("sim_bin", group_keys=False).apply(lambda g: g.sample(n=min(per_bin, len(g)), random_state=cfg["seed"]))
    return gold[["turn_id", "cand_turn_id"]].reset_index(drop=True)


# one shuffled sheet per rater showing exactly what the judge saw, without any verdict
def sheets(gold: pd.DataFrame, turns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    j = config.load()["judge"]
    t = turns.set_index("turn_id")
    base = pd.DataFrame({
        "turn_id": gold["turn_id"], "cand_turn_id": gold["cand_turn_id"],
        "new_request": gold["turn_id"].map(lambda x: head_tail(t.at[x, "request"], j["request_chars"])),
        "reference_answer": gold["turn_id"].map(lambda x: head_tail(t.at[x, "answer"], j["answer_chars"])),
        "earlier_request": gold["cand_turn_id"].map(lambda x: head_tail(t.at[x, "request"], j["request_chars"])),
        "cached_answer": gold["cand_turn_id"].map(lambda x: head_tail(t.at[x, "answer"], j["answer_chars"])),
        "acceptable_YES_NO": "",
    })
    return {r: base.sample(frac=1, random_state=k) for k, r in enumerate(["rater_a", "rater_b"])}


# reads a filled sheet into a (turn, candidate) -> bool series, skipping blanks
def read_sheet(df: pd.DataFrame) -> pd.Series:
    v = df["acceptable_YES_NO"].astype(str).str.strip().str.upper()
    df = df[v.isin(["YES", "NO"])]
    return pd.Series((v[v.isin(["YES", "NO"])] == "YES").to_numpy(), index=pd.MultiIndex.from_frame(df[["turn_id", "cand_turn_id"]]))


# raw agreement and cohen's kappa on the overlap of two label series
def agreement(name: str, a: pd.Series, b: pd.Series) -> dict:
    both = a.index.intersection(b.index)
    if not len(both):
        return {"comparison": name, "n": 0, "raw_agreement": np.nan, "kappa": np.nan}
    x, y = a.loc[both].astype(int), b.loc[both].astype(int)
    kappa = cohen_kappa_score(x, y) if len(set(x) | set(y)) > 1 else np.nan
    return {"comparison": name, "n": len(both), "raw_agreement": float((x == y).mean()), "kappa": kappa}


# label series for one judge from the long label table
def judge_series(labels: pd.DataFrame, model: str) -> pd.Series:
    l = labels[labels["judge"] == model].drop_duplicates(["turn_id", "cand_turn_id"])
    return pd.Series(l["acceptable"].astype(bool).to_numpy(), index=pd.MultiIndex.from_frame(l[["turn_id", "cand_turn_id"]]))
