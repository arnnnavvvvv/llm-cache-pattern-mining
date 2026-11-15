# behavioral pattern miner: daily fp-growth and prefixspan over past traffic, and causal pattern features
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import fpgrowth
from mlxtend.preprocessing import TransactionEncoder
from prefixspan import PrefixSpan

from gwcache import config

DEPENDENT_ACTS = {"follow_up", "continuation", "correction", "new_ask_same_material"}
SESSION_SEQ = ["pat_act_conf", "pat_dep_prior", "pat_intent_conf", "pat_cand_intent_conf", "pat_cand_dep_prior"]
SESSION_FREQ = ["pat_freq_support", "pat_freq_matches"]
USER_SEQ = ["pat_user_intent_conf", "pat_user_cand_conf"]
# numeric state features; the raw state strings only feed the association-rule prior
STATE = ["pat_same_state", "pat_cand_act_conf"]
RULES = ["pat_rule_prior"]
ALL = SESSION_SEQ + SESSION_FREQ + USER_SEQ + STATE + RULES


# counts of every frequent subsequence (length 1..max_len) as a dict keyed by tuple
def mine_sequences(seqs: list[list], min_support: float, max_len: int) -> dict:
    seqs = [s for s in seqs if s]
    if not seqs:
        return {}
    ps = PrefixSpan(seqs)
    ps.minlen, ps.maxlen = 1, max_len
    return {tuple(p): c for c, p in ps.frequent(max(2, int(min_support * len(seqs))))}


# frequent itemsets (size 2+) with their support, as a dict keyed by frozenset
def mine_itemsets(sets: list[set], min_support: float) -> dict:
    sets = [sorted(s) for s in sets if len(s) > 1]
    if len(sets) < 10:
        return {}
    enc = TransactionEncoder()
    onehot = pd.DataFrame(enc.fit(sets).transform(sets), columns=enc.columns_)
    found = fpgrowth(onehot, min_support=min_support, use_colnames=True, max_len=3)
    found = found[found["itemsets"].map(len) > 1]
    return dict(zip(found["itemsets"].map(frozenset), found["support"]))


# confidence that `nxt` follows the history, using the longest suffix (up to 2 tokens) the miner saw
def confidence(counts: dict, history: list, nxt) -> float:
    for k in (2, 1):
        prefix = tuple(history[-k:])
        if len(prefix) == k and prefix in counts:
            return counts.get(prefix + (nxt,), 0) / counts[prefix]
    return 0.0


# token sequences per session (acts, intents, intent:act) and per user (intents across sessions), in time order
def entity_sequences(turns: pd.DataFrame) -> dict:
    t = turns.sort_values(["timestamp", "session_id", "turn_index"])
    return {
        "session_acts": t.groupby("session_id")["act"].apply(list),
        "session_intents": t.groupby("session_id")["intent"].apply(list),
        "session_tokens": t.groupby("session_id").apply(lambda g: set(g["intent"].astype(str) + ":" + g["act"]), include_groups=False),
        "user_intents": t.groupby("user_id")["intent"].apply(list),
    }


# mines all pattern tables from the turns strictly before `cutoff`
def mine_before(turns: pd.DataFrame, cutoff: pd.Timestamp) -> dict:
    p = config.load()["patterns"]
    past = turns[turns["timestamp"] < cutoff]
    if past.empty:
        return {"acts": {}, "intents": {}, "itemsets": {}, "user_intents": {}, "n_sessions": 0}
    seqs = entity_sequences(past)
    return {
        "acts": mine_sequences(seqs["session_acts"].tolist(), p["seq_min_support"], p["seq_max_len"]),
        "intents": mine_sequences(seqs["session_intents"].tolist(), p["seq_min_support"], p["seq_max_len"]),
        "itemsets": mine_itemsets(seqs["session_tokens"].tolist(), p["freq_min_support"]),
        "user_intents": mine_sequences(seqs["user_intents"].tolist(), p["seq_min_support"], p["seq_max_len"]),
        "n_sessions": past["session_id"].nunique(),
    }


# behavioral state of a turn: the longest suffix of its act history that the miner found frequent
def state(act_counts: dict, history: list) -> str:
    if not history:
        return "start"
    for k in (2, 1):
        suffix = tuple(history[-k:])
        if len(suffix) == k and suffix in act_counts:
            return ">".join(suffix)
    return "rare"


# prior that the next act is context-dependent, given the act history
def dependent_prior(act_counts: dict, history: list) -> float:
    return sum(confidence(act_counts, history, a) for a in DEPENDENT_ACTS)


# per-turn history views; the placebo modes scramble them while leaving the mined patterns untouched
def histories(turns: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = turns.sort_values(["session_id", "turn_index"]).copy()
    if mode == "shuffled":
        t["order"] = t.groupby("session_id")["turn_index"].transform(lambda s: rng.permutation(len(s)))
    else:
        t["order"] = t["turn_index"]
    t = t.sort_values(["session_id", "order"])
    acts = t.groupby("session_id")["act"].apply(list)
    intents = t.groupby("session_id")["intent"].apply(list)
    if mode == "borrowed":
        donors = rng.permutation(acts.index.to_numpy())
        acts = pd.Series(acts.loc[donors].to_numpy(), index=acts.index)
        intents = pd.Series(intents.loc[donors].to_numpy(), index=intents.index)
    rank = t.groupby("session_id").cumcount()
    hist = pd.DataFrame({"turn_id": t["turn_id"].to_numpy(), "session_id": t["session_id"].to_numpy(), "k": rank.to_numpy()})
    hist["prev_acts"] = [acts[s][:k] for s, k in zip(hist["session_id"], hist["k"])]
    hist["prev_intents"] = [intents[s][:k] for s, k in zip(hist["session_id"], hist["k"])]
    return hist.set_index("turn_id")


# the user's intents from earlier sessions (strictly before this session started); placebos scramble or swap them
def user_histories(turns: pd.DataFrame, mode: str = "real", seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed + 1)
    starts = turns.groupby("session_id")["timestamp"].min()
    out = {}
    for _, g in turns.sort_values("timestamp").groupby("user_id"):
        sess_start = g["session_id"].map(starts).to_numpy()
        intents = g["intent"].to_numpy()
        for tid, st in zip(g["turn_id"], sess_start):
            h = intents[sess_start < st][-10:].tolist()
            out[tid] = rng.permutation(h).tolist() if mode == "shuffled" else h
    hist = pd.Series(out)
    if mode == "borrowed":
        hist = pd.Series(rng.permutation(hist.to_numpy()), index=hist.index)
    return hist


# mined pattern tables for every day in the data, each using only turns before that day
def mine_daily(turns: pd.DataFrame) -> dict:
    return {day: mine_before(turns, day) for day in sorted(turns["timestamp"].dt.floor("D").unique())}


# turn-level pattern features, each computed from the patterns mined before that turn's day
def turn_features(turns: pd.DataFrame, daily: dict, mode: str = "real", seed: int = 0) -> pd.DataFrame:
    hist = histories(turns, mode, seed)
    uhist = user_histories(turns, mode, seed)
    days = turns["timestamp"].dt.floor("D")
    rows = []
    for day, g in turns.groupby(days):
        mined = daily[day]
        for tid, intent, act in zip(g["turn_id"], g["intent"], g["act"]):
            h = hist.loc[tid]
            seen = {f"{i}:{a}" for i, a in zip(h["prev_intents"], h["prev_acts"])} | {f"{intent}:{act}"}
            freq = [s for items, s in mined["itemsets"].items() if items <= seen]
            rows.append({
                "turn_id": tid,
                "pat_act_conf": confidence(mined["acts"], h["prev_acts"], act),
                "pat_dep_prior": dependent_prior(mined["acts"], h["prev_acts"]),
                "pat_intent_conf": confidence(mined["intents"], h["prev_intents"], intent),
                "pat_freq_support": max(freq, default=0.0),
                "pat_freq_matches": len(freq),
                "pat_user_hist": uhist.get(tid, []),
                "_mined": day,
            })
    return pd.DataFrame(rows).set_index("turn_id")


# adds pattern features to the pair table, including the ones that depend on the candidate
def add_to_pairs(pairs: pd.DataFrame, turns: pd.DataFrame, tf: pd.DataFrame, daily: dict,
                 mode: str = "real", seed: int = 0) -> pd.DataFrame:
    p = pairs.copy()
    t = turns.set_index("turn_id")
    hist = histories(turns, mode, seed)
    for col in ["pat_act_conf", "pat_dep_prior", "pat_intent_conf", "pat_freq_support", "pat_freq_matches"]:
        p[col] = tf.loc[p["turn_id"], col].to_numpy()
    p["pat_cand_dep_prior"] = tf.loc[p["cand_turn_id"], "pat_dep_prior"].to_numpy()
    cand_conf, user_cur, user_cand, state_q, state_c, cand_act_conf = [], [], [], [], [], []
    for tid, cid in zip(p["turn_id"], p["cand_turn_id"]):
        mined = daily[tf.at[tid, "_mined"]]
        hq, hc = hist.at[tid, "prev_acts"], hist.at[cid, "prev_acts"]
        state_q.append(state(mined["acts"], hq))
        state_c.append(state(mined["acts"], hc))
        cand_act_conf.append(confidence(mined["acts"], hc, t.at[cid, "act"]))
        cand_intent = t.at[cid, "intent"]
        cand_conf.append(confidence(mined["intents"], hist.at[tid, "prev_intents"], cand_intent))
        uh = tf.at[tid, "pat_user_hist"]
        user_cur.append(confidence(mined["user_intents"], uh, t.at[tid, "intent"]))
        user_cand.append(confidence(mined["user_intents"], uh, cand_intent))
    p["pat_cand_intent_conf"], p["pat_user_intent_conf"], p["pat_user_cand_conf"] = cand_conf, user_cur, user_cand
    p["pat_state_q"], p["pat_state_c"], p["pat_cand_act_conf"] = state_q, state_c, cand_act_conf
    p["pat_same_state"] = (p["pat_state_q"] == p["pat_state_c"]).astype(int)
    return p


# size of each day's mined pattern tables, for the report
def mining_summary(daily: dict) -> pd.DataFrame:
    rows = []
    for day, m in daily.items():
        rows.append({"day": day, "sessions_mined": m["n_sessions"], "act_seqs": len(m["acts"]),
                     "intent_seqs": len(m["intents"]), "itemsets": len(m["itemsets"]), "user_seqs": len(m["user_intents"])})
    return pd.DataFrame(rows)
