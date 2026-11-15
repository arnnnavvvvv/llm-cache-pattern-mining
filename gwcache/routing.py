# routing between a strong and a weak model, using human votes as the quality signal
import json

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold

from gwcache import acts, config, embed, patterns


# parses a json list field from the arena dump, tolerating plain strings
def _as_list(raw) -> list[str]:
    try:
        out = json.loads(raw)
        return [x or "" for x in out] if isinstance(out, list) else [str(raw)]
    except (TypeError, ValueError):
        return [str(raw)]


# strong-vs-weak multi-turn conversations with the label "weak model was at least as good"
def load_conversations() -> pd.DataFrame:
    from datasets import load_dataset

    cfg = config.load()["routing"]
    raw = load_dataset(cfg["dataset"], split="train").to_pandas()
    strong = raw["model_a"].str.contains(cfg["strong_models"]), raw["model_b"].str.contains(cfg["strong_models"])
    weak = raw["model_a"].str.contains(cfg["weak_models"]), raw["model_b"].str.contains(cfg["weak_models"])
    a_strong = strong[0] & weak[1]
    b_strong = strong[1] & weak[0]
    df = raw[a_strong | b_strong].copy()
    df["weak_side"] = np.where(a_strong[df.index], "b", "a")
    won = {"a": df["winner_model_a"].astype(int), "b": df["winner_model_b"].astype(int)}
    df["weak_ok"] = ((df["weak_side"] == "a") & (won["a"] == 1) | (df["weak_side"] == "b") & (won["b"] == 1)
                     | (df["winner_tie"].astype(int) == 1)).astype(int)
    df["prompts"] = df["prompt"].map(_as_list)
    df = df[df["prompts"].map(len) >= cfg["min_turns"]]
    return df[["id", "model_a", "model_b", "weak_side", "weak_ok", "prompts"]].reset_index(drop=True)


# one row per prompt turn, so the wildchat act tagger and intent centroids can be applied
def explode_turns(conv: pd.DataFrame) -> pd.DataFrame:
    rows = [{"turn_id": f"{cid}-{k}", "session_id": str(cid), "turn_index": k, "request": text}
            for cid, prompts in zip(conv["id"], conv["prompts"]) for k, text in enumerate(prompts)]
    return pd.DataFrame(rows)


# embeddings, intents (nearest wildchat centroid) and acts (wildchat-trained tagger) for every prompt turn
def annotate(turns: pd.DataFrame, centers: np.ndarray, act_model) -> tuple[pd.DataFrame, np.ndarray]:
    vecs = embed.encode(turns["request"].tolist())
    turns["intent"] = np.argmax(vecs @ embed.normalize(centers.astype(np.float32)).T, axis=1)
    prev = acts.previous_requests(turns)
    turns["act"] = act_model.predict(acts.features(turns, vecs, prev))
    return turns, vecs


# per-conversation features at the last turn: per-query, context, and pattern features from training-only mining
def conversation_features(conv: pd.DataFrame, turns: pd.DataFrame, vecs: np.ndarray, train_ids: set, pca: PCA) -> pd.DataFrame:
    p = config.load()["patterns"]
    t = turns.assign(pos=np.arange(len(turns)))
    train_turns = t[t["session_id"].isin(train_ids)]
    act_counts = patterns.mine_sequences(train_turns.groupby("session_id")["act"].apply(list).tolist(), p["seq_min_support"], p["seq_max_len"])
    intent_counts = patterns.mine_sequences(train_turns.groupby("session_id")["intent"].apply(list).tolist(), p["seq_min_support"], p["seq_max_len"])
    rows = []
    for cid, g in t.groupby("session_id", sort=False):
        g = g.sort_values("turn_index")
        last, hist = g.iloc[-1], g.iloc[:-1]
        ctx = embed.normalize(vecs[hist["pos"]].mean(axis=0, keepdims=True))[0]
        row = {"id": cid, "n_turns": len(g), "last_len": np.log1p(len(last["request"])), "intent": int(last["intent"]),
               "act": last["act"], "ctx_sim": float(vecs[last["pos"]] @ ctx), "ctx_spread": float(np.linalg.norm(vecs[hist["pos"]].std(axis=0))),
               "pat_act_conf": patterns.confidence(act_counts, hist["act"].tolist(), last["act"]),
               "pat_dep_prior": patterns.dependent_prior(act_counts, hist["act"].tolist()),
               "pat_intent_conf": patterns.confidence(intent_counts, hist["intent"].tolist(), last["intent"]),
               "pat_intent_stay": patterns.confidence(intent_counts, hist["intent"].tolist(), hist["intent"].iloc[-1])}
        row.update({f"emb_{i}": v for i, v in enumerate(pca.transform(vecs[[last["pos"]]])[0])})
        rows.append(row)
    f = pd.DataFrame(rows)
    f["intent"], f["act"] = f["intent"].astype("category"), f["act"].astype("category")
    return conv.assign(id=conv["id"].astype(str)).merge(f, on="id")


# feature columns for each router
def router_sets(n_emb: int) -> dict:
    per_query = ["n_turns", "last_len", "intent", "act"] + [f"emb_{i}" for i in range(n_emb)]
    return {"per_query": per_query, "context": per_query + ["ctx_sim", "ctx_spread"],
            "patterns": per_query + ["pat_act_conf", "pat_dep_prior", "pat_intent_conf", "pat_intent_stay"]}


# out-of-fold p(weak is fine) for each router, conversation-grouped k-fold over several shuffles, mining per fold
def oof_scores(conv: pd.DataFrame, turns: pd.DataFrame, vecs: np.ndarray, n_emb: int = 16) -> tuple[dict, pd.DataFrame]:
    cfg = config.load()
    ids = conv["id"].astype(str).to_numpy()
    scores = {name: np.zeros((cfg["eval"]["n_shuffles"], len(conv))) for name in router_sets(n_emb)}
    last_pos = turns.assign(pos=np.arange(len(turns))).groupby("session_id")["pos"].max()
    folds_log = []
    for rep in range(cfg["eval"]["n_shuffles"]):
        for fold, (tr, te) in enumerate(GroupKFold(cfg["eval"]["n_folds"], shuffle=True, random_state=cfg["seed"] + rep).split(conv, groups=ids)):
            pca = PCA(n_emb, random_state=cfg["seed"]).fit(vecs[last_pos.loc[ids[tr]].to_numpy()])
            feats = conversation_features(conv, turns, vecs, set(ids[tr]), pca).set_index("id").loc[ids]
            for name, cols in router_sets(n_emb).items():
                model = LGBMClassifier(random_state=cfg["seed"] + rep, **cfg["lgbm"]).fit(feats.iloc[tr][cols], conv["weak_ok"].iloc[tr])
                scores[name][rep, te] = model.predict_proba(feats.iloc[te][cols])[:, 1]
            folds_log.append({"shuffle": rep, "fold": fold, "train": len(tr), "test": len(te)})
    return {k: v.mean(axis=0) for k, v in scores.items()}, pd.DataFrame(folds_log)


# quality (share of conversations where the routed answer is no worse than the strong one) vs share sent to strong
def quality_curve(p_weak_ok: np.ndarray, weak_ok: np.ndarray) -> pd.DataFrame:
    order = np.argsort(-p_weak_ok)
    to_weak = np.arange(0, len(order) + 1)
    weak_good = np.r_[0, np.cumsum(weak_ok[order])]
    quality = (len(order) - to_weak + weak_good) / len(order)
    return pd.DataFrame({"strong_share": 1 - to_weak / len(order), "quality": quality})


# best quality with the strong-model share at or under the cap
def quality_at(p: np.ndarray, y: np.ndarray, cap: float) -> float:
    c = quality_curve(p, y)
    return float(c.loc[c["strong_share"] <= cap + 1e-12, "quality"].max())
