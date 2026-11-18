# projected monthly savings of behavior-aware admission over a fixed-threshold cache, from measured hit rates and real prices
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from gwcache import config, storage

# gateway list price in inr per million tokens (input, output), the rates billed for this project
TIERS = {"premium (Sonnet-class)": (197.95, 989.75), "budget (Haiku-class)": (9.90, 49.49)}
SCALES = [1_000_000, 10_000_000, 100_000_000]
CHARS_PER_TOKEN = 4


# average tokens of one request and one answer in the replayed traffic (no conversation history, so a low estimate)
def call_tokens() -> tuple[float, float]:
    turns = storage.load("turns")
    return turns["request"].str.len().mean() / CHARS_PER_TOKEN, turns["answer"].str.len().mean() / CHARS_PER_TOKEN


# extra share of requests served by p4 over the fixed threshold at each wrong-reuse level, from the confirmation run
def extra_hits() -> dict:
    s = pd.read_csv(config.path("results") / "confirm_summary.csv").set_index("policy")
    return {lvl: (s.loc["P4_patterns", f"hit_at_wr{lvl}"], s.loc["P1_fixed", f"hit_at_wr{lvl}"]) for lvl in (5, 10)}


# one row per price tier, traffic scale and wrong-reuse level
def projection() -> pd.DataFrame:
    tin, tout = call_tokens()
    rows = []
    for tier, (p_in, p_out) in TIERS.items():
        per_call = (tin * p_in + tout * p_out) / 1e6
        for lvl, (ours, standard) in extra_hits().items():
            for n in SCALES:
                avoided = (ours - standard) * n
                rows.append({"tier": tier, "wrong_reuse_level": lvl, "requests_per_month": n, "tokens_in": round(tin),
                             "tokens_out": round(tout), "cost_per_call_inr": per_call, "hit_ours": ours,
                             "hit_standard": standard, "calls_avoided_month": avoided,
                             "saving_inr_month": avoided * per_call, "saving_inr_year": avoided * per_call * 12})
    return pd.DataFrame(rows)


# writes the projection table
def main():
    df = projection()
    storage.save_result(df, "savings_projection")
    pd.set_option("display.width", 200)
    print(df[["tier", "wrong_reuse_level", "requests_per_month", "cost_per_call_inr", "calls_avoided_month",
              "saving_inr_month", "saving_inr_year"]].to_string(index=False))


if __name__ == "__main__":
    main()
