# checks cache-state handling in the replay engine and the weighted metrics
import numpy as np

from gwcache import metrics, replay, stats


# a turn served from cache never becomes a cache entry, so a later turn falls back to its next candidate
def test_served_turn_not_cached():
    cand = np.array([[-1, -1], [0, -1], [1, 0]])
    score = np.array([[-np.inf, -np.inf], [0.9, -np.inf], [0.95, 0.5]])
    served, chosen = replay.run(cand, score, np.array([0.4]))
    assert served[0].tolist() == [False, True, True]
    assert chosen[0, 2] == 0


# nothing is served at an infinite threshold
def test_infinite_threshold_serves_nothing():
    cand = np.array([[-1], [0]])
    served, _ = replay.run(cand, np.array([[-np.inf], [1.0]]), np.array([np.inf]))
    assert not served.any()


# hit rate uses the whole period as denominator and wrong-reuse only the served ones
def test_curve_and_hit_at():
    s = np.array([[True, True, False, False], [True, False, False, False]])
    wrong = np.array([[False, True, False, False], [False, False, False, False]])
    w = np.ones(4)
    c = metrics.curve(s, wrong, w, n_total=10)
    assert np.allclose(c["hit_rate"], [0.2, 0.1]) and np.allclose(c["wrong_reuse"], [0.5, 0.0])
    assert metrics.hit_at(s, wrong, w, 10, 0.1) == 0.1


# holm rejects in step-down order and stops at the first failure
def test_holm():
    assert stats.holm([0.01, 0.04], 0.05) == [True, True]
    assert stats.holm([0.03, 0.04], 0.05) == [False, False]
