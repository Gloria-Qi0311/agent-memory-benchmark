"""DeepSeek LLM wrapper. One thin client used by both agents and the judge.

Includes exponential backoff retry for transient errors (429, 5xx, network
hiccups). The benchmark makes ~100s of API calls per run, and one transient
failure shouldn't kill the whole experiment.
"""
import os
import time
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)
_model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

_RETRYABLE = (APIError, APIConnectionError, RateLimitError)
_MAX_ATTEMPTS = 3


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
        except _RETRYABLE as e:
            last_exc = e
            if attempt == _MAX_ATTEMPTS - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s
    # Unreachable, but keeps the type checker quiet.
    raise last_exc  # type: ignore[misc]
