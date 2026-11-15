# phase 6: development run, train on the train period and evaluate on dev (iterate here, never on confirm)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
import pandas as pd

from gwcache import config, decision, evaluate, experiments, features, rules, storage
from gwcache.features import CATEGORICAL


# fits p4 on train+dev labels and saves everything the live service needs in one file
def save_bundle(pairs, labels, turns):
    cols = experiments.FEATURE_SETS["P4_patterns"]
    lab = evaluate.labeled_pairs(pairs, labels)
    lab = lab[lab["turn_id"].map(turns.set_index("turn_id")["period"]).isin(["train", "dev"])]
    work = config.path("work")
    lab, _ = rules.add_prior(lab, lab.head(1), seed=config.load()["seed"])
    table, default = rules.mine_rules(lab)
    storage.save_result(rules.top_rules(lab), "behavioral_rules")
    joblib.dump({"model": decision.fit_verifier(lab, cols), "cols": cols, "rules": (table.to_dict(), default),
                 "categories": {c: list(pairs[c].cat.categories) for c in CATEGORICAL},
                 "centers": np.load(work / "intent_centers.npy"), "act_model": joblib.load(work / "act_model.joblib")},
                work / "service_bundle.joblib")


# replays every policy on dev with bootstrap cis, plus the k-fold spread diagnostic on train
def main():
    turns, labels, strata = storage.load("turns"), storage.load("labels"), storage.load("label_queue")
    pairs = features.as_categorical(storage.load("pairs"))
    pol = experiments.main_policies()
    res = evaluate.compare(pairs, labels, turns, strata, pol, ["train"], "dev",
                           focal="P4_patterns", n_boot=config.load()["eval"]["n_boot"])
    storage.save_result(res["summary"], "dev_summary")
    storage.save_result(res["comparisons"], "dev_comparisons")
    storage.save_result(res["curves"], "dev_curves")
    cv = evaluate.cv_diagnostic(pairs, labels, turns, experiments.FEATURE_SETS, ["train"])
    storage.save_result(cv, "dev_cv_folds")
    storage.save_result(evaluate.spread(cv), "dev_cv_spread")
    save_bundle(pairs, labels, turns)
    pd.set_option("display.width", 220)
    print(res["summary"].to_string(index=False))
    print(res["comparisons"].to_string(index=False))
    print(evaluate.spread(cv).to_string(index=False))


if __name__ == "__main__":
    main()
