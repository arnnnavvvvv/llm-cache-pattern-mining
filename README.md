# Pattern-Mining-Driven Cache Admission and Routing for Multi-Provider LLM Gateways

Semantic caches in LLM gateways usually decide one request at a time: serve the cached answer if the new request is similar enough to an old one. This project mines behavioral patterns from gateway traffic, meaning frequent and ordered sequences of what users ask and how they follow up within sessions and across a user's sessions. Those patterns are then used as priors and features for three decisions:

- **Admission:** serve a cached answer, or go to a provider?
- **Routing:** which provider gets the request?
- **Trajectory fast-tracking (exploratory):** serve where a conversation is heading, saving turns?

The claims and pass criteria are fixed in [PREREG.md](PREREG.md). All settings are in [config.yaml](config.yaml).

## Layout

- `gwcache/`: the library: ingest, embeddings, dialogue acts, candidates, judge, replay engine, pattern miner, decision engine, routing, trajectories, service.
- `scripts/`: one runner per build phase, numbered in order.
- `tests/`: unit tests, including the leakage checks.
- `results/`: committed tables and figures.
- `data/`: raw and intermediate data (not committed).

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set GROQ_API_KEY=...
pytest -q
```

Every Hugging Face cache is pointed at `D:/Capstone/.cache` (see `config.yaml`).

## Running

Run the scripts in `scripts/` in numeric order, or run everything with `python run_all.py`. Each script reads the outputs of the previous phase from `data/work/`. LLM calls are cached on disk, so re-runs are free and interrupted jobs resume.
