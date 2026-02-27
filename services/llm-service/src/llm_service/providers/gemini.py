"""Google Gemini API provider."""
import asyncio
import os
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini API integration using the fast Flash model."""

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 15  # Keep total retry time under httpx timeout

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY is missing!")
            raise ValueError("GEMINI_API_KEY is missing")

        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.0-flash"

    async def complete(self, messages: list) -> str:
        system_prompt = next(
            (m["content"] for m in messages if m.get("role") == "system"), ""
        )
        user_prompt = "\n".join(
            [m["content"] for m in messages if m.get("role") != "system"]
        )

        logger.info(
            f"Sending request to Gemini model={self.model_name} "
            f"(System prompt length: {len(system_prompt)})"
        )

        # Configure model with system instruction
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await model.generate_content_async(user_prompt)

                if not response.text:
                    logger.warning("Gemini returned an empty response.")
                    return "{}"

                return response.text

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit / quota error
                if "429" in str(e) or "quota" in error_str or "resource_exhausted" in error_str:
                    wait = self.RETRY_DELAY_SECONDS * attempt
                    logger.warning(
                        f"Gemini rate limited (attempt {attempt}/{self.MAX_RETRIES}). "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                    continue
                else:
                    # Non-retryable error
                    logger.error(f"GEMINI CRITICAL ERROR: {str(e)}", exc_info=True)
                    raise

        # All retries exhausted
        logger.error(f"Gemini rate limit: all {self.MAX_RETRIES} retries exhausted")
        raise last_error