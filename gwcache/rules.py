# behavioral association rules: p(reuse acceptable | request state and act, cache-entry state and act), mined from training labels
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

KEY = ["pat_state_q", "act", "pat_state_c", "cand_act"]
SMOOTHING = 20  # pseudo-count pulling rare rules toward the global acceptance rate


# one string per pair naming the rule it falls under
def rule_key(df: pd.DataFrame) -> pd.Series:
    return df[KEY].astype(str).agg("|".join, axis=1)


# smoothed acceptance rate for every rule seen in the given labeled rows
def mine_rules(labeled: pd.DataFrame) -> tuple[pd.Series, float]:
    g = labeled["acceptable"].mean()
    stats = labeled.assign(rule=rule_key(labeled)).groupby("rule")["acceptable"].agg(["sum", "count"])
    return (stats["sum"] + SMOOTHING * g) / (stats["count"] + SMOOTHING), g


# rule prior for every pair from the training labels, and out-of-fold priors for the training rows themselves
def add_prior(train: pd.DataFrame, pairs: pd.DataFrame, n_folds: int = 5, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    table, g = mine_rules(train)
    pairs = pairs.assign(pat_rule_prior=rule_key(pairs).map(table).fillna(g).to_numpy())
    train = train.reset_index(drop=True).copy()
    train["pat_rule_prior"] = g
    sessions = train["turn_id"].str.rsplit("-", n=1).str[0]
    for tr, te in GroupKFold(n_splits=n_folds, shuffle=True, random_state=seed).split(train, groups=sessions):
        t, gg = mine_rules(train.iloc[tr])
        train.loc[te, "pat_rule_prior"] = rule_key(train.iloc[te]).map(t).fillna(gg).to_numpy()
    return train, pairs


# the strongest rules, for the report
def top_rules(labeled: pd.DataFrame, min_count: int = 30) -> pd.DataFrame:
    stats = labeled.assign(rule=rule_key(labeled)).groupby("rule")["acceptable"].agg(["mean", "count"])
    stats = stats[stats["count"] >= min_count].sort_values("mean")
    parts = stats.index.to_series().str.split("|", expand=True)
    parts.columns = KEY
    return pd.concat([parts, stats.rename(columns={"mean": "acceptable_rate", "count": "pairs"})], axis=1).reset_index(drop=True)
