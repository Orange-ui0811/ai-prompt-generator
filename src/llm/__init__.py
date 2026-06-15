"""LLM enhancement layer for the AI Project Prompt Generator.

Provides LLMClient for calling OpenAI-compatible APIs and LLMEnhancer
as a high-level wrapper with automatic fallback to template rendering.
"""

from .client import LLMClient, LLMError
from .prompts import build_system_prompt, build_user_prompt

__all__ = ["LLMClient", "LLMError", "build_system_prompt", "build_user_prompt"]
