# small helpers for reading and writing the shared work tables
import json
from pathlib import Path

import pandas as pd

from gwcache import config


# full path of a parquet table in the work folder
def table_path(name: str) -> Path:
    return config.path("work") / f"{name}.parquet"


# saves a work table as parquet
def save(df: pd.DataFrame, name: str) -> Path:
    out = table_path(name)
    df.to_parquet(out, index=False)
    return out


# loads a work table, failing loudly if an earlier phase has not produced it
def load(name: str) -> pd.DataFrame:
    p = table_path(name)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing, run the phase that builds '{name}' first")
    return pd.read_parquet(p)


# true if a work table already exists
def exists(name: str) -> bool:
    return table_path(name).exists()


# writes a small committed result table (csv) under results/
def save_result(df: pd.DataFrame, name: str) -> Path:
    out = config.path("results") / f"{name}.csv"
    df.to_csv(out, index=False)
    return out


# writes a small json summary under results/
def save_json(obj: dict, name: str) -> Path:
    out = config.path("results") / f"{name}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    return out
