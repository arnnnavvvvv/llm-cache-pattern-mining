# picks the judge model: same training turns through each candidate model, comparing token use, cost and agreement
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, judge, storage

MODELS = {"claude-haiku-5.5": (9.90, 49.49), "claude-sonnet-5.5": (197.95, 989.75), "claude-opus-5.5": (395.90, 1979.50)}


# summed token usage of the cached responses for these models, read back from the disk cache
def usage_by_model() -> dict:
    out = {}
    for m in MODELS:
        files = list((config.path("llm_cache") / m.replace("/", "_")).glob("*.json"))
        used = [json.loads(f.read_text(encoding="utf-8")).get("usage", {}) for f in files]
        out[m] = {"input": sum(u.get("input", 0) for u in used), "output": sum(u.get("output", 0) for u in used)}
    return out


# labels the first n training turns of the queue with every model and reports agreement and projected cost
def main(n: int = 100):
    turns, cands, queue = storage.load("turns"), storage.load("candidates"), storage.load("label_queue")
    pick = queue[queue["period"] == "train"]["turn_id"].head(n).tolist()
    frames = {m: judge.label(pick, turns, cands, m) for m in MODELS}
    storage.save(pd.concat(frames.values(), ignore_index=True), "judge_pick_labels")
    labels = {m: f.set_index(["turn_id", "cand_turn_id"])["acceptable"] for m, f in frames.items()}
    total_turns = len(queue)
    usage = usage_by_model()
    rows = []
    for m, (p_in, p_out) in MODELS.items():
        u = usage[m]
        per_turn_in, per_turn_out = u["input"] / n, u["output"] / n
        rows.append({"model": m, "pairs": len(labels[m]), "acceptable_share": labels[m].mean(),
                     "in_tokens_per_turn": per_turn_in, "out_tokens_per_turn": per_turn_out,
                     "cost_inr_this_run": (u["input"] * p_in + u["output"] * p_out) / 1e6,
                     "projected_inr_full_queue": total_turns * (per_turn_in * p_in + per_turn_out * p_out) / 1e6})
    agree = []
    names = list(MODELS)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = labels[names[i]], labels[names[j]]
            both = a.index.intersection(b.index)
            agree.append({"pair": f"{names[i]} vs {names[j]}", "n": len(both), "agreement": float((a.loc[both] == b.loc[both]).mean())})
    storage.save_result(pd.DataFrame(rows), "judge_pick_cost")
    storage.save_result(pd.DataFrame(agree), "judge_pick_agreement")
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(pd.DataFrame(agree).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
