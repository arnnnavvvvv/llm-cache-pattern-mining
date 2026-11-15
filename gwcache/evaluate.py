# runs a set of admission policies through the replay engine on one evaluation period and compares them
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from gwcache import config, metrics, replay, stats
from gwcache.experiments import fit_score


# joins primary-judge labels onto the pair table
def labeled_pairs(pairs: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    l = labels[labels["judge"] == config.load()["judge"]["model"]].drop_duplicates(["turn_id", "cand_turn_id"])
    return pairs.merge(l[["turn_id", "cand_turn_id", "acceptable"]], on=["turn_id", "cand_turn_id"])


# replays every policy on the eval period and returns curves, the summary, paired comparisons and raw outcomes
def compare(pairs: pd.DataFrame, labels: pd.DataFrame, turns: pd.DataFrame, strata: pd.DataFrame,
            policies: dict[str, Callable], train_periods: list[str], eval_period: str,
            focal: str | None = None, n_boot: int | None = None) -> dict:
    cfg = config.load()
    k = cfg["candidates"]["top_k"]
    levels = cfg["eval"]["wrong_reuse_levels"]
    lab = labeled_pairs(pairs, labels)
    train = lab[lab["turn_id"].map(turns.set_index("turn_id")["period"]).isin(train_periods)]

    pos = pd.Series(np.arange(len(turns)), index=turns["turn_id"])
    judged = set(lab["turn_id"])
    eval_strata = strata[(strata["period"] == eval_period) & strata["turn_id"].isin(judged)]
    rows = pos.loc[eval_strata["turn_id"]].to_numpy()
    w = metrics.stratum_weights(eval_strata, strata[strata["period"] == eval_period])
    n_total = int((turns["period"] == eval_period).sum())
    label_map = {(a, b): v for a, b, v in lab[["turn_id", "cand_turn_id", "acceptable"]].itertuples(index=False)}
    ids = turns["turn_id"].to_numpy()

    out, curves, summary = {}, [], []
    for name, scorer in policies.items():
        cand, score = replay.to_matrices(pairs, scorer(train, pairs), len(turns), k)
        served, chosen = replay.run(cand, score, replay.threshold_grid(score, rows))
        s, wrong = metrics.outcomes(served, chosen, rows, ids, ids, label_map)
        out[name] = (s, wrong)
        curves.append(metrics.curve(s, wrong, w, n_total).assign(policy=name))
        row = {"policy": name, "eval_period": eval_period, "labeled_turns": len(rows), "period_turns": n_total,
               "best_utility": metrics.best_utility(s, wrong, w, n_total)}
        row.update({f"hit_at_wr{int(l * 100)}": metrics.hit_at(s, wrong, w, n_total, l) for l in levels})
        summary.append(row)

    comparisons = []
    if focal and n_boot:
        draws = stats.session_draws(eval_strata["session_id"].to_numpy(), n_boot, cfg["seed"])
        boots = {(p, l): stats.boot_hits(*out[p], w, n_total, l, draws) for p in out for l in levels}
        summary = [dict(r, **{f"ci_wr{int(l * 100)}": (float(np.quantile(boots[(r['policy'], l)], 0.025)),
                                                        float(np.quantile(boots[(r['policy'], l)], 0.975))) for l in levels})
                   for r in summary]
        for other in [p for p in out if p != focal]:
            pv = []
            for l in levels:
                diff = boots[(focal, l)] - boots[(other, l)]
                pv.append(stats.p_value(diff))
                comparisons.append({"comparison": f"{focal} - {other}", "level": l,
                                    "gain": next(r[f"hit_at_wr{int(l * 100)}"] for r in summary if r["policy"] == focal)
                                    - next(r[f"hit_at_wr{int(l * 100)}"] for r in summary if r["policy"] == other),
                                    "ci_low": float(np.quantile(diff, 0.025)), "ci_high": float(np.quantile(diff, 0.975)),
                                    "p_value": pv[-1]})
            for c, rej in zip(comparisons[-len(levels):], stats.holm(pv, cfg["eval"]["alpha"])):
                c["holm_reject"] = rej
    return {"curves": pd.concat(curves, ignore_index=True), "summary": pd.DataFrame(summary),
            "comparisons": pd.DataFrame(comparisons), "outcomes": out, "rows": rows, "weights": w}


# stateless k-fold x shuffles diagnostic on the training periods, per the standing rule on reporting spread
def cv_diagnostic(pairs: pd.DataFrame, labels: pd.DataFrame, turns: pd.DataFrame, feature_sets: dict[str, list[str]],
                  periods: list[str]) -> pd.DataFrame:
    cfg = config.load()
    lab = labeled_pairs(pairs, labels)
    lab = lab[lab["turn_id"].map(turns.set_index("turn_id")["period"]).isin(periods)].reset_index(drop=True)
    rows = []
    for rep in range(cfg["eval"]["n_shuffles"]):
        folds = GroupKFold(n_splits=cfg["eval"]["n_folds"], shuffle=True, random_state=cfg["seed"] + rep)
        groups = lab["turn_id"].map(turns.set_index("turn_id")["session_id"])
        for fold, (tr, te) in enumerate(folds.split(lab, groups=groups), start=1):
            for name, cols in feature_sets.items():
                test = lab.iloc[te].assign(score=fit_score(lab.iloc[tr], lab.iloc[te], cols))
                best = test.sort_values("score", ascending=False).drop_duplicates("turn_id")
                served = best["score"] >= 0
                tp = int((served & (best["acceptable"] == 1)).sum())
                prec = tp / max(int(served.sum()), 1)
                rec = tp / max(int((best["acceptable"] == 1).sum()), 1)
                rows.append({"shuffle": rep, "fold": fold, "policy": name, "precision": prec, "recall": rec,
                             "f1": 2 * prec * rec / max(prec + rec, 1e-9)})
    return pd.DataFrame(rows)


# mean, std and spread per policy from the cv diagnostic
def spread(cv: pd.DataFrame) -> pd.DataFrame:
    g = cv.groupby("policy")["f1"]
    return pd.DataFrame({"f1_mean": g.mean(), "f1_std": g.std(), "f1_spread": g.max() - g.min()}).reset_index()
