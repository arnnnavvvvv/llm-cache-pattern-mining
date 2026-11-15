# phase 7: the one-time confirmation run on frozen code: main test, placebos, ablations, mechanism, robustness
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, evaluate, experiments, storage


# refuses to run unless the working tree is clean and HEAD carries a tag, so the run is tied to frozen code
def frozen_tag() -> str:
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    tag = subprocess.run(["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True).stdout.strip()
    if dirty or not tag:
        sys.exit("confirmation run needs a clean tree and a tag on HEAD (git tag freeze-...)")
    return tag


# main comparison with p4 as the focal policy, against every comparator
def main_test(pairs, labels, turns, strata, n_boot) -> dict:
    res = evaluate.compare(pairs, labels, turns, strata, experiments.main_policies(), ["train", "dev"], "confirm",
                           focal="P4_patterns", n_boot=n_boot)
    for key in ["summary", "comparisons", "curves"]:
        storage.save_result(res[key], f"confirm_{key}")
    return res


# placebo policies (scrambled histories) and ablations, each compared against p3
def controls(pairs, labels, turns, strata, n_boot):
    cols = experiments.FEATURE_SETS["P4_patterns"]
    pol = {"P3_per_query": experiments.learned(experiments.FEATURE_SETS["P3_per_query"]),
           "placebo_shuffled": experiments.placebo(storage.load("pairs_shuffled"), cols),
           "placebo_borrowed": experiments.placebo(storage.load("pairs_borrowed"), cols)}
    pol.update({name: experiments.learned(c) for name, c in experiments.ABLATIONS.items()})
    res = evaluate.compare(pairs, labels, turns, strata, pol, ["train", "dev"], "confirm", focal="P3_per_query", n_boot=n_boot)
    storage.save_result(res["summary"], "confirm_controls_summary")
    storage.save_result(res["comparisons"], "confirm_controls_vs_p3")


# robustness: a stricter similarity floor (drop weaker candidates) with the core policies
def robustness(pairs, labels, turns, strata, n_boot):
    strict = pairs[pairs["sim"] >= 0.80].reset_index(drop=True)
    pol = {k: v for k, v in experiments.main_policies().items() if k in ("P1_fixed", "P3_per_query", "P4_patterns")}
    res = evaluate.compare(strict, labels, turns, strata, pol, ["train", "dev"], "confirm", focal="P4_patterns", n_boot=n_boot)
    storage.save_result(res["summary"].assign(variant="sim_floor_0.80"), "confirm_robust_floor_summary")
    storage.save_result(res["comparisons"].assign(variant="sim_floor_0.80"), "confirm_robust_floor_comparisons")


# runs everything once and records which frozen tag produced it
def main():
    tag = frozen_tag()
    n_boot = config.load()["eval"]["n_boot"]
    turns, labels, strata, pairs = storage.load("turns"), storage.load("labels"), storage.load("label_queue"), storage.load("pairs")
    res = main_test(pairs, labels, turns, strata, n_boot)
    storage.save_result(experiments.mechanism(res, strata, turns, ["P3_per_query", "P4_patterns"], 0.10), "confirm_mechanism")
    controls(pairs, labels, turns, strata, n_boot)
    robustness(pairs, labels, turns, strata, n_boot)
    cv = evaluate.cv_diagnostic(pairs, labels, turns, experiments.FEATURE_SETS, ["train", "dev"])
    storage.save_result(evaluate.spread(cv), "confirm_cv_spread")
    storage.save_result(experiments.run_positive_control(), "positive_control")

    comp = res["comparisons"]
    comparators = ["P1_fixed", "P2_per_intent", "P3_per_query", "P5_context"]
    p4_rows = comp[comp["comparison"].isin([f"P4_patterns - {c}" for c in comparators])]
    verdict = {"tag": tag, "labeled_confirm_turns": int(res["summary"]["labeled_turns"].iloc[0]),
               "h1a_pass": bool(p4_rows["holm_reject"].all() and (p4_rows["gain"] > 0).all())}
    storage.save_json(verdict, "confirm_verdict")
    pd.set_option("display.width", 220)
    print(res["summary"].to_string(index=False))
    print(comp.to_string(index=False))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
