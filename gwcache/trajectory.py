# trajectory caching: store successful multi-turn sessions and fast-track new sessions to their final answer
import numpy as np
import pandas as pd

from gwcache import config
from gwcache.acts import head_tail
from gwcache.llm import Client

TRAJ_PROMPT = """You evaluate a gateway that tries to skip ahead in a conversation. Each item shows a user's FIRST \
request and the LATER request they ended on, with the FINAL answer they eventually accepted (the reference). It also \
shows a STORED answer that another user ended up accepting after a similar first request.

Decide whether serving the STORED answer right after the FIRST request would have given this user what they \
eventually needed, as well as the reference did. Different specifics, materials or goals mean false.
Long texts are shortened with [...]. Reply with JSON only: {"items": [{"id": <item id>, "acceptable": true|false}]}"""


# satisfaction proxy per session: long enough, and no correction among the last two turns
def satisfied_sessions(turns: pd.DataFrame) -> pd.DataFrame:
    min_turns = config.load()["trajectory"]["min_session_turns"]
    g = turns.sort_values("turn_index").groupby("session_id")
    s = pd.DataFrame({"n_turns": g.size(), "last_acts": g["act"].apply(lambda a: list(a)[-2:]),
                      "period": g["period"].first(), "first_turn": g["turn_id"].first(), "last_turn": g["turn_id"].last()})
    s["satisfied"] = (s["n_turns"] >= min_turns) & ~s["last_acts"].map(lambda a: "correction" in a)
    return s


# for each eligible eval session, the best-matching stored trajectory from strictly earlier successful sessions
def match(turns: pd.DataFrame, vecs: np.ndarray, sessions: pd.DataFrame, store_periods: list[str], eval_period: str) -> pd.DataFrame:
    pos = pd.Series(np.arange(len(turns)), index=turns["turn_id"])
    t = turns.set_index("turn_id")
    store = sessions[sessions["satisfied"] & sessions["period"].isin(store_periods)]
    evals = sessions[sessions["satisfied"] & (sessions["period"] == eval_period)]
    sv = vecs[pos.loc[store["first_turn"]].to_numpy()]
    s_start = t.loc[store["first_turn"], "timestamp"].to_numpy()
    s_intent = t.loc[store["first_turn"], "intent"].to_numpy()
    rows = []
    for sid, e in evals.iterrows():
        q = vecs[pos.at[e["first_turn"]]]
        ok = (s_start < t.at[e["first_turn"], "timestamp"]) & (s_intent == t.at[e["first_turn"], "intent"])
        if not ok.any():
            continue
        sims = np.where(ok, sv @ q, -1)
        j = int(np.argmax(sims))
        rows.append({"session_id": sid, "first_turn": e["first_turn"], "last_turn": e["last_turn"], "n_turns": e["n_turns"],
                     "stored_session": store.index[j], "stored_last_turn": store["last_turn"].iloc[j], "match_sim": float(sims[j])})
    return pd.DataFrame(rows)


# judges whether each fast-track would have served the user's eventual need
def judge(matches: pd.DataFrame, turns: pd.DataFrame, model: str, log=print) -> pd.DataFrame:
    j = config.load()["judge"]
    t = turns.set_index("turn_id")
    client = Client()
    out = []
    for start in range(0, len(matches), 4):
        batch = matches.iloc[start : start + 4]
        text = "\n\n".join(
            f"### Item {i}\nFIRST request:\n{head_tail(t.at[r.first_turn, 'request'], j['request_chars'])}\n\n"
            f"LATER request:\n{head_tail(t.at[r.last_turn, 'request'], j['request_chars'])}\n\n"
            f"FINAL answer (reference):\n{head_tail(t.at[r.last_turn, 'answer'], j['answer_chars'])}\n\n"
            f"STORED answer:\n{head_tail(t.at[r.stored_last_turn, 'answer'], j['answer_chars'])}"
            for i, r in enumerate(batch.itertuples(), start=1))
        reply = client.json_call(model, TRAJ_PROMPT, text, log=log)
        got = {int(x["id"]): bool(x["acceptable"]) for x in reply.get("items", []) if "acceptable" in x}
        out += [{"session_id": r.session_id, "acceptable": got.get(i)} for i, r in enumerate(batch.itertuples(), start=1)]
        log(f"trajectory judge: {min(start + 4, len(matches))}/{len(matches)}")
    return matches.merge(pd.DataFrame(out).dropna(), on="session_id")


# turns saved vs false fast-track rate as the match-similarity threshold moves, with the oracle for reference
def turns_saved_curve(judged: pd.DataFrame, n_eligible: int) -> pd.DataFrame:
    rows = []
    for th in np.unique(np.r_[judged["match_sim"].to_numpy(), np.inf]):
        fired = judged[judged["match_sim"] >= th]
        good = fired[fired["acceptable"].astype(bool)]
        rows.append({"threshold": th, "fired": len(fired),
                     "false_fast_track_rate": 1 - len(good) / len(fired) if len(fired) else 0.0,
                     "turns_saved_per_session": (good["n_turns"] - 1).sum() / n_eligible})
    return pd.DataFrame(rows)


# blind sheet for checking the satisfaction proxy against human judgement
def human_sheet(turns: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    cfg = config.load()
    pick = sessions[sessions["n_turns"] >= cfg["trajectory"]["min_session_turns"]].sample(
        n=cfg["trajectory"]["human_check_size"], random_state=cfg["seed"])
    t = turns.sort_values("turn_index")
    convo = t.groupby("session_id").apply(
        lambda g: "\n---\n".join(f"USER: {head_tail(r, 200)}\nASSISTANT: {head_tail(a, 200)}" for r, a in zip(g["request"], g["answer"])),
        include_groups=False)
    return pd.DataFrame({"session_id": pick.index, "conversation": convo.loc[pick.index].to_numpy(), "user_satisfied_YES_NO": ""})
