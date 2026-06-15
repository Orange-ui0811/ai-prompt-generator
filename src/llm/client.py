"""LLM client for OpenAI-compatible APIs.

Wraps the openai SDK with retry, timeout, and graceful fallback support.
"""

import logging
from ..models import LLMConfig, StageDefinition, ProjectProfile
from .prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM call fails in a non-recoverable way."""


class LLMClient:
    """Thin wrapper around the OpenAI SDK for generating prompts.

    Usage:
        config = LLMConfig.from_env()
        if config.is_ready():
            client = LLMClient(config)
            prompt_text = client.generate_prompt(stage_def, profile)
    """

    def __init__(self, config: LLMConfig):
        if not config.is_ready():
            raise LLMError("LLMConfig is not ready: missing api_key, base_url, or model")
        self.config = config
        self._client = None  # lazily initialized

    def _get_client(self):
        """Lazy-import and initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise LLMError(
                    "openai package is not installed. Run: pip install openai"
                )
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=30.0,
            )
        return self._client

    def generate_prompt(
        self,
        stage_def: StageDefinition,
        profile: ProjectProfile,
    ) -> str:
        """Generate a customized prompt for a single stage using the LLM.

        Args:
            stage_def: Stage definition (name, description, key points).
            profile: User's project profile.

        Returns:
            Generated prompt text.

        Raises:
            LLMError: If the API call fails (non-recoverable) or times out.
        """
        system_prompt = build_system_prompt(stage_def, profile=profile)
        user_prompt = build_user_prompt(profile, stage_def)

        logger.info(
            "LLM request — stage=%s, profile_fields_filled=%d/%d, "
            "project_goal=%r, current_task=%r, impact_scope=%r",
            stage_def.name,
            profile.filled_field_count(), 9,
            profile.project_goal, profile.current_task, profile.impact_scope,
        )

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("LLM returned empty response")
            return content.strip()

        except ImportError:
            raise LLMError("openai package is not installed. Run: pip install openai")
        except Exception as e:
            # Re-raise as LLMError for upstream handling
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise LLMError(f"API Key 认证失败，请检查您的 API Key: {e}")
            elif "404" in error_msg or "Not Found" in error_msg or "model_not_found" in error_msg:
                raise LLMError(f"模型不可用，请检查 model 名称和 base_url: {e}")
            elif "429" in error_msg or "Rate limit" in error_msg:
                raise LLMError(f"请求频率超限，请稍后重试: {e}")
            else:
                raise LLMError(f"LLM 调用失败: {e}")

    def test_connection(self) -> bool:
        """Test if the LLM connection is working.

        Returns:
            True if a simple API call succeeds, False otherwise.
        """
        try:
            client = self._get_client()
            client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0,
            )
            return True
        except Exception as e:
            logger.warning("LLM connection test failed: %s", e)
            return False
