# phase 2a: embed every request and assign intent clusters fit on the training period
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from gwcache import config, embed, intents, storage


# embeds requests, clusters intents, saves vectors and the intent table
def main():
    config.set_cache_env()
    turns = storage.load("turns")
    vecs = embed.encode(turns["request"].tolist())
    np.save(config.path("work") / "vecs.npy", vecs)
    turns["intent"], centers = intents.fit_assign(vecs, (turns["period"] == "train").to_numpy())
    np.save(config.path("work") / "intent_centers.npy", centers)
    storage.save(turns, "turns")
    table = intents.describe(turns["request"], turns["intent"].to_numpy())
    storage.save_result(table, "intent_clusters")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
