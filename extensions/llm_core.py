"""
Common Gemini LLM utilities shared across prompt modules.
"""
import json
import re
import time
from typing import Any, Dict

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from config import GEMINI_API_KEY, GEMINI_MODEL

# Configure Gemini client once
genai.configure(api_key=GEMINI_API_KEY)

LLM = genai.GenerativeModel(
    GEMINI_MODEL,
    generation_config=GenerationConfig(response_mime_type="application/json")
)


def safe_parse_llm_output(raw: str) -> Dict[str, Any]:
    """
    Safely parse LLM output as JSON.
    Removes markdown code fences and fixes escape characters.

    Args:
        raw: Raw LLM output string

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If JSON parsing fails
    """
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    cleaned = re.sub(r'(?<!\\)\\(?![\\"])', r'\\\\', cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Cannot parse LLM output as JSON: {e}\nRaw output: {raw}")


def call_llm_json(prompt: str, max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
    """
    Call LLM with JSON mode and parse response safely.

    Args:
        prompt: Prompt text
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)

    Returns:
        Parsed JSON dictionary

    Raises:
        Exception: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            response = LLM.generate_content(prompt)
            raw = (response.text or "").strip()
            if not raw:
                raise ValueError("Empty response from LLM")
            return safe_parse_llm_output(raw)
        except Exception as error:  # noqa: BLE001 - capture all to retry
            last_error = error
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise last_error

    raise last_error

