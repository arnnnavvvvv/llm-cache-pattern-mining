# stateful gateway replay: each policy keeps its own cache, and answers served from cache never enter it
import numpy as np
import pandas as pd


# candidate positions and policy scores as dense (turns x k) arrays, -1 / -inf where empty
def to_matrices(pairs: pd.DataFrame, scores: np.ndarray, n_turns: int, k: int) -> tuple[np.ndarray, np.ndarray]:
    cand = np.full((n_turns, k), -1, dtype=np.int64)
    score = np.full((n_turns, k), -np.inf)
    r = pairs["rank"].to_numpy() - 1
    cand[pairs["pos"].to_numpy(), r] = pairs["cand_pos"].to_numpy()
    score[pairs["pos"].to_numpy(), r] = scores
    return cand, score


# replays all turns in time order for each threshold; returns served flags and chosen candidate per turn
def run(cand: np.ndarray, score: np.ndarray, thresholds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(cand)
    served = np.zeros((len(thresholds), n), dtype=bool)
    chosen = np.full((len(thresholds), n), -1, dtype=np.int64)
    best = np.where(cand >= 0, score, -np.inf).max(axis=1)
    for ti, th in enumerate(thresholds):
        # only turns with some candidate at or above the threshold can ever be served at it
        live = np.flatnonzero(best >= th)
        in_cache = np.ones(n, dtype=bool)
        for i in live:
            ok = (cand[i] >= 0) & in_cache[np.maximum(cand[i], 0)]
            s = np.where(ok, score[i], -np.inf)
            j = int(np.argmax(s))
            if s[j] >= th:
                served[ti, i], chosen[ti, i] = True, cand[i, j]
                in_cache[i] = False
    return served, chosen


# threshold grid over each turn's best score: dense in the top 30% where strict wrong-reuse levels are read,
# coarser below, plus one threshold that serves nothing
def threshold_grid(score: np.ndarray, rows: np.ndarray, n_top: int = 300, n_rest: int = 60) -> np.ndarray:
    best = score[rows].max(axis=1)
    best = best[np.isfinite(best)]
    if not len(best):
        return np.array([np.inf])
    grid = np.r_[np.quantile(best, np.linspace(0.7, 1, n_top)), np.quantile(best, np.linspace(0, 0.7, n_rest))]
    return np.r_[np.unique(grid), np.inf]
