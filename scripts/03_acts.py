# phase 2b: seed dialogue-act labels with an llm, train the tagger, tag every turn, export the human check
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from gwcache import acts, config, storage


# runs seeding (cached), training, tagging and writes the human check sheet if missing
def main():
    turns = storage.load("turns")
    vecs = np.load(config.path("work") / "vecs.npy")
    prev = acts.previous_requests(turns)

    seeds = storage.load("act_seeds") if storage.exists("act_seeds") else acts.seed_labels(turns, prev)
    storage.save(seeds, "act_seeds")

    x = acts.features(turns, vecs, prev)
    pos = pd.Series(np.arange(len(turns)), index=turns["turn_id"])
    rows = pos.loc[seeds["turn_id"]].to_numpy()
    model, cv_f1 = acts.train(x[rows], seeds["act"].to_numpy(), turns["session_id"].to_numpy()[rows])
    turns["act"] = model.predict(x)
    storage.save(turns, "turns")

    sheet_path = config.path("results") / "human_checks" / "act_sheet.csv"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    if not sheet_path.exists():
        acts.human_sheet(turns, prev).to_csv(sheet_path, index=False, encoding="utf-8-sig")
    human = acts.score_human(pd.read_csv(sheet_path, encoding="utf-8-sig"), turns.set_index("turn_id")["act"])

    report = {"seed_labels": len(seeds), "seed_distribution": seeds["act"].value_counts().to_dict(),
              "cv_macro_f1_vs_llm": cv_f1, "human_check": human,
              "gate_macro_f1": config.load()["acts"]["min_macro_f1"],
              "tagged_distribution": turns["act"].value_counts().to_dict()}
    storage.save_json(report, "act_tagger")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
