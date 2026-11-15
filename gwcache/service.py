# live admission service: a small http api a gateway can call before going to a provider
import time
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd

from gwcache import acts, config, decision, embed, patterns


@dataclass
class Session:
    requests: list = field(default_factory=list)
    vecs: list = field(default_factory=list)
    acts: list = field(default_factory=list)
    intents: list = field(default_factory=list)


class Engine:
    # loads the frozen artifacts: encoder, intent centroids, act tagger, admission model and latest patterns
    def __init__(self, bundle_path, mined: dict):
        from sentence_transformers import SentenceTransformer

        cfg = config.load()
        b = joblib.load(bundle_path)
        self.model, self.cols, self.categories = b["model"], b["cols"], b["categories"]
        self.centers = embed.normalize(b["centers"].astype(np.float32))
        self.act_model = b["act_model"]
        self.encoder = SentenceTransformer(cfg["embedding"]["model"], cache_folder=cfg["paths"]["hf_cache"])
        self.mined = mined
        self.k, self.floor = cfg["candidates"]["top_k"], cfg["candidates"]["sim_floor"]
        self.cache_vecs = np.zeros((0, self.centers.shape[1]), dtype=np.float32)
        self.cache_meta: list[dict] = []
        self.sessions: dict[str, Session] = {}
        self.user_intents: dict[str, list] = {}

    # embeds one request
    def _vec(self, text: str) -> np.ndarray:
        return embed.normalize(self.encoder.encode([text], convert_to_numpy=True).astype(np.float32))[0]

    # tags the act of a request given its session, reusing the offline feature builder on a one-row frame
    def _act(self, s: Session, text: str, v: np.ndarray) -> str:
        frame = pd.DataFrame({"session_id": ["x"] * (len(s.requests) + 1), "turn_index": range(len(s.requests) + 1),
                              "request": s.requests + [text]})
        vecs = np.vstack(s.vecs + [v]) if s.vecs else v[None, :]
        x = acts.features(frame, vecs, acts.previous_requests(frame))
        return str(self.act_model.predict(x[-1:])[0])

    # decides whether to serve a cached answer for this request
    def admit(self, session_id: str, user_id: str, request: str) -> dict:
        t0 = time.perf_counter()
        s = self.sessions.setdefault(session_id, Session())
        v = self._vec(request)
        intent = int(np.argmax(self.centers @ v))
        act = self._act(s, request, v)
        result = {"serve": False, "intent": intent, "act": act}
        if len(self.cache_meta):
            sims = self.cache_vecs @ v
            top = np.argsort(-sims)[: self.k]
            top = top[sims[top] >= self.floor]
            if len(top):
                rows = self._features(s, user_id, request, v, intent, act, sims, top)
                score = decision.score_learned(self.model, rows, self.cols)
                best = int(np.argmax(score))
                result.update({"score": float(score[best]), "candidate": self.cache_meta[top[best]]["turn_id"]})
                if score[best] >= 0:
                    result.update({"serve": True, "answer": self.cache_meta[top[best]]["answer"]})
        result["latency_ms"] = (time.perf_counter() - t0) * 1000
        s.requests.append(request); s.vecs.append(v); s.acts.append(act); s.intents.append(intent)
        return result

    # adds a freshly answered request to the cache
    def record(self, session_id: str, user_id: str, turn_id: str, request: str, answer: str, act: str, intent: int) -> None:
        v = self._vec(request)
        self.cache_vecs = np.vstack([self.cache_vecs, v[None, :]])
        self.cache_meta.append({"turn_id": turn_id, "answer": answer, "session_id": session_id, "user_id": user_id,
                                "act": act, "intent": intent, "time": time.time(), "req_len": len(request), "ctx": self._ctx(self.sessions.get(session_id))})
        self.user_intents.setdefault(user_id, []).append(intent)

    # mean of the last two request vectors in a session (zeros when there is no history)
    def _ctx(self, s: Session | None) -> np.ndarray:
        if not s or not s.vecs:
            return np.zeros(self.centers.shape[1], dtype=np.float32)
        c = np.mean(s.vecs[-2:], axis=0)
        return c / (np.linalg.norm(c) or 1.0)

    # feature rows for the top candidates, matching the offline pair table columns
    def _features(self, s, user_id, request, v, intent, act, sims, top) -> pd.DataFrame:
        tau = config.load()["decision"]["softmax_temperature"]
        ctx = self._ctx(s)
        top_sims = np.r_[sims[top], [np.nan] * (3 - len(top))]
        soft = np.exp((sims[top] - sims[top][0]) / tau)
        uh = self.user_intents.get(user_id, [])[-10:]
        rows = []
        for r, ci in enumerate(top):
            m = self.cache_meta[ci]
            rows.append({
                "sim": sims[ci], "rank": r + 1, "turn_index": len(s.requests), "sim_1": top_sims[0], "sim_2": top_sims[1],
                "sim_3": top_sims[2], "sim_margin": top_sims[0] - np.nan_to_num(top_sims[1]), "sim_softmax": soft[r] / soft.sum(),
                "intent": intent, "cand_intent": m["intent"], "same_intent": int(intent == m["intent"]), "act": act,
                "cand_act": m["act"], "same_session": int(False), "same_user": int(user_id == m["user_id"]),
                "gap_days": (time.time() - m["time"]) / 86400, "log_gap": np.log1p(time.time() - m["time"]),
                "log_req_len": np.log1p(len(request)), "log_cand_req_len": np.log1p(m["req_len"]),
                "log_cand_ans_len": np.log1p(len(m["answer"])), "has_ctx": int(bool(s.vecs)),
                "ctx_sim": float(ctx @ m["ctx"]), "ctx_to_cand_req": float(ctx @ self.cache_vecs[ci]), "req_to_cand_ctx": float(v @ m["ctx"]),
                "pat_act_conf": patterns.confidence(self.mined["acts"], s.acts, act),
                "pat_dep_prior": patterns.dependent_prior(self.mined["acts"], s.acts),
                "pat_intent_conf": patterns.confidence(self.mined["intents"], s.intents, intent),
                "pat_cand_intent_conf": patterns.confidence(self.mined["intents"], s.intents, m["intent"]),
                "pat_cand_dep_prior": 0.0,
                "pat_freq_support": max([sup for items, sup in self.mined["itemsets"].items()
                                         if items <= {f"{i}:{a}" for i, a in zip(s.intents + [intent], s.acts + [act])}], default=0.0),
                "pat_freq_matches": 0,
                "pat_user_intent_conf": patterns.confidence(self.mined["user_intents"], uh, intent),
                "pat_user_cand_conf": patterns.confidence(self.mined["user_intents"], uh, m["intent"]),
            })
        df = pd.DataFrame(rows)
        for col, cats in self.categories.items():
            df[col] = pd.Categorical(df[col], categories=cats)
        return df


# builds the fastapi app around an engine
def create_app(engine: Engine):
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="gateway cache admission")

    class AdmitIn(BaseModel):
        session_id: str
        user_id: str
        request: str

    class RecordIn(AdmitIn):
        turn_id: str
        answer: str
        act: str = "new_request"
        intent: int = 0

    # serve-or-fresh decision for one request
    @app.post("/admit")
    def admit(body: AdmitIn):
        return engine.admit(body.session_id, body.user_id, body.request)

    # store a fresh provider answer in the cache
    @app.post("/record")
    def record(body: RecordIn):
        engine.record(body.session_id, body.user_id, body.turn_id, body.request, body.answer, body.act, body.intent)
        return {"cached": len(engine.cache_meta)}

    # liveness and cache size
    @app.get("/health")
    def health():
        return {"ok": True, "cached": len(engine.cache_meta)}

    return app
