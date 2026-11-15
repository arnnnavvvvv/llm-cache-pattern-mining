# hit rate, wrong-reuse and the hit-at-matched-wrong-reuse readout from replay results
import numpy as np
import pandas as pd

from gwcache import config


# population weight for each labeled turn: stratum size / labeled turns in that stratum
def stratum_weights(labeled: pd.DataFrame, population: pd.DataFrame) -> np.ndarray:
    key = ["period", "sim_bin"]
    pop = population.groupby(key).size()
    lab = labeled.groupby(key).size()
    w = labeled.set_index(key).index.map(lambda k: pop.get(k, 0) / lab.get(k, 1))
    return np.asarray(w, dtype=float)


# for each labeled turn and threshold: was it served, and was the served answer wrong
def outcomes(served: np.ndarray, chosen: np.ndarray, rows: np.ndarray, turn_ids: np.ndarray,
             cand_ids: np.ndarray, label_map: dict) -> tuple[np.ndarray, np.ndarray]:
    s = served[:, rows]
    wrong = np.zeros_like(s)
    for ti in range(s.shape[0]):
        for k, r in enumerate(rows):
            if s[ti, k]:
                # a missing label counts as wrong, so gaps in judging can only make a policy look worse
                wrong[ti, k] = label_map.get((turn_ids[r], cand_ids[chosen[ti, r]]), 0) == 0
    return s, wrong


# curve rows (hit rate, wrong-reuse) for every threshold from weighted outcomes
def curve(s: np.ndarray, wrong: np.ndarray, w: np.ndarray, n_total: int) -> pd.DataFrame:
    served_w = (s * w).sum(axis=1)
    wrong_w = (wrong * w).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = np.where(served_w > 0, wrong_w / served_w, 0.0)
    return pd.DataFrame({"hit_rate": served_w / n_total, "wrong_reuse": wr})


# best hit rate with wrong-reuse at or under the level, 0 if no threshold qualifies
def hit_at(s: np.ndarray, wrong: np.ndarray, w: np.ndarray, n_total: int, level: float) -> float:
    c = curve(s, wrong, w, n_total)
    ok = c[(c["wrong_reuse"] <= level) & (c["hit_rate"] > 0)]
    return float(ok["hit_rate"].max()) if len(ok) else 0.0


# net utility per request at the threshold that maximises it, using the configured reuse value and wrong-reuse cost
def best_utility(s: np.ndarray, wrong: np.ndarray, w: np.ndarray, n_total: int) -> float:
    d = config.load()["decision"]
    good = ((s & ~wrong) * w).sum(axis=1)
    bad = (wrong * w).sum(axis=1)
    return float(((d["reuse_utility"] * good - d["wrong_reuse_cost"] * bad) / n_total).max())
