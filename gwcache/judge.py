# reference-based judge: would a candidate's cached answer serve the new request as well as the real answer did
import pandas as pd

from gwcache import config
from gwcache.acts import head_tail
from gwcache.llm import Client, call_splitting

JUDGE_PROMPT = """You audit a semantic cache in an LLM gateway. Each item has a NEW request, the REFERENCE answer \
that was actually given to it, and one or more CANDIDATES: earlier requests with the answers given to them.

For each candidate, decide whether returning that candidate's answer, unchanged, would have been an acceptable \
response to the NEW request. Use the REFERENCE to understand what the new request really needed.

Acceptable (true) only if the candidate answer does what the NEW request asks: same task, same input material, \
same specifics. Small wording differences are fine, and it does not need to match the reference word for word.
Not acceptable (false) if the NEW request asks for something different (a different operation on the same text, \
different numbers, names, code, constraints, length, format or language), if the new request depends on \
conversation context the candidate answer does not reflect, or if the candidate answer is a refusal or error the \
new request would not want.
Long texts are shortened with [...] in the middle; judge from what is shown.

Reply with JSON only: {"items": [{"id": <item id>, "candidates": [{"c": <candidate number>, "acceptable": true|false}]}]}"""


# renders a batch of turns, each with its reference and candidates, into the user message
def render(batch: list[dict]) -> str:
    j = config.load()["judge"]
    blocks = []
    for i, item in enumerate(batch, start=1):
        lines = [f"### Item {i}", f"NEW request:\n{head_tail(item['request'], j['request_chars'])}",
                 f"REFERENCE answer:\n{head_tail(item['answer'], j['answer_chars'])}"]
        for c, cand in enumerate(item["candidates"], start=1):
            lines.append(f"CANDIDATE {c} earlier request:\n{head_tail(cand['request'], j['request_chars'])}\n"
                         f"CANDIDATE {c} answer:\n{head_tail(cand['answer'], j['answer_chars'])}")
        blocks.append("\n\n".join(lines))
    return "\n\n".join(blocks)


# groups candidate rows into judge items for the given turns, keeping queue order
def items_for(turn_ids: list[str], turns: pd.DataFrame, cands: pd.DataFrame) -> list[dict]:
    t = turns.set_index("turn_id")
    by_turn = cands.sort_values("rank").groupby("turn_id")
    items = []
    for tid in turn_ids:
        cs = by_turn.get_group(tid)
        items.append({"turn_id": tid, "request": t.at[tid, "request"], "answer": t.at[tid, "answer"],
                      "candidates": [{"cand_turn_id": cid, "request": t.at[cid, "request"], "answer": t.at[cid, "answer"]}
                                     for cid in cs["cand_turn_id"]]})
    return items


# labels every candidate of the given turns with one judge model, sending batches in parallel
def label(turn_ids: list[str], turns: pd.DataFrame, cands: pd.DataFrame, model: str, log=print) -> pd.DataFrame:
    from concurrent.futures import ThreadPoolExecutor

    per = config.load()["judge"]["items_per_request"]
    workers = config.load()["gateway"]["workers"] if model.startswith("claude") else 1
    client = Client()
    items = items_for(turn_ids, turns, cands)
    batches = [items[i : i + per] for i in range(0, len(items), per)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        parts = [p for res in pool.map(lambda b: call_splitting(b, lambda x: client.json_call(model, JUDGE_PROMPT, render(x), log=log)), batches)
                 for p in res]
    refused = [item["turn_id"] for batch, reply in parts if reply is None for item in batch]
    if refused:
        log(f"{model}: refused {len(refused)} turns, left unlabeled")
    rows = []
    for batch, reply in parts:
        if reply is None:
            continue
        verdicts = {(int(it["id"]), int(c["c"])): bool(c["acceptable"])
                    for it in reply.get("items", []) for c in it.get("candidates", []) if "acceptable" in c}
        for i, item in enumerate(batch, start=1):
            for c, cand in enumerate(item["candidates"], start=1):
                if (i, c) in verdicts:
                    rows.append({"turn_id": item["turn_id"], "cand_turn_id": cand["cand_turn_id"],
                                 "acceptable": int(verdicts[(i, c)]), "judge": model})
    log(f"{model}: labeled {len(items)} turns ({client.calls} new calls, {client.tokens} tokens)")
    return pd.DataFrame(rows, columns=["turn_id", "cand_turn_id", "acceptable", "judge"])
