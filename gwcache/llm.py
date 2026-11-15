# llm client for groq and claude (via the gateway), with an on-disk response cache, rate-limit waits and retries
import hashlib
import json
import os
import re
import threading
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


# lowest reasoning setting each model family accepts, to keep token use down
def reasoning_effort(model: str) -> str | None:
    if "gpt-oss" in model or model.startswith("claude"):
        return "low"
    if "qwen" in model:
        return "none"
    return None


# seconds to wait after a 429, read from retry-after when the server sends it
def _retry_after(err) -> float:
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    try:
        return float(headers.get("retry-after", 30)) + 2
    except (TypeError, ValueError):
        return 32.0


# pulls the first json object out of a reply, tolerating code fences or stray text around it
def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start : end + 1])


# reads the gateway key from the environment or the repo's .env file
def _gateway_key() -> str:
    from dotenv import load_dotenv

    load_dotenv(config.ROOT / ".env")
    key = os.environ.get(config.load()["gateway"]["key_env"], "").strip()
    if not key:
        raise RuntimeError("gateway key missing: put AICREDITS_API_KEY=... in .env")
    return key


# raised when the model declines a request, so callers can split the batch and isolate the cause
class Refusal(Exception):
    pass


# runs fn on a batch; on a refusal it retries each half, so only the items that trigger it are dropped (reply None)
def call_splitting(batch: list, fn) -> list[tuple[list, dict | None]]:
    try:
        return [(batch, fn(batch))]
    except Refusal:
        if len(batch) == 1:
            return [(batch, None)]
        mid = len(batch) // 2
        return call_splitting(batch[:mid], fn) + call_splitting(batch[mid:], fn)


class Client:
    # builds provider clients lazily and keeps simple usage counters
    def __init__(self):
        self._groq = None
        self._claude = None
        self.lock = threading.Lock()
        self.calls = 0
        self.tokens = {"input": 0, "output": 0}

    # groq client from GROQ_API_KEY
    def groq(self):
        if self._groq is None:
            from groq import Groq
            self._groq = Groq(api_key=os.environ["GROQ_API_KEY"])
        return self._groq

    # anthropic sdk client pointed at the gateway with bearer auth
    def claude(self):
        if self._claude is None:
            import anthropic
            self._claude = anthropic.Anthropic(base_url=config.load()["gateway"]["base_url"], api_key=None,
                                               auth_token=_gateway_key(), max_retries=4)
        return self._claude

    # one json-producing call, served from disk cache when possible, waiting out rate limits
    def json_call(self, model: str, system: str, user: str, max_tokens: int = 3000, log=print) -> dict:
        params = {"temperature": 0, "max_tokens": max_tokens}
        effort = reasoning_effort(model)
        if effort:
            params["reasoning_effort"] = effort
        key = cache_key(model, system, user, params)
        cached = _cache_file(model, key)
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))["content"]

        call = self._claude_call if model.startswith("claude") else self._groq_call
        content, usage, served_by = call(model, system, user, max_tokens, effort, log)
        cached.write_text(json.dumps({"content": content, "usage": usage, "served_by": served_by}), encoding="utf-8")
        with self.lock:
            self.calls += 1
            self.tokens["input"] += usage["input"]
            self.tokens["output"] += usage["output"]
        return content

    # groq chat completion in json mode
    def _groq_call(self, model, system, user, max_tokens, effort, log):
        from groq import APIConnectionError, APIStatusError, RateLimitError

        while True:
            try:
                resp = self.groq().chat.completions.create(
                    model=model, temperature=0, max_completion_tokens=max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format={"type": "json_object"}, **({"reasoning_effort": effort} if effort else {}),
                )
                usage = {"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens}
                return json.loads(resp.choices[0].message.content), usage, resp.model
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

    # claude messages call through the gateway; the answer is the text block after any thinking
    def _claude_call(self, model, system, user, max_tokens, effort, log):
        import anthropic

        for _ in range(6):
            try:
                resp = self.claude().messages.create(
                    model=model, max_tokens=max_tokens, system=system,
                    messages=[{"role": "user", "content": user}], output_config={"effort": effort},
                )
                text = "".join(b.text for b in resp.content if b.type == "text")
                if resp.stop_reason == "refusal":
                    raise Refusal(model)
                if resp.stop_reason == "max_tokens" and not text.strip():
                    max_tokens *= 2
                    log(f"{model} ran out of tokens before answering, retrying with {max_tokens}")
                    continue
                usage = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
                return parse_json(text), usage, resp.model
            except anthropic.RateLimitError as err:
                wait = _retry_after(err)
                log(f"rate limited on {model}, waiting {wait:.0f}s")
                time.sleep(wait)
            except (json.JSONDecodeError, ValueError) as err:
                log(f"unparseable reply from {model}, retrying: {str(err)[:80]}")
            except anthropic.APIStatusError as err:
                if 400 <= err.status_code < 500:
                    raise
                log(f"server error {err.status_code}, retrying in 15s")
                time.sleep(15)
            except anthropic.APIConnectionError as err:
                log(f"connection error, retrying in 15s: {str(err)[:80]}")
                time.sleep(15)
        raise RuntimeError(f"{model}: no usable reply after retries")
