# post-hoc, descriptive only: per-act breakdown for every policy and per-turn decisions for the demo, from the frozen models
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from gwcache import config, evaluate, experiments, features, metrics, replay, storage

POLICIES = ["P1_fixed", "P2_per_intent", "P3_per_query", "P5_context", "P4_patterns", "P4plus_context_patterns"]
DEMO_POLICIES = ["P1_fixed", "P3_per_query", "P4_patterns"]


# replays each policy on the confirm period exactly as the frozen comparison does, keeping scores and chosen entries
def replay_all(pairs, labels, turns, strata) -> dict:
    cfg = config.load()
    k = cfg["candidates"]["top_k"]
    lab = evaluate.labeled_pairs(pairs, labels)
    train = lab[lab["turn_id"].map(turns.set_index("turn_id")["period"]).isin(["train", "dev"])]
    pos = pd.Series(np.arange(len(turns)), index=turns["turn_id"])
    eval_strata = strata[(strata["period"] == "confirm") & strata["turn_id"].isin(set(lab["turn_id"]))]
    rows = pos.loc[eval_strata["turn_id"]].to_numpy()
    w = metrics.stratum_weights(eval_strata, strata[strata["period"] == "confirm"])
    n_total = int((turns["period"] == "confirm").sum())
    label_map = {(a, b): v for a, b, v in lab[["turn_id", "cand_turn_id", "acceptable"]].itertuples(index=False)}
    ids = turns["turn_id"].to_numpy()
    out = {}
    pol = experiments.main_policies()
    for name in POLICIES:
        cand, score = replay.to_matrices(pairs, pol[name](train, pairs), len(turns), k)
        grid = replay.threshold_grid(score, rows)
        served, chosen = replay.run(cand, score, grid)
        s, wrong = metrics.outcomes(served, chosen, rows, ids, ids, label_map)
        out[name] = {"cand": cand, "score": score, "grid": grid, "served": served, "chosen": chosen, "s": s, "wrong": wrong}
    return {"policies": out, "rows": rows, "weights": w, "n_total": n_total, "label_map": label_map, "ids": ids}


# index of the threshold with the highest hit rate whose wrong-reuse stays at or under the level
def operating_point(s, wrong, w, n_total, level) -> int:
    c = metrics.curve(s, wrong, w, n_total)
    ok = c[(c["wrong_reuse"] <= level) & (c["hit_rate"] > 0)]
    return int(ok["hit_rate"].idxmax()) if len(ok) else len(c) - 1


# wrong-reuse and hit rate per dialogue act and position for every policy, at both pre-registered levels
def mechanism_all(res, turns) -> pd.DataFrame:
    rows, w = res["rows"], res["weights"]
    info = turns.iloc[rows][["turn_index", "act"]].reset_index(drop=True)
    info["position"] = np.where(info["turn_index"] == 0, "first_turn", "later_turn")
    out = []
    for level in config.load()["eval"]["wrong_reuse_levels"]:
        for name, p in res["policies"].items():
            ti = operating_point(p["s"], p["wrong"], w, res["n_total"], level)
            for col in ["position", "act"]:
                for g, idx in info.groupby(col).groups.items():
                    idx = np.asarray(idx)
                    served = p["s"][ti, idx]
                    served_w = (served * w[idx]).sum()
                    out.append({"level": level, "policy": name, "split_by": col, "group": g, "labeled_turns": len(idx),
                                "served_turns": int(served.sum()), "wrong_turns": int((p["wrong"][ti, idx]).sum()),
                                "wrong_reuse": (p["wrong"][ti, idx] * w[idx]).sum() / served_w if served_w else np.nan,
                                "group_hit_rate": served_w / w[idx].sum()})
    return pd.DataFrame(out)


# one row per labeled confirm turn with what each demo policy did at its 10% operating point
def demo_decisions(res, turns, pairs) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, w, ids = res["rows"], res["weights"], res["ids"]
    level = max(config.load()["eval"]["wrong_reuse_levels"])
    table = turns.iloc[rows][["turn_id", "session_id", "turn_index", "timestamp", "request", "answer", "act", "intent"]].copy()
    table["weight"] = w
    points = []
    for name in DEMO_POLICIES:
        p = res["policies"][name]
        ti = operating_point(p["s"], p["wrong"], w, res["n_total"], level)
        th = float(p["grid"][ti])
        best = np.where(p["cand"][rows] >= 0, p["score"][rows], -np.inf).max(axis=1)
        chosen = p["chosen"][ti, rows]
        table[f"{name}_served"] = p["s"][ti]
        table[f"{name}_wrong"] = p["wrong"][ti]
        table[f"{name}_score"] = best
        table[f"{name}_cand"] = np.where(chosen >= 0, ids[np.maximum(chosen, 0)], None)
        points.append({"policy": name, "level": level, "threshold": th,
                       "hit_rate": float((p["s"][ti] * w).sum() / res["n_total"]),
                       "wrong_reuse": float((p["wrong"][ti] * w).sum() / max((p["s"][ti] * w).sum(), 1e-9))})
    top = pairs[pairs["rank"] == 1].set_index("turn_id")
    keep = ["cand_turn_id", "sim", "cand_act", "pat_state_q", "pat_state_c", "same_session"]
    table = table.join(top[keep], on="turn_id")
    return table.sort_values("timestamp").reset_index(drop=True), pd.DataFrame(points)


# runs the replay once and writes the exploratory table and the demo files
def main():
    turns, labels, strata = storage.load("turns"), storage.load("labels"), storage.load("label_queue")
    pairs = features.as_categorical(storage.load("pairs"))
    res = replay_all(pairs, labels, turns, strata)
    storage.save_result(mechanism_all(res, turns), "exploratory_mechanism_all")
    table, points = demo_decisions(res, turns, pairs)
    storage.save(table, "demo_decisions")
    storage.save_result(points, "demo_operating_points")
    print(points.to_string(index=False))


if __name__ == "__main__":
    main()
