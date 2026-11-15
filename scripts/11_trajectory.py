# phase 9: exploratory trajectory fast-tracking on the confirmation period
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from gwcache import config, storage, trajectory


# matches confirm sessions to stored trajectories, judges up to --max sessions, and writes the curve
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=120)
    args = parser.parse_args()
    cfg = config.load()
    turns = storage.load("turns")
    vecs = np.load(config.path("work") / "vecs.npy")
    sessions = trajectory.satisfied_sessions(turns)

    sheet = config.path("results") / "human_checks" / "satisfaction_sheet.csv"
    if not sheet.exists():
        trajectory.human_sheet(turns, sessions).to_csv(sheet, index=False, encoding="utf-8-sig")

    matches = trajectory.match(turns, vecs, sessions, ["train", "dev"], "confirm")
    eligible = int((sessions["satisfied"] & (sessions["period"] == "confirm")).sum())
    near = matches[matches["match_sim"] >= cfg["trajectory"]["match_sim"] - 0.1].sort_values("match_sim", ascending=False)
    judged = trajectory.judge(near.head(args.max), turns, cfg["judge"]["model"])
    storage.save(judged, "trajectory_judged")
    curve = trajectory.turns_saved_curve(judged, eligible)
    storage.save_result(curve, "trajectory_curve")
    oracle = float((sessions.loc[sessions["satisfied"] & (sessions["period"] == "confirm"), "n_turns"] - 1).mean())
    storage.save_json({"eligible_sessions": eligible, "matched": len(matches), "judged": len(judged),
                       "oracle_turns_saved_per_session": oracle, "single_answer_cache_turns_saved": 0.0,
                       "note": "exploratory; satisfaction proxy pending human check"}, "trajectory_summary")
    print(curve.tail(15).to_string(index=False))


if __name__ == "__main__":
    main()
