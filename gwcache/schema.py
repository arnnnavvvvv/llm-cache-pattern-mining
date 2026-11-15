# column contracts for the shared tables, checked whenever a phase writes one
import pandas as pd

TABLES = {
    "turns": {
        "turn_id": "object", "session_id": "object", "user_id": "object", "turn_index": "int64",
        "timestamp": "datetime64[ns, UTC]", "request": "object", "answer": "object", "period": "object",
    },
    "candidates": {
        "turn_id": "object", "rank": "int64", "cand_turn_id": "object", "sim": "float64",
    },
    "labels": {
        "turn_id": "object", "cand_turn_id": "object", "acceptable": "int64", "judge": "object",
    },
}


# raises if a table is missing required columns or has the wrong dtypes
def validate(df: pd.DataFrame, table: str) -> None:
    spec = TABLES[table]
    missing = [c for c in spec if c not in df.columns]
    if missing:
        raise ValueError(f"{table}: missing columns {missing}")
    wrong = {c: str(df[c].dtype) for c, t in spec.items() if str(df[c].dtype) != t and not _compatible(str(df[c].dtype), t)}
    if wrong:
        raise ValueError(f"{table}: unexpected dtypes {wrong}")


# treats pandas string and object dtypes, and any utc timestamp resolution, as the same thing
def _compatible(actual: str, expected: str) -> bool:
    if expected == "object":
        return actual in ("object", "string", "str")
    if expected.startswith("datetime64"):
        return actual.startswith("datetime64") and "UTC" in actual
    return False
