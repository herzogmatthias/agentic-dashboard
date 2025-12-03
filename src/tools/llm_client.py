import time
from openai import OpenAI

from ..core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, SUMMARIZER_MODEL
from ..core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Summarizer Prompts (static methods for use by tools)
# ============================================================================


def get_output_summary_prompt() -> str:
    """
    Returns the prompt used for summarizing raw Python stdout/stderr output.
    
    This prompt instructs the summarizer to extract useful information for
    deciding the next analysis step, compressing large tables and verbose output.
    """
    return """
You are a summarizer for a data-analysis agent.

Input will be raw stdout/stderr from executing Python inside a sandbox.
This output may include:
- large tables
- pandas describe() output
- value_counts
- long numeric dumps
- warnings and tracebacks
- multiline logs

Your job:
1. Extract only information that is useful for deciding the next analysis step:
   - dataset shape (rows, columns)
   - dtypes or type hints
   - missingness patterns
   - potential ID columns
   - potential target/label columns
   - anomalies (negative values, extreme outliers, weird strings)
   - errors and exceptions (summarized)
2. Ignore or compress huge tables. Do NOT reproduce them.
3. Omit repetitive lines (like many warnings).
4. Keep the final summary under ~500 tokens.
5. Output using clear Markdown headings and bullet points.
6. Never invent details that are not in the input.

Do not return code. Do not return instructions. Only return the summarized content.

Now summarize this snippet:
"""


def get_snippet_summary_prompt() -> str:
    """
    Returns the prompt used for summarizing large text snippets.
    
    This prompt instructs the summarizer to preserve factual content
    without adding information or guessing missing parts.
    """
    return """
You are a summarizer for a data-analysis agent.
The following text excerpt is too large to return directly. 
Summarize it without adding information or guessing missing parts.

Rules:
- Preserve factual content only; do not infer beyond what is shown.
- Keep all technical details that describe structure, errors, stack traces, or code logic.
- When code appears, summarize its purpose, functions, and important branches.
- When logs appear, summarize the sequence of events, warnings, and errors.
- When JSON appears, summarize the structure (keys and types), not full values.
- If something is cut off or incomplete, explicitly state: "[truncated]" without filling in the missing content.

Output format:
- one short paragraph summary
- then bullet points with the most important technical findings
- no code unless necessary

Now summarize this snippet:
"""


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

