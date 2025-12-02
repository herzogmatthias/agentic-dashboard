import time
from openai import OpenAI

from ..core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, SUMMARIZER_MODEL
from ..core.logging import get_logger

logger = get_logger(__name__)


class Summarizer:
    def __init__(self) -> None:
        self._client = None
        if OPENROUTER_API_KEY:
            self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)

    def summarize(self, text: str, system_prompt: str, max_tokens: int = 512) -> str:
        if not self._client:
            raise RuntimeError("OPENROUTER_API_KEY not configured; cannot summarize.")
        
        combined_prompt = system_prompt + "\n\n" + text

        # Retry settings
        max_attempts = 5
        backoff = 1  # start with 1 second

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=SUMMARIZER_MODEL,
                    extra_body={"reasoning": {"enabled": False}},
                    messages=[
                        {"role": "user", "content": combined_prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.1,
                )
                return resp.choices[0].message.content or ""
            
            except Exception as exc:
                if attempt == max_attempts:
                    # Final failure → return raw text
                    logger.error("Summarizer failed after max attempts", extra={"attempts": attempt, "error": str(exc)})
                    return text
                
                logger.warning("Summarizer error, retrying", extra={"attempt": attempt, "backoff_seconds": backoff, "error": str(exc)})

                time.sleep(backoff)
                backoff *= 2  # exponential backoff

        # Should never happen, fallback
        return text

