# descriptive analysis for the paper: how wrong-reuse depends on dialogue behavior at fixed similarity
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gwcache import config, evaluate, features, storage

BANDS = [0.70, 0.80, 0.90, 0.97, 1.001]
BAND_NAMES = ["0.70-0.80", "0.80-0.90", "0.90-0.97", "0.97-1.00"]
ACT_ORDER = ["new_request", "follow_up", "new_ask_same_material", "correction", "continuation"]
# categorical slots of the reference palette in fixed order
ACT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


# self-contained vs context-dependent label for a column of dialogue acts
def behavior(acts: pd.Series) -> np.ndarray:
    return np.where(acts.astype(str) == "new_request", "self_contained", "context_dependent")


# wrong-reuse rate and pair count for every (dialogue act, similarity band) cell, plus the near-duplicate split
def wrong_reuse_table(lab: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lab = lab.assign(band=pd.cut(lab["sim"], BANDS, right=False, labels=BAND_NAMES))
    cell = (lab.groupby(["act", "band"], observed=True)["acceptable"].agg(["mean", "count"])
            .assign(wrong_reuse=lambda d: 1 - d["mean"]).drop(columns="mean").reset_index())
    near = lab[lab["sim"] >= 0.97]
    split = pd.concat([
        near.groupby(behavior(near["act"]))["acceptable"].agg(["mean", "count"]).assign(side="request"),
        near.groupby(behavior(near["cand_act"]))["acceptable"].agg(["mean", "count"]).assign(side="cache_entry"),
    ]).rename_axis("behavior").reset_index()
    split["wrong_reuse"] = 1 - split.pop("mean")
    overall = pd.DataFrame([{"behavior": "all", "side": "all", "count": len(near), "wrong_reuse": 1 - near["acceptable"].mean()}])
    return cell, pd.concat([overall, split], ignore_index=True)


# grouped bars: wrong-reuse by similarity band, one bar per dialogue act, legend above the plot
def figure(cell: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.2, 3.9), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    width = 0.16
    x = np.arange(len(BAND_NAMES))
    for k, (act, color) in enumerate(zip(ACT_ORDER, ACT_COLORS)):
        d = cell[cell["act"] == act].set_index("band").reindex(BAND_NAMES)
        ax.bar(x + (k - 2) * width, d["wrong_reuse"] * 100, width - 0.02, color=color, label=act.replace("_", " "))
    ax.set_xticks(x, BAND_NAMES)
    ax.set_xlabel("Cosine similarity to the cached request", color=INK)
    ax.set_ylabel("Wrong-reuse rate (%)", color=INK)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.legend(frameon=False, labelcolor=INK, fontsize=8, ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    fig.savefig(config.path("figures") / "wrong_reuse_by_act.png", dpi=250, facecolor=SURFACE)
    plt.close(fig)


def main():
    turns, labels = storage.load("turns"), storage.load("labels")
    pairs = features.as_categorical(storage.load("pairs"))
    lab = evaluate.labeled_pairs(pairs, labels)
    cell, near = wrong_reuse_table(lab)
    storage.save_result(cell, "wrong_reuse_by_act")
    storage.save_result(near, "near_duplicate_behavior")
    figure(cell)
    print(near.to_string(index=False))


if __name__ == "__main__":
    main()
