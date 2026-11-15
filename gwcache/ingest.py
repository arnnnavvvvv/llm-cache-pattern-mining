# streams wildchat into a turn table (request + real answer) and splits sessions by time
import pandas as pd

from gwcache import config


# keeps english, non-toxic, multi-turn conversations and flattens them into one row per user turn
def stream_turns(target: int) -> list[dict]:
    from datasets import load_dataset

    cfg = config.load()["ingest"]
    stream = load_dataset(cfg["dataset"], split="train", streaming=True)
    rows = []
    for convo in stream:
        if convo["turn"] < cfg["min_turns"] or convo["language"] != cfg["language"] or convo.get("toxic"):
            continue
        msgs = convo["conversation"]
        turn_index = 0
        for i, msg in enumerate(msgs):
            if msg["role"] != "user" or not (msg["content"] or "").strip():
                continue
            reply = msgs[i + 1] if i + 1 < len(msgs) and msgs[i + 1]["role"] == "assistant" else None
            # wildchat only timestamps assistant replies, so the user turn borrows its reply's time
            ts = reply.get("timestamp") if reply and reply.get("timestamp") else convo["timestamp"]
            rows.append({
                "turn_id": f"{convo['conversation_hash']}-{turn_index}",
                "session_id": convo["conversation_hash"],
                "user_id": convo.get("hashed_ip") or convo["conversation_hash"],
                "turn_index": turn_index,
                "timestamp": ts,
                "request": msg["content"].strip(),
                "answer": ((reply or {}).get("content") or "").strip(),
            })
            turn_index += 1
        if len(rows) >= target:
            break
    return rows


# assigns each session to train/dev/confirm by its first turn's time, cutting at turn-count shares
def split_by_time(turns: pd.DataFrame, shares: dict) -> pd.DataFrame:
    first = turns.groupby("session_id").agg(start=("timestamp", "min"), n=("turn_id", "size")).sort_values("start")
    cum = first["n"].cumsum() / first["n"].sum()
    cut_train, cut_dev = shares["train"], shares["train"] + shares["dev"]
    first["period"] = "confirm"
    first.loc[cum <= cut_dev, "period"] = "dev"
    first.loc[cum <= cut_train, "period"] = "train"
    return turns.merge(first[["period"]], left_on="session_id", right_index=True)


# end-to-end phase 1: stream, clean types, split, return the turn table
def build_turns() -> pd.DataFrame:
    cfg = config.load()["ingest"]
    turns = pd.DataFrame(stream_turns(cfg["target_queries"]))
    turns["timestamp"] = pd.to_datetime(turns["timestamp"], utc=True)
    turns = turns[turns["answer"].str.len() > 0].reset_index(drop=True)
    turns = split_by_time(turns, cfg["split"])
    return turns.sort_values(["timestamp", "session_id", "turn_index"]).reset_index(drop=True)


# summary numbers per period for the dataset table in the report
def describe(turns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, g in [("all", turns)] + list(turns.groupby("period")):
        rows.append({
            "period": period, "turns": len(g), "sessions": g["session_id"].nunique(), "users": g["user_id"].nunique(),
            "start": g["timestamp"].min(), "end": g["timestamp"].max(),
            "turns_per_session": len(g) / g["session_id"].nunique(),
            "users_with_2plus_sessions": int((g.groupby("user_id")["session_id"].nunique() >= 2).sum()),
        })
    return pd.DataFrame(rows)
