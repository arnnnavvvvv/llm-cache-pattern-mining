# phase 10: run the admission api, or benchmark it by replaying dev traffic into the cache and timing confirm requests
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from gwcache import config, patterns, service, storage


# engine loaded with the frozen bundle and the patterns mined from all traffic before the confirm period
def build_engine() -> service.Engine:
    config.set_cache_env()
    turns = storage.load("turns")
    cutoff = turns.loc[turns["period"] == "confirm", "timestamp"].min().floor("D")
    return service.Engine(config.path("work") / "service_bundle.joblib", patterns.mine_before(turns, cutoff))


# seeds the cache with dev turns, then times admit calls for a sample of confirm turns through the http layer
def bench(n_seed: int, n_admit: int):
    from fastapi.testclient import TestClient

    turns = storage.load("turns")
    engine = build_engine()
    client = TestClient(service.create_app(engine))
    for r in turns[turns["period"] == "dev"].head(n_seed).itertuples():
        client.post("/record", json={"session_id": r.session_id, "user_id": r.user_id, "turn_id": r.turn_id,
                                     "request": r.request, "answer": r.answer, "act": r.act, "intent": int(r.intent)})
    sample = turns[turns["period"] == "confirm"].head(n_admit)
    lat, served, wall = [], 0, []
    for r in sample.itertuples():
        t0 = time.perf_counter()
        out = client.post("/admit", json={"session_id": r.session_id, "user_id": r.user_id, "request": r.request}).json()
        wall.append((time.perf_counter() - t0) * 1000)
        lat.append(out["latency_ms"])
        served += out["serve"]
    report = {"cache_entries": len(engine.cache_meta), "admit_calls": len(lat), "served": served,
              "engine_ms_p50": float(np.percentile(lat, 50)), "engine_ms_p95": float(np.percentile(lat, 95)),
              "http_ms_p50": float(np.percentile(wall, 50)), "http_ms_p95": float(np.percentile(wall, 95))}
    storage.save_json(report, "service_latency")
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["serve", "bench"])
    parser.add_argument("--seed", type=int, default=3000)
    parser.add_argument("--admit", type=int, default=300)
    args = parser.parse_args()
    if args.mode == "bench":
        bench(args.seed, args.admit)
    else:
        import uvicorn
        cfg = config.load()["service"]
        uvicorn.run(service.create_app(build_engine()), host=cfg["host"], port=cfg["port"])
