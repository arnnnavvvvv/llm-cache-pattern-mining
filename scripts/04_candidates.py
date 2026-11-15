# phase 3a: build the top-k candidate pool and the stratified labeling queue
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from gwcache import candidates, config, schema, storage


# finds causal neighbours for every turn and orders turns for labeling
def main():
    turns = storage.load("turns")
    vecs = np.load(config.path("work") / "vecs.npy")
    cands = candidates.build(turns, vecs)
    schema.validate(cands, "candidates")
    storage.save(cands, "candidates")
    q = candidates.queue(candidates.strata(turns, cands))
    storage.save(q, "label_queue")
    summary = q.groupby(["period", "sim_bin"]).size().unstack(fill_value=0)
    summary["total"] = summary.sum(axis=1)
    storage.save_result(summary.reset_index(), "candidate_strata")
    print(f"{len(cands)} candidate rows for {q['turn_id'].nunique()} of {len(turns)} turns")
    print(summary.to_string())


if __name__ == "__main__":
    main()
