# phase 3b: judge the next turns in the labeling queue (resumable, llm calls are cached on disk)
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, judge, schema, storage


# labels up to --max-turns unlabeled turns from the queue, saving after every chunk
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--model", default=None, help="defaults to the primary judge in config")
    parser.add_argument("--turn-file", default=None, help="csv with a turn_id column to label instead of the queue")
    parser.add_argument("--chunk", type=int, default=40)
    args = parser.parse_args()

    model = args.model or config.load()["judge"]["model"]
    turns, cands = storage.load("turns"), storage.load("candidates")
    labels = storage.load("labels") if storage.exists("labels") else pd.DataFrame(columns=["turn_id", "cand_turn_id", "acceptable", "judge"])
    done = set(labels.loc[labels["judge"] == model, "turn_id"])

    order = pd.read_csv(args.turn_file)["turn_id"] if args.turn_file else storage.load("label_queue")["turn_id"]
    todo = [t for t in order if t not in done][: args.max_turns]
    print(f"{model}: {len(done)} turns already labeled, {len(todo)} to go", flush=True)

    for start in range(0, len(todo), args.chunk):
        new = judge.label(todo[start : start + args.chunk], turns, cands, model, log=lambda m: print(m, flush=True))
        labels = pd.concat([labels, new], ignore_index=True).astype({"acceptable": "int64"})
        schema.validate(labels, "labels")
        storage.save(labels, "labels")
    print(f"total label rows: {len(labels)}", flush=True)


if __name__ == "__main__":
    main()
