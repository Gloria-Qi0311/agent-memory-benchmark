"""DeepSeek LLM wrapper. One thin client used by both agents and the judge.

Includes exponential backoff retry for transient errors (429, 5xx, network
hiccups). The benchmark makes ~100s of API calls per run, and one transient
failure shouldn't kill the whole experiment.
"""
import os
import random
import time
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, APIStatusError, RateLimitError

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    # Keep retries in this wrapper so attempts and backoff are observable and
    # do not multiply with the SDK's own hidden retry loop.
    max_retries=0,
    timeout=float(os.environ.get("DEEPSEEK_TIMEOUT_SECONDS", "60")),
)
_model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

_MAX_ATTEMPTS = int(os.environ.get("DEEPSEEK_MAX_ATTEMPTS", "6"))
_BASE_DELAY_SECONDS = float(os.environ.get("DEEPSEEK_RETRY_BASE_SECONDS", "1"))
_MAX_DELAY_SECONDS = float(os.environ.get("DEEPSEEK_RETRY_MAX_SECONDS", "16"))


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (APIConnectionError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {408, 409, 429} or exc.status_code >= 500
    return False


def chat(system: str, user: str, temperature: float = 0.2) -> str:
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = _client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt == _MAX_ATTEMPTS - 1:
                raise
            delay = min(_MAX_DELAY_SECONDS, _BASE_DELAY_SECONDS * (2 ** attempt))
            # A small jitter prevents concurrent benchmark workers from
            # reconnecting through the same proxy at exactly the same time.
            time.sleep(delay * random.uniform(0.8, 1.2))
    # Unreachable, but keeps the type checker quiet.
    raise last_exc  # type: ignore[misc]
