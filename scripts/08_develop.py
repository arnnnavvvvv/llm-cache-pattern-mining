# phase 6: development run, train on the train period and evaluate on dev (iterate here, never on confirm)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, evaluate, experiments, storage


# replays every policy on dev with bootstrap cis, plus the k-fold spread diagnostic on train
def main():
    turns, labels, strata = storage.load("turns"), storage.load("labels"), storage.load("label_queue")
    pairs = storage.load("pairs")
    pol = experiments.main_policies()
    res = evaluate.compare(pairs, labels, turns, strata, pol, ["train"], "dev",
                           focal="P4_patterns", n_boot=config.load()["eval"]["n_boot"])
    storage.save_result(res["summary"], "dev_summary")
    storage.save_result(res["comparisons"], "dev_comparisons")
    storage.save_result(res["curves"], "dev_curves")
    cv = evaluate.cv_diagnostic(pairs, labels, turns, experiments.FEATURE_SETS, ["train"])
    storage.save_result(cv, "dev_cv_folds")
    storage.save_result(evaluate.spread(cv), "dev_cv_spread")
    pd.set_option("display.width", 220)
    print(res["summary"].to_string(index=False))
    print(res["comparisons"].to_string(index=False))
    print(evaluate.spread(cv).to_string(index=False))


if __name__ == "__main__":
    main()
