# sentence embeddings for requests and a causal nearest-neighbour search over earlier turns
import numpy as np

from gwcache import config


# encodes texts with a sentence-transformers model and returns unit-length float32 vectors
def encode(texts: list[str], model_name: str | None = None) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    cfg = config.load()["embedding"]
    model = SentenceTransformer(model_name or cfg["model"], cache_folder=config.load()["paths"]["hf_cache"])
    vecs = model.encode(texts, batch_size=cfg["batch_size"], show_progress_bar=False, convert_to_numpy=True)
    return normalize(vecs.astype(np.float32))


# scales rows to unit length so inner product equals cosine similarity
def normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


# for each row (in time order), the top-k most similar strictly earlier rows
def causal_top_k(vecs: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    import faiss

    index = faiss.IndexFlatIP(vecs.shape[1])
    sims = np.full((len(vecs), k), np.nan, dtype=np.float32)
    ids = np.full((len(vecs), k), -1, dtype=np.int64)
    for i in range(len(vecs)):
        if index.ntotal:
            kk = min(k, index.ntotal)
            s, n = index.search(vecs[i : i + 1], kk)
            sims[i, :kk], ids[i, :kk] = s[0], n[0]
        index.add(vecs[i : i + 1])
    return sims, ids
