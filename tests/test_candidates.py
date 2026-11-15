# checks that neighbour search is causal, the queue is stratified, and the power maths behaves
import numpy as np
import pandas as pd

from gwcache import candidates, embed, power


# a turn can only ever be matched to turns that came before it
def test_causal_top_k_only_looks_back():
    rng = np.random.default_rng(0)
    vecs = embed.normalize(rng.normal(size=(50, 8)).astype(np.float32))
    _, ids = embed.causal_top_k(vecs, 3)
    for i in range(50):
        assert all(j < i for j in ids[i] if j >= 0)
    assert (ids[0] == -1).all()


# an exact duplicate shows up as the top candidate with similarity 1
def test_duplicate_is_found():
    vecs = embed.normalize(np.array([[1, 0], [0, 1], [1, 0]], dtype=np.float32))
    sims, ids = embed.causal_top_k(vecs, 2)
    assert ids[2, 0] == 0 and abs(sims[2, 0] - 1) < 1e-6


# the first half of the queue holds roughly half of every stratum
def test_queue_prefix_is_stratified():
    st = pd.DataFrame({"turn_id": [f"t{i}" for i in range(400)], "period": ["train"] * 200 + ["confirm"] * 200,
                       "session_id": [f"s{i}" for i in range(400)], "sim": 0.9, "sim_bin": [0, 1] * 200})
    q = candidates.queue(st)
    half = q.head(200).groupby(["period", "sim_bin"]).size()
    assert half.between(35, 65).all()


# more labels shrink the detectable effect, and the two formulas agree
def test_power_round_trip():
    n = power.n_required(0.3, 0.02)
    assert abs(power.min_detectable(0.3, n) - 0.02) < 0.001
    assert power.min_detectable(0.3, 4000) < power.min_detectable(0.3, 1000)
