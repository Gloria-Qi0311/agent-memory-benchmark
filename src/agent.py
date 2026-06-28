"""DeepSeek LLM wrapper. One thin client used by both agents and the judge."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)
_model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def chat(system: str, user: str, temperature: float = 0.2) -> str:
    resp = _client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
