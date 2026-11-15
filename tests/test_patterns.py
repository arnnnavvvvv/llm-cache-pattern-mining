# leakage checks for the pattern miner: nothing from the future may reach a turn's features
import numpy as np
import pandas as pd

from gwcache import patterns

ACTS = ["new_request", "follow_up", "continuation", "correction"]


# small multi-day, multi-user traffic with repeated session shapes so patterns exist
def synthetic_turns(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(120):
        day = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=s // 30)
        for k in range(rng.integers(2, 5)):
            rows.append({"turn_id": f"s{s}-{k}", "session_id": f"s{s}", "user_id": f"u{s % 15}", "turn_index": k,
                         "timestamp": day + pd.Timedelta(minutes=10 * k + s), "intent": int(rng.integers(0, 3)),
                         "act": ACTS[0] if k == 0 else ACTS[int(rng.integers(1, 4))]})
    return pd.DataFrame(rows)


# mining at a cutoff ignores every turn at or after the cutoff
def test_mine_before_ignores_future():
    turns = synthetic_turns()
    cutoff = pd.Timestamp("2024-01-03", tz="UTC")
    a = patterns.mine_before(turns, cutoff)
    future = turns["timestamp"] >= cutoff
    changed = turns.copy()
    changed.loc[future, "act"] = "correction"
    changed.loc[future, "intent"] = 2
    b = patterns.mine_before(changed, cutoff)
    assert a["acts"] == b["acts"] and a["intents"] == b["intents"] and a["itemsets"] == b["itemsets"]


# rewriting the last day's traffic leaves every earlier turn's pattern features unchanged
def test_turn_features_are_causal():
    turns = synthetic_turns()
    last_day = turns["timestamp"].dt.floor("D").max()
    changed = turns.copy()
    late = changed["timestamp"].dt.floor("D") == last_day
    changed.loc[late, "act"] = "continuation"
    changed.loc[late, "intent"] = 1
    a = patterns.turn_features(turns, patterns.mine_daily(turns))
    b = patterns.turn_features(changed, patterns.mine_daily(changed))
    early = turns.loc[~late, "turn_id"]
    cols = ["pat_act_conf", "pat_dep_prior", "pat_intent_conf", "pat_freq_support", "pat_freq_matches"]
    pd.testing.assert_frame_equal(a.loc[early, cols], b.loc[early, cols])


# a user's history only contains intents from sessions that started earlier
def test_user_history_is_from_earlier_sessions():
    turns = synthetic_turns()
    hist = patterns.user_histories(turns)
    first_sessions = turns.sort_values("timestamp").groupby("user_id")["session_id"].first()
    for s in first_sessions:
        for tid in turns.loc[turns["session_id"] == s, "turn_id"]:
            assert hist[tid] == []


# confidence backs off from two-token to one-token history and returns 0 for unseen prefixes
def test_confidence_backoff():
    counts = {("a",): 10, ("a", "b"): 4, ("x", "a"): 5}
    assert patterns.confidence(counts, ["z", "a"], "b") == 0.4
    assert patterns.confidence(counts, ["q"], "b") == 0.0
