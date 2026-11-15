# dialogue-act tagger: llm seed labels on training turns, then a fast classifier for every turn
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold, cross_val_predict

from gwcache import config
from gwcache.llm import Client

ACT_PROMPT = """You label the dialogue act of user turns in chatbot conversations. For each item you see the user's \
PREVIOUS turn (may be empty) and the CURRENT turn. Pick exactly one act for the CURRENT turn:

- new_request: a self-contained new task or question that makes sense without the earlier conversation.
- follow_up: refines, extends or modifies the previous answer (shorter, longer, add X, change style, more examples).
- continuation: asks the assistant to keep going with the same output (continue, go on, next part).
- correction: says the previous answer was wrong or did not work, or asks to fix it.
- new_ask_same_material: a different task on material already given earlier (same pasted text or code, new instruction).

Texts may be shortened with [...]. Reply with JSON only: {"acts": [{"id": <item id>, "act": "<one label>"}, ...]}"""

# surface cues that are cheap to compute and carry a lot of the act signal
CUES = {
    "cue_continue": r"\b(continue|go on|keep going|next part|carry on)\b",
    "cue_refine": r"\b(shorter|longer|more|less|again|rewrite|rephrase|instead|also|add|change|make it)\b",
    "cue_correct": r"\b(wrong|error|incorrect|not work|doesn'?t work|fix|mistake|still)\b",
    "cue_deictic": r"\b(this|that|it|above|previous|these|those)\b",
}


# shortens long text to its first and last part
def head_tail(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit // 2] + " [...] " + text[-limit // 2 :]


# previous request in the same session for every turn (empty for first turns)
def previous_requests(turns: pd.DataFrame) -> pd.Series:
    ordered = turns.sort_values(["session_id", "turn_index"])
    prev = ordered.groupby("session_id")["request"].shift(1).fillna("")
    return prev.reindex(turns.index)


# asks the llm for act labels on a sample of training turns, in batches
def seed_labels(turns: pd.DataFrame, prev: pd.Series, log=print) -> pd.DataFrame:
    cfg = config.load()
    a = cfg["acts"]
    pool = turns[turns["period"] == "train"]
    sample = pool.sample(n=min(a["seed_size"], len(pool)), random_state=cfg["seed"])
    client = Client()
    out = []
    for start in range(0, len(sample), a["turns_per_request"]):
        batch = sample.iloc[start : start + a["turns_per_request"]]
        items = "\n\n".join(
            f"### Item {i}\nPREVIOUS: {head_tail(prev.loc[idx], 150)}\nCURRENT: {head_tail(row.request, 250)}"
            for i, (idx, row) in enumerate(batch.iterrows(), start=1)
        )
        reply = client.json_call(a["seed_model"], ACT_PROMPT, items, log=log)
        got = {int(x["id"]): x["act"] for x in reply.get("acts", []) if x.get("act") in a["labels"]}
        out += [{"turn_id": row.turn_id, "act": got.get(i)} for i, row in enumerate(batch.itertuples(), start=1)]
        log(f"act seeds: {len(out)}/{len(sample)}")
    return pd.DataFrame(out).dropna()


# tags every turn's act with the llm, batched and in parallel; turns the model skips come back as new_request
def tag_all(turns: pd.DataFrame, prev: pd.Series, model: str, log=print) -> pd.Series:
    from concurrent.futures import ThreadPoolExecutor

    cfg = config.load()
    per, labels = cfg["acts"]["turns_per_request"], cfg["acts"]["labels"]
    client = Client()
    idx = list(turns.index)
    batches = [idx[i : i + per] for i in range(0, len(idx), per)]

    # one request for one batch of turns
    def run(batch):
        text = "\n\n".join(f"### Item {k}\nPREVIOUS: {head_tail(prev.loc[j], 150)}\nCURRENT: {head_tail(turns.at[j, 'request'], 250)}"
                            for k, j in enumerate(batch, start=1))
        reply = client.json_call(model, ACT_PROMPT, text, log=log)
        got = {int(x["id"]): x["act"] for x in reply.get("acts", []) if x.get("act") in labels}
        return [got.get(k, "new_request") for k in range(1, len(batch) + 1)]

    with ThreadPoolExecutor(max_workers=cfg["gateway"]["workers"]) as pool:
        out = []
        for n, tags in enumerate(pool.map(run, batches), start=1):
            out += tags
            if n % 100 == 0:
                log(f"act tags: {n}/{len(batches)} batches, tokens so far {client.tokens}")
    return pd.Series(out, index=idx)


# numeric features for the classifier: request embedding, similarity to previous turn, position, length, cues
def features(turns: pd.DataFrame, vecs: np.ndarray, prev: pd.Series) -> np.ndarray:
    pos = pd.Series(np.arange(len(turns)), index=turns.index)
    ordered = turns.sort_values(["session_id", "turn_index"])
    prev_pos = ordered.assign(p=pos.loc[ordered.index]).groupby("session_id")["p"].shift(1).reindex(turns.index)
    sim_prev = np.array([float(vecs[i] @ vecs[int(j)]) if pd.notna(j) else 0.0 for i, j in enumerate(prev_pos)])
    text = turns["request"].str.lower()
    cue_cols = [text.str.slice(0, 300).str.contains(rx, regex=True).astype(float).to_numpy() for rx in CUES.values()]
    extra = np.column_stack([
        sim_prev, (turns["turn_index"] == 0).astype(float), np.log1p(turns["turn_index"]),
        np.log1p(turns["request"].str.len()), np.log1p(prev.str.len()), *cue_cols,
    ])
    return np.hstack([vecs, extra])


# trains the classifier on seed labels and reports cross-validated agreement with the llm labels
def train(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[LogisticRegression, float]:
    model = LogisticRegression(max_iter=3000, C=2.0, class_weight="balanced")
    pred = cross_val_predict(model, x, y, cv=GroupKFold(n_splits=5), groups=groups)
    model.fit(x, y)
    return model, f1_score(y, pred, average="macro")


# blind sheet for the human act check, sampled from training turns
def human_sheet(turns: pd.DataFrame, prev: pd.Series) -> pd.DataFrame:
    cfg = config.load()
    pick = turns[turns["period"] == "train"].sample(n=cfg["acts"]["human_check_size"], random_state=cfg["seed"] + 1)
    return pd.DataFrame({
        "turn_id": pick["turn_id"], "previous_turn": prev.loc[pick.index].map(lambda t: head_tail(t, 300)),
        "current_turn": pick["request"].map(lambda t: head_tail(t, 400)), "act": "",
    })


# macro f1 of the tagger against a filled human sheet
def score_human(sheet: pd.DataFrame, predicted: pd.Series) -> dict:
    sheet = sheet[sheet["act"].astype(str).str.strip().isin(config.load()["acts"]["labels"])]
    if sheet.empty:
        return {"n": 0, "macro_f1": None}
    pred = predicted.loc[sheet["turn_id"]].to_numpy()
    return {"n": len(sheet), "macro_f1": f1_score(sheet["act"].str.strip(), pred, average="macro"),
            "accuracy": float((sheet["act"].str.strip().to_numpy() == pred).mean())}

