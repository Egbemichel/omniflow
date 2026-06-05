"""Environment-backed configuration for the Form Service.

All config originates here (CLAUDE.md §9). Values are read lazily so tests can
override the environment before a value is consumed.
"""

import os


def get_gemini_api_key() -> str:
    """API key for the Gemini vision OCR call. Empty string when unset."""
    return os.getenv("GEMINI_API_KEY", "")


def get_gemini_model() -> str:
    """Gemini model id used for form field extraction.

    Defaults to gemini-2.5-flash. Do NOT fall back to gemini-2.0-flash — that
    model is being retired.
    """
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
