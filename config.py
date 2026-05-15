"""Backward-compatible imports for older local scripts.

The app's real configuration lives in :mod:`backend.core.config`.
"""

from backend.core.config import Settings, load_openai_api_key, load_settings


__all__ = ["Settings", "load_openai_api_key", "load_settings"]
