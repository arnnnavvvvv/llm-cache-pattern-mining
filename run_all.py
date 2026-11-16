# rebuilds every table and figure from raw data by running the phase scripts in order
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    ["scripts/01_ingest.py"],
    ["scripts/02_embed_intents.py"],
    ["scripts/03_acts.py"],
    ["scripts/04_candidates.py"],
    ["scripts/05a_judge_pick.py"],
    ["scripts/05_label.py"],
    ["scripts/06_gold.py", "export"],
    ["scripts/07_pairs.py"],
    ["scripts/08_develop.py"],
    ["scripts/09_confirm.py"],
    ["scripts/10_routing.py"],
    ["scripts/11_trajectory.py"],
    ["scripts/12_service.py", "bench"],
    ["scripts/13_figures.py"],
    ["scripts/14_analysis.py"],
    ["scripts/15_paper.py"],
    ["scripts/16_exploratory.py"],
    ["scripts/17_report_figures.py"],
    ["scripts/18_diagrams.py"],
    ["scripts/20_report_tables.py"],
    ["report/build_report.py"],
    ["report/build_deck.py"],
    ["report/build_poster.py"],
]


# runs each step and stops at the first failure; pass a step number to start from there
def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for i, step in enumerate(STEPS[start:], start=start):
        print(f"\n=== step {i}: {' '.join(step)}", flush=True)
        if subprocess.run([sys.executable, str(ROOT / step[0]), *step[1:]], cwd=ROOT).returncode != 0:
            sys.exit(f"step {i} failed")


if __name__ == "__main__":
    main()
