# shared chart styling and policy names/colors for the report figures
import matplotlib.pyplot as plt

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ACCENT, ALERT, GOOD, NEUTRAL = "#2a78d6", "#d03b3b", "#1baf7a", "#9a9893"
LABELS = {"P1_fixed": "P1 fixed threshold", "P2_per_intent": "P2 per-intent thresholds", "P3_per_query": "P3 per-turn verifier",
          "P5_context": "P5 + context embedding", "P4_patterns": "P4 + mined patterns", "P4plus_context_patterns": "P4+ context and patterns"}
SHORT = {"P1_fixed": "P1", "P2_per_intent": "P2", "P3_per_query": "P3", "P5_context": "P5", "P4_patterns": "P4",
         "P4plus_context_patterns": "P4+"}
COLORS = {"P1_fixed": "#2a78d6", "P2_per_intent": "#eb6834", "P3_per_query": "#1baf7a",
          "P5_context": "#eda100", "P4_patterns": "#e87ba4", "P4plus_context_patterns": "#008300"}
ACTS = {"new_request": "new request", "follow_up": "follow-up", "new_ask_same_material": "new ask, same material",
        "correction": "correction", "continuation": "continuation"}


# new figure with the shared background
def figure(w: float = 8, h: float = 4.6):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=SURFACE)
    return fig, ax


# shared axis styling: recessive grid, no top/right spines, muted ticks
def style(ax, title: str = "", xlabel: str = "", ylabel: str = "", grid_axis: str = "both"):
    ax.set_facecolor(SURFACE)
    if title:
        ax.set_title(title, color=INK, loc="left", fontsize=11)
    ax.set_xlabel(xlabel, color=INK)
    ax.set_ylabel(ylabel, color=INK)
    ax.grid(color=GRID, linewidth=0.8, axis=grid_axis)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)


# writes the figure at print resolution and closes it
def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=SURFACE)
    plt.close(fig)
