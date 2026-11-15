# phase 8: routing experiment on human-voted strong-vs-weak conversations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
import pandas as pd

from gwcache import config, routing, stats, storage


# builds data, scores routers out-of-fold, and compares quality at the configured strong-call caps
def main():
    config.set_cache_env()
    cfg = config.load()
    conv = routing.load_conversations()
    turns = routing.explode_turns(conv)
    centers = np.load(config.path("work") / "intent_centers.npy")
    turns, vecs = routing.annotate(turns, centers, joblib.load(config.path("work") / "act_model.joblib"))
    scores, folds = routing.oof_scores(conv, turns, vecs)
    y = conv["weak_ok"].to_numpy()

    curves = pd.concat([routing.quality_curve(s, y).assign(router=k) for k, s in scores.items()], ignore_index=True)
    storage.save_result(curves, "routing_curves")
    caps = cfg["routing"]["strong_share_levels"]
    summary = [{"router": "always_strong", "strong_share": 1.0, "quality": 1.0},
               {"router": "always_cheap", "strong_share": 0.0, "quality": float(y.mean())}]
    summary += [{"router": k, **{f"quality_at_strong{int(c * 100)}": routing.quality_at(s, y, c) for c in caps}} for k, s in scores.items()]

    rng = np.random.default_rng(cfg["seed"])
    draws = [rng.integers(0, len(y), len(y)) for _ in range(cfg["eval"]["n_boot"])]
    comps = []
    for other in ["per_query", "context"]:
        pv, rows = [], []
        for c in caps:
            diff = np.array([routing.quality_at(scores["patterns"][d], y[d], c) - routing.quality_at(scores[other][d], y[d], c) for d in draws])
            pv.append(stats.p_value(diff))
            rows.append({"comparison": f"patterns - {other}", "strong_cap": c,
                         "gain": routing.quality_at(scores["patterns"], y, c) - routing.quality_at(scores[other], y, c),
                         "ci_low": float(np.quantile(diff, 0.025)), "ci_high": float(np.quantile(diff, 0.975)), "p_value": pv[-1]})
        for r, rej in zip(rows, stats.holm(pv, cfg["eval"]["alpha"])):
            comps.append({**r, "holm_reject": rej})

    storage.save_result(pd.DataFrame(summary), "routing_summary")
    storage.save_result(pd.DataFrame(comps), "routing_comparisons")
    storage.save_json({"conversations": len(conv), "weak_ok_share": float(y.mean()), "turns": len(turns),
                       "h1b_pass": bool(all(c["holm_reject"] and c["gain"] > 0 for c in comps))}, "routing_verdict")
    pd.set_option("display.width", 200)
    print(pd.DataFrame(summary).to_string(index=False))
    print(pd.DataFrame(comps).to_string(index=False))


if __name__ == "__main__":
    main()
