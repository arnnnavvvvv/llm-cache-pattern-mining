# phase 3c: export gold sheets for two raters, then score judge-human agreement once they come back
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, gold, storage

GOLD_DIR = config.path("results") / "human_checks"


# writes gold pairs and the two blind sheets (never overwriting filled ones)
def export():
    labels, st, turns = storage.load("labels"), storage.load("label_queue"), storage.load("turns")
    primary = labels[labels["judge"] == config.load()["judge"]["model"]]
    pairs = gold.pick(primary, st)
    pairs.to_csv(GOLD_DIR / "gold_pairs.csv", index=False)
    pairs[["turn_id"]].drop_duplicates().to_csv(GOLD_DIR / "gold_turns.csv", index=False)
    for rater, sheet in gold.sheets(pairs, turns).items():
        out = GOLD_DIR / f"gold_sheet_{rater}.csv"
        if out.exists():
            print(f"{out.name} exists, left as is")
            continue
        sheet.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"wrote {out.name} ({len(sheet)} pairs)")


# agreement table: rater vs rater, each judge vs each rater and vs the rater consensus, judge vs judge
def score():
    cfg = config.load()["judge"]
    labels = storage.load("labels")
    a = gold.read_sheet(pd.read_csv(GOLD_DIR / "gold_sheet_rater_a.csv", encoding="utf-8-sig"))
    b = gold.read_sheet(pd.read_csv(GOLD_DIR / "gold_sheet_rater_b.csv", encoding="utf-8-sig"))
    both = a.index.intersection(b.index)
    consensus = a.loc[both][a.loc[both] == b.loc[both]]
    rows = [gold.agreement("rater_a vs rater_b", a, b)]
    for model in [cfg["model"], cfg["second_model"]]:
        j = gold.judge_series(labels, model)
        rows += [gold.agreement(f"{model} vs rater_a", j, a), gold.agreement(f"{model} vs rater_b", j, b),
                 gold.agreement(f"{model} vs consensus", j, consensus)]
    rows.append(gold.agreement("judge vs second judge", gold.judge_series(labels, cfg["model"]), gold.judge_series(labels, cfg["second_model"])))
    table = pd.DataFrame(rows)
    table["gate"] = config.load()["labels"]["min_judge_human_agreement"]
    storage.save_result(table, "gold_agreement")
    print(table.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["export", "score"])
    export() if parser.parse_args().step == "export" else score()
