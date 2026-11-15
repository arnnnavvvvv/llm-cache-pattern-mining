# phase 5/6: build the pair feature table with per-query, context and mined pattern features
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from gwcache import config, features, patterns, storage


# computes pair features once for the real histories and once for each placebo history mode
def main():
    turns = storage.load("turns")
    vecs = np.load(config.path("work") / "vecs.npy")
    cands = storage.load("candidates")
    base = features.pair_table(turns, cands, vecs)
    daily = patterns.mine_daily(turns)
    storage.save_result(patterns.mining_summary(daily), "pattern_mining_summary")
    for mode in ["real", "shuffled", "borrowed"]:
        tf = patterns.turn_features(turns, daily, mode=mode, seed=config.load()["seed"])
        pairs = patterns.add_to_pairs(base, turns, tf, daily, mode=mode, seed=config.load()["seed"])
        storage.save(pairs, "pairs" if mode == "real" else f"pairs_{mode}")
        print(f"{mode}: {len(pairs)} pair rows", flush=True)


if __name__ == "__main__":
    main()
