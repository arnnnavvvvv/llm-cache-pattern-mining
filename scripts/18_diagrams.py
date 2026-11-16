# draws the system block diagram, the offline data pipeline and the per-request decision flow
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from gwcache import config
from gwcache.plotstyle import ACCENT, GRID, INK, MUTED, SURFACE

OUT = config.path("figures") / "report"
FILL = {"io": "#eef4fc", "core": "#fdf0f5", "store": "#f3f2ee", "decide": "#eaf7f1", "warn": "#fdeeee"}
EDGE = {"io": ACCENT, "core": "#e87ba4", "store": MUTED, "decide": "#1baf7a", "warn": "#d03b3b"}


# empty canvas in data units so boxes can be placed on a simple grid
def canvas(w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=SURFACE)
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


# rounded box with a bold title and an optional smaller second line, returns its anchor points
def box(ax, x, y, w, h, title, sub="", kind="core", size=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", facecolor=FILL[kind],
                                edgecolor=EDGE[kind], linewidth=1.4))
    ax.text(x + w / 2, y + h / 2 + (1.4 if sub else 0), title, ha="center", va="center", fontsize=size, color=INK, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 1.8, sub, ha="center", va="center", fontsize=size - 2, color=MUTED)
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}


# arrow between two anchor points with an optional label at its middle
def arrow(ax, a, b, label="", color=MUTED, style="-|>", ls="-", offset=(0, 1.2)):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12, color=color, linewidth=1.3, linestyle=ls,
                                 shrinkA=4, shrinkB=4))
    if label:
        ax.text((a[0] + b[0]) / 2 + offset[0], (a[1] + b[1]) / 2 + offset[1], label, ha="center", fontsize=7, color=MUTED)


# gateway architecture: online request path on top, offline learning loop below
def block_diagram():
    fig, ax = canvas(13, 7.2)
    ax.text(2, 69, "Online request path (per request)", fontsize=10, color=INK, weight="bold")
    client = box(ax, 2, 50, 14, 10, "Client", "chat request", "io")
    emb = box(ax, 22, 50, 16, 10, "Embedder", "MiniLM-L6-v2", "core")
    knn = box(ax, 44, 50, 18, 10, "Candidate search", "FAISS top-3, sim >= 0.70", "core")
    feat = box(ax, 68, 50, 18, 10, "Behavior features", "acts, states, patterns", "core")
    dec = box(ax, 92, 50, 18, 10, "Admission decision", "verifier + rule prior", "decide")
    serve = box(ax, 115, 56, 14, 8, "Serve cached", "score >= threshold", "decide", 8)
    llm = box(ax, 115, 43, 14, 8, "Call LLM", "otherwise", "io", 8)
    arrow(ax, client["r"], emb["l"])
    arrow(ax, emb["r"], knn["l"])
    arrow(ax, knn["r"], feat["l"])
    arrow(ax, feat["r"], dec["l"])
    arrow(ax, dec["r"], serve["l"])
    arrow(ax, dec["r"], llm["l"])

    ax.text(2, 37, "Offline learning loop (daily, past traffic only)", fontsize=10, color=INK, weight="bold")
    logs = box(ax, 2, 18, 16, 11, "Gateway log", "request, answer,\nsession, time", "store")
    acts = box(ax, 24, 18, 16, 11, "Act tagging", "5 dialogue acts", "core")
    mine = box(ax, 46, 18, 18, 11, "Pattern mining", "FP-Growth, PrefixSpan,\nbehavioral states", "core")
    rules = box(ax, 70, 18, 18, 11, "Association rules", "smoothed prior per\n(state, act) pair", "core")
    train = box(ax, 94, 18, 18, 11, "Verifier training", "LightGBM on\njudged reuses", "decide")
    judge = box(ax, 94, 2, 18, 9, "Reference judge", "acceptable reuse labels", "warn", 8)
    arrow(ax, logs["r"], acts["l"])
    arrow(ax, acts["r"], mine["l"])
    arrow(ax, mine["r"], rules["l"])
    arrow(ax, rules["r"], train["l"])
    arrow(ax, judge["t"], train["b"])
    arrow(ax, (103, 29.5), (103, 49.5), "model + rules", color=ACCENT, ls="--", offset=(7, 0))
    arrow(ax, (55, 29.5), (77, 49.5), "pattern tables", color=ACCENT, ls="--", offset=(-6, 0))
    ax.text(45, 8, "answers from the LLM are logged back to the gateway log; answers served from cache never become cache entries",
            fontsize=7, color=MUTED, ha="center")
    fig.tight_layout()
    fig.savefig(OUT / "block_diagram.png", dpi=220, facecolor=SURFACE)
    plt.close(fig)


# the fifteen scripts as a left-to-right pipeline in four stages
def pipeline():
    fig, ax = canvas(13, 6)
    stages = [("Data", ["01 ingest WildChat", "02 embed + intents", "03 dialogue acts", "04 candidates + queue"], "io"),
              ("Labels", ["05a judge pick", "05 label queue", "06 gold sheets", "07 pair features"], "warn"),
              ("Evaluation", ["08 develop (dev)", "09 confirm (frozen)", "10 routing", "11 trajectory"], "decide"),
              ("Delivery", ["12 service + bench", "13-15 figures, paper", "16-18 report assets", "demo app"], "core")]
    for i, (name, steps, kind) in enumerate(stages):
        x = 3 + i * 32
        ax.text(x + 13, 55, name, ha="center", fontsize=11, color=INK, weight="bold")
        prev = None
        for j, step in enumerate(steps):
            b = box(ax, x, 41 - j * 11, 26, 8, step, "", kind, 8.5)
            if prev:
                arrow(ax, prev["b"], b["t"])
            prev = b
        if i < 3:
            arrow(ax, (x + 26.5, 45), (x + 31.5, 45), color=ACCENT)
    ax.text(65, 2, "every table and figure is rebuilt from raw data by run_all.py; the confirmation run is tied to tag freeze-confirm-2026-11-16",
            ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(OUT / "pipeline.png", dpi=220, facecolor=SURFACE)
    plt.close(fig)


# decision flow for one incoming request
def decision_flow():
    fig, ax = canvas(9, 9.5)
    req = box(ax, 25, 84, 40, 7, "New request in a session", "", "io")
    cand = box(ax, 25, 71, 40, 7, "Any cached entry with similarity >= 0.70?", "", "core", 8.5)
    feat = box(ax, 25, 57, 40, 8, "Tag dialogue act, compute behavioral state", "match mined sequences and rules", "core", 8.5)
    score = box(ax, 25, 43, 40, 8, "Verifier probability q for each candidate", "softmax over top-3, staleness 2^(-age/T)", "core", 8.5)
    ben = box(ax, 25, 29, 40, 8, "Expected benefit B = U q - L (1 - q)", "keep the best candidate", "decide", 8.5)
    hit = box(ax, 2, 12, 34, 8, "Serve cached answer", "cache hit", "decide")
    miss = box(ax, 54, 12, 34, 8, "Call the LLM", "log answer as a new entry", "io")
    nocand = box(ax, 72, 71, 16, 7, "Call LLM", "", "io", 8)
    arrow(ax, req["b"], cand["t"])
    arrow(ax, cand["r"], nocand["l"], "no", offset=(0, 1))
    arrow(ax, cand["b"], feat["t"], "yes", offset=(2.5, 0))
    arrow(ax, feat["b"], score["t"])
    arrow(ax, score["b"], ben["t"])
    arrow(ax, (35, 29), hit["t"], "B >= threshold", offset=(-6, 0))
    arrow(ax, (55, 29), miss["t"], "otherwise", offset=(5, 0))
    ax.text(45, 3, "threshold set per policy so wrong reuse stays at or under the target level", ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(OUT / "decision_flow.png", dpi=220, facecolor=SURFACE)
    plt.close(fig)


# builds all three diagrams
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    block_diagram()
    pipeline()
    decision_flow()


if __name__ == "__main__":
    main()
