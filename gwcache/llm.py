# groq chat client with an on-disk response cache, rate-limit waits and retries
import hashlib
import json
import os
import time

from gwcache import config


# stable cache key for one request, so re-runs never pay for the same call twice
def cache_key(model: str, system: str, user: str, params: dict) -> str:
    blob = json.dumps({"model": model, "system": system, "user": user, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# where a cached response for this key lives
def _cache_file(model: str, key: str):
    folder = config.path("llm_cache") / model.replace("/", "_")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{key}.json"


# seconds to wait after a 429, read from retry-after when groq sends it
def _retry_after(err) -> float:
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    try:
        return float(headers.get("retry-after", 60)) + 2
    except (TypeError, ValueError):
        return 62.0


class Client:
    # lazily builds the groq client from GROQ_API_KEY
    def __init__(self):
        from groq import Groq
        self.groq = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.calls = 0
        self.tokens = 0

    # one json-mode chat call, served from disk cache when possible, waiting out rate limits
    def json_call(self, model: str, system: str, user: str, max_tokens: int = 3000, log=print) -> dict:
        from groq import APIConnectionError, APIStatusError, RateLimitError

        params = {"temperature": 0, "max_tokens": max_tokens}
        if "gpt-oss" in model:
            params["reasoning_effort"] = "low"
        key = cache_key(model, system, user, params)
        cached = _cache_file(model, key)
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))["content"]

        while True:
            try:
                resp = self.groq.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0,
                    max_completion_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    **({"reasoning_effort": "low"} if "gpt-oss" in model else {}),
                )
                content = json.loads(resp.choices[0].message.content)
                usage = {"prompt": resp.usage.prompt_tokens, "completion": resp.usage.completion_tokens}
                cached.write_text(json.dumps({"content": content, "usage": usage}), encoding="utf-8")
                self.calls += 1
                self.tokens += usage["prompt"] + usage["completion"]
                return content
            except RateLimitError as err:
                wait = _retry_after(err)
                log(f"rate limited on {model}, waiting {wait:.0f}s")
                time.sleep(wait)
            except APIStatusError as err:
                # client-side mistakes (bad params, bad model) will not fix themselves, so stop instead of looping
                if 400 <= err.status_code < 500:
                    raise
                log(f"server error {err.status_code}, retrying in 15s")
                time.sleep(15)
            except (APIConnectionError, json.JSONDecodeError) as err:
                log(f"llm error, retrying in 15s: {str(err)[:120]}")
                time.sleep(15)
