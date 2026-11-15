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


# a refusal inside a batch is narrowed down to the single item that caused it
def test_refusal_splitting_isolates_item():
    # fake model call that refuses any batch containing item 3
    def fn(batch):
        if 3 in batch:
            raise llm.Refusal("x")
        return {"n": len(batch)}
    parts = llm.call_splitting([1, 2, 3, 4, 5, 6, 7, 8], fn)
    assert [p for p, r in parts if r is None] == [[3]]
    assert sum(len(p) for p, _ in parts) == 8


# json is recovered from fenced or chatty replies
def test_parse_json_tolerates_fences():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.parse_json('Here you go: {"a": 2} done') == {"a": 2}
