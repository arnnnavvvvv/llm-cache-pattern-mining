# the admission decision engine: expected benefit of serving each cached candidate
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression

from gwcache import config


# probability-of-staying-valid multiplier that halves every configured half-life
def staleness(gap_days: np.ndarray) -> np.ndarray:
    half = config.load()["decision"]["staleness_half_life_days"]
    return np.power(0.5, np.asarray(gap_days, dtype=float) / half)


# expected benefit of reuse: value of a good reuse minus cost of a wrong one, given p(acceptable)
def expected_benefit(p_valid: np.ndarray, gap_days: np.ndarray) -> np.ndarray:
    d = config.load()["decision"]
    q = np.clip(p_valid, 0, 1) * staleness(gap_days)
    return d["reuse_utility"] * q - d["wrong_reuse_cost"] * (1 - q)


# p1: the raw cosine similarity of each candidate
def score_fixed(pairs: pd.DataFrame) -> np.ndarray:
    return pairs["sim"].to_numpy(dtype=float)


# p2: per-intent calibration of similarity into p(acceptable), fit on training labels (global fit for sparse intents)
def score_per_intent(pairs: pd.DataFrame, train: pd.DataFrame, min_rows: int = 40) -> np.ndarray:
    glob = LogisticRegression().fit(train[["sim"]], train["acceptable"])
    out = glob.predict_proba(pairs[["sim"]])[:, 1]
    for intent, g in train.groupby("intent", observed=True):
        if len(g) >= min_rows and g["acceptable"].nunique() == 2:
            m = LogisticRegression().fit(g[["sim"]], g["acceptable"])
            mask = (pairs["intent"] == intent).to_numpy()
            if mask.any():
                out[mask] = m.predict_proba(pairs.loc[mask, ["sim"]])[:, 1]
    return out


# fits the learned verifier on labeled training pairs with the given feature columns
def fit_verifier(train: pd.DataFrame, cols: list[str], seed: int | None = None) -> LGBMClassifier:
    cfg = config.load()
    model = LGBMClassifier(random_state=cfg["seed"] if seed is None else seed, **cfg["lgbm"])
    return model.fit(train[cols], train["acceptable"])


# learned policy score: expected benefit using the verifier's p(acceptable) and staleness
def score_learned(model: LGBMClassifier, pairs: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return expected_benefit(model.predict_proba(pairs[cols])[:, 1], pairs["gap_days"].to_numpy())
