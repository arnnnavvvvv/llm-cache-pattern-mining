# Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways

Semantic caches in LLM gateways usually decide one request at a time: serve the cached answer if the new request is similar enough to an old one. This project mines **behavioral patterns** from gateway traffic: frequent and ordered sequences of what users ask (intent) and how they follow up (dialogue act), within sessions and across each user's sessions. Those patterns become priors and features for three decisions:

- **Admission:** serve a cached answer, or go to a provider?
- **Routing:** send the request to a strong or a cheap model?
- **Trajectory fast-tracking (exploratory):** jump a conversation straight to an answer that satisfied similar users?

The claims, comparators, metrics and pass criteria are fixed in [PREREG.md](PREREG.md), along with a log of every change. All settings are in [config.yaml](config.yaml).

## Layout

| Path | Contents |
|---|---|
| `gwcache/` | the library: ingest, embeddings, intents and acts, candidates, judge, replay engine, metrics and stats, pattern miner, decision engine, routing, trajectories, live service |
| `scripts/` | one runner per build step, in numeric order |
| `tests/` | unit tests, including leakage checks on the pattern miner |
| `results/` | committed tables, figures, human-check sheets and the results register |
| `data/` | raw and intermediate data plus the LLM response cache (not committed) |

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Keys:

- **`.env` file (gitignored):** `AICREDITS_API_KEY=...`, for Anthropic models through the Anthropic-compatible gateway in `config.yaml`.
- **Environment variable:** `GROQ_API_KEY`, only for the Qwen act seeding.

Every Hugging Face cache points at `D:/Capstone/.cache`.

## Run order

`python run_all.py` runs everything in order. `python run_all.py 7` resumes from step 7.

| Step | Script | What it does |
|---|---|---|
| 1 | `01_ingest.py` | Streams 30k WildChat turns with the real answers; splits sessions into train/dev/confirm by time |
| 2 | `02_embed_intents.py` | Request embeddings; 20 intent clusters fit on the training period |
| 3 | `03_acts.py` | Dialogue act for every turn (LLM); a fast tagger for the live service |
| 4 | `04_candidates.py` | Top-3 earlier neighbours per turn; stratified labeling queue |
| 5a | `05a_judge_pick.py` | Three candidate judges on 100 training turns; cost and agreement |
| 5 | `05_label.py` | Reference-based judge labels every queued turn's candidates |
| 6 | `06_gold.py export` / `06_gold.py score` | Blind human gold sheets; judge-human agreement and kappa |
| 7 | `07_pairs.py` | Pair features: per-query, context, and patterns mined daily from past traffic (plus placebo versions) |
| 8 | `08_develop.py` | Development run on the dev period; saves the service bundle |
| 9 | `09_confirm.py` | The one-time confirmation run. Needs a clean tree and a tag on HEAD |
| 10 | `10_routing.py` | Routing experiment on human-voted strong-vs-weak conversations |
| 11 | `11_trajectory.py` | Exploratory trajectory fast-tracking |
| 12 | `12_service.py bench` / `12_service.py serve` | Latency benchmark, or run the live API |
| 13 | `13_figures.py` | Figures and `results/REGISTER.md` |

All LLM calls are cached on disk, so re-runs are free and interrupted jobs resume where they stopped.

## Human checks

The sheets and `RATER_GUIDE.md` are in `results/human_checks/`:

- **Gold set:** two raters each fill in the 199-pair gold sheets independently. Then run `python scripts/06_gold.py score`.
- **Act check:** one rater fills in `act_sheet.csv`. Re-running step 3 scores the tagger against it.
- **Satisfaction proxy:** one rater fills in `satisfaction_sheet.csv` (written by step 11).

## Gateway integration

`python scripts/12_service.py serve` starts the admission API on `127.0.0.1:8077`. A gateway calls `/admit` before forwarding a request, and calls `/record` after a provider answers.

| Endpoint | Body | Returns |
|---|---|---|
| `POST /admit` | `session_id`, `user_id`, `request` | `serve` (bool), `answer` when serving, `score`, `candidate`, `intent`, `act`, `latency_ms` |
| `POST /record` | the same fields plus `turn_id`, `answer`, and optionally `act`, `intent` | cache size |
| `GET /health` | (none) | liveness and cache size |
