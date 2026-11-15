# phase 1: pull wildchat turns with real answers and split sessions by time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gwcache import config, ingest, schema, storage


# builds and saves the turn table plus its summary stats
def main():
    config.set_cache_env()
    turns = ingest.build_turns()
    schema.validate(turns, "turns")
    storage.save(turns, "turns")
    stats = ingest.describe(turns)
    storage.save_result(stats, "dataset_stats")
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()
