# checks for the behavioral association-rule prior
import numpy as np
import pandas as pd

from gwcache import rules


# synthetic labeled pairs where one behavioral rule is always unsafe and the rest are always safe
def labeled(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"turn_id": [f"s{i // 4}-{i % 4}" for i in range(n)],
                       "pat_state_q": rng.choice(["start", "follow_up"], n), "act": rng.choice(["new_request", "follow_up"], n),
                       "pat_state_c": "start", "cand_act": "new_request"})
    df["acceptable"] = (~((df["pat_state_q"] == "follow_up") & (df["act"] == "follow_up"))).astype(int)
    return df


# the prior separates the unsafe rule from the safe ones, and unseen rules fall back to the global rate
def test_prior_separates_rules():
    train = labeled()
    new = pd.DataFrame({"pat_state_q": ["follow_up", "start", "x"], "act": ["follow_up", "new_request", "y"],
                        "pat_state_c": "start", "cand_act": "new_request"})
    _, scored = rules.add_prior(train, new)
    p = scored["pat_rule_prior"].to_numpy()
    assert p[0] < 0.2 and p[1] > 0.8 and abs(p[2] - train["acceptable"].mean()) < 1e-9


# training rows get out-of-fold priors, never computed from their own label
def test_training_prior_is_out_of_fold():
    train = labeled(40)
    train.loc[0, "acceptable"] = 1 - train.loc[0, "acceptable"]
    oof, _ = rules.add_prior(train, train.head(1))
    table, _ = rules.mine_rules(train)
    assert oof.loc[0, "pat_rule_prior"] != table[rules.rule_key(train.head(1)).iloc[0]]
