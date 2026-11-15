# intent clusters over request embeddings, fit on the training period only
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from gwcache import config


# fits k-means on training-period vectors and assigns every turn to its nearest centroid
def fit_assign(vecs: np.ndarray, is_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cfg = config.load()
    km = KMeans(n_clusters=cfg["intents"]["k"], random_state=cfg["seed"], n_init=10).fit(vecs[is_train])
    return km.predict(vecs), km.cluster_centers_


# names each cluster by its most distinctive words, for readable tables
def describe(requests: pd.Series, intent: np.ndarray, top_n: int = 6) -> pd.DataFrame:
    tfidf = TfidfVectorizer(max_features=20000, stop_words="english", min_df=3)
    x = tfidf.fit_transform(requests.str.slice(0, 500))
    words = np.array(tfidf.get_feature_names_out())
    rows = []
    for c in sorted(set(intent)):
        mask = intent == c
        mean = np.asarray(x[mask].mean(axis=0)).ravel() - np.asarray(x.mean(axis=0)).ravel()
        rows.append({"intent": int(c), "turns": int(mask.sum()), "top_words": ", ".join(words[np.argsort(-mean)[:top_n]]),
                     "example": requests[mask].iloc[0][:120].replace("\n", " ")})
    return pd.DataFrame(rows)
