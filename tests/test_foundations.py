# checks for config loading, schema validation and the llm cache key
import pandas as pd
import pytest

from gwcache import config, llm, schema


# config loads and has the sections every phase relies on
def test_config_has_sections():
    cfg = config.load()
    for key in ["paths", "ingest", "candidates", "judge", "eval", "decision"]:
        assert key in cfg


# a table with the right columns passes, a missing column fails
def test_schema_validation():
    ok = pd.DataFrame({"turn_id": ["a"], "rank": [1], "cand_turn_id": ["b"], "sim": [0.9]})
    schema.validate(ok, "candidates")
    with pytest.raises(ValueError):
        schema.validate(ok.drop(columns=["sim"]), "candidates")


# the cache key is deterministic and changes when the prompt changes
def test_cache_key_stable():
    a = llm.cache_key("m", "s", "u", {"t": 0})
    assert a == llm.cache_key("m", "s", "u", {"t": 0})
    assert a != llm.cache_key("m", "s", "u2", {"t": 0})
