# session bootstrap for paired policy differences and holm correction
import numpy as np

from gwcache import metrics


# resampled session index sets, reused for every policy so differences stay paired
def session_draws(sessions: np.ndarray, n_boot: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(sessions, return_inverse=True)
    members = [np.flatnonzero(inv == u) for u in range(len(uniq))]
    return [np.concatenate([members[u] for u in rng.integers(0, len(uniq), len(uniq))]) for _ in range(n_boot)]


# bootstrap distribution of hit-at-level for one policy's outcomes
def boot_hits(s: np.ndarray, wrong: np.ndarray, w: np.ndarray, n_total: int, level: float, draws: list) -> np.ndarray:
    return np.array([metrics.hit_at(s[:, d], wrong[:, d], w[d], n_total, level) for d in draws])


# two-sided bootstrap p-value that a paired difference is zero
def p_value(diff: np.ndarray) -> float:
    return float(min(1.0, 2 * min((diff <= 0).mean(), (diff >= 0).mean())))


# holm step-down: which hypotheses are rejected at family level alpha
def holm(pvals: list[float], alpha: float) -> list[bool]:
    order = np.argsort(pvals)
    reject = [False] * len(pvals)
    for step, idx in enumerate(order):
        if pvals[idx] <= alpha / (len(pvals) - step):
            reject[idx] = True
        else:
            break
    return reject
