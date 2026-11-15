# loads config.yaml once and resolves project paths
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


# reads config.yaml from the repo root and caches it for the process
@lru_cache(maxsize=1)
def load() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# turns a configured path into an absolute one under the repo, creating the folder
def path(key: str) -> Path:
    raw = Path(load()["paths"][key])
    full = raw if raw.is_absolute() else ROOT / raw
    full.mkdir(parents=True, exist_ok=True)
    return full


# points every huggingface cache at D: so nothing lands on the full C: drive
def set_cache_env() -> None:
    cfg = load()["paths"]
    os.environ.setdefault("HF_HOME", cfg["hf_cache"])
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", cfg["hf_cache"])
    os.environ.setdefault("HF_DATASETS_CACHE", cfg["datasets_cache"])
