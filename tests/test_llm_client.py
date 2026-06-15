"""Tests for LLM client, config, and engine LLM integration."""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.models import LLMConfig, ProjectProfile, StageDefinition
from src.engine import PromptGenerator


# ── LLMConfig tests ──────────────────────────────────────────────────


class TestLLMConfig:
    def test_empty_config_is_not_ready(self):
        config = LLMConfig()
        assert config.is_ready() is False

    def test_full_config_is_ready(self):
        config = LLMConfig(
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        assert config.is_ready() is True

    def test_missing_key_not_ready(self):
        config = LLMConfig(
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        assert config.is_ready() is False

    def test_from_env_reads_variables(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-env-test")
        monkeypatch.setenv("LLM_BASE_URL", "https://custom.api.com/v1")
        monkeypatch.setenv("LLM_MODEL", "custom-model")

        config = LLMConfig.from_env()
        assert config.api_key == "sk-env-test"
        assert config.base_url == "https://custom.api.com/v1"
        assert config.model == "custom-model"
        assert config.enabled is True

    def test_from_env_empty_when_vars_missing(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        config = LLMConfig.from_env()
        assert config.api_key == ""
        assert config.enabled is False

    def test_enabled_false_when_no_key(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setenv("LLM_BASE_URL", "https://x.com/v1")
        monkeypatch.setenv("LLM_MODEL", "m")
        config = LLMConfig.from_env()
        assert config.enabled is False


# ── LLMClient tests (mocked OpenAI) ──────────────────────────────────


class TestLLMClientGeneration:
    @pytest.fixture
    def profile(self):
        return ProjectProfile(
            project_goal="构建电商推荐系统",
            current_task="实现协同过滤算法",
        )

    @pytest.fixture
    def stage_def(self):
        return StageDefinition(
            id=5,
            name="测试驱动开发",
            name_en="tdd",
            description="优先测试驱动",
            key_points=["先写测试", "最小实现"],
            template_file="stage_05_tdd.j2",
        )

    @pytest.fixture
    def llm_config(self):
        return LLMConfig(
            api_key="sk-test",
            base_url="https://api.test.com/v1",
            model="test-model",
            enabled=True,
        )

    def test_generate_prompt_returns_text(self, llm_config, stage_def, profile):
        """Mocked OpenAI call returns a valid prompt string."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "这是 AI 生成的测试驱动开发提示词"
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[mock_choice]
            )
            mock_openai.return_value = mock_client

            from src.llm.client import LLMClient
            client = LLMClient(llm_config)
            result = client.generate_prompt(stage_def, profile)

            assert "测试驱动开发" in result
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_prompt_handles_empty_response(self, llm_config, stage_def, profile):
        """LLM returns None content → should raise LLMError."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = None
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[mock_choice]
            )
            mock_openai.return_value = mock_client

            from src.llm.client import LLMClient, LLMError
            client = LLMClient(llm_config)
            with pytest.raises(LLMError, match="empty response"):
                client.generate_prompt(stage_def, profile)

    def test_generate_401_raises_friendly_error(self, llm_config, stage_def, profile):
        """401 should raise LLMError with Chinese message about API key."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception(
                "401 Unauthorized"
            )
            mock_openai.return_value = mock_client

            from src.llm.client import LLMClient, LLMError
            client = LLMClient(llm_config)
            with pytest.raises(LLMError, match="API Key"):
                client.generate_prompt(stage_def, profile)

    def test_generate_404_raises_model_error(self, llm_config, stage_def, profile):
        """404 should raise LLMError about model name."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception(
                "404 model_not_found"
            )
            mock_openai.return_value = mock_client

            from src.llm.client import LLMClient, LLMError
            client = LLMClient(llm_config)
            with pytest.raises(LLMError, match="模型不可用"):
                client.generate_prompt(stage_def, profile)


# ── Engine LLM integration tests ─────────────────────────────────────


class TestEngineWithLLM:
    @pytest.fixture
    def gen(self, templates_dir, config_dir):
        return PromptGenerator(templates_dir=templates_dir, config_dir=config_dir)

    @pytest.fixture
    def profile(self):
        return ProjectProfile(
            project_goal="修复登录超时",
            current_task="排查 session 过期问题",
        )

    def test_generate_single_falls_back_to_template_on_llm_error(
        self, gen, profile
    ):
        """When LLM raises error, engine should fall back to template."""
        mock_llm = MagicMock()
        mock_llm.generate_prompt.side_effect = Exception("Connection timeout")

        prompt = gen.generate_single(profile, 5, mode="standalone", llm_client=mock_llm)

        assert prompt is not None
        assert prompt.generation_method == "template"
        assert prompt.stage_id == 5

    def test_generate_single_uses_llm_when_available(self, gen, profile):
        """LLM success → returns LLM-generated prompt."""
        mock_llm = MagicMock()
        mock_llm.generate_prompt.return_value = "AI 生成的 TDD 提示词"

        prompt = gen.generate_single(profile, 5, mode="standalone", llm_client=mock_llm)

        assert prompt.generation_method == "llm"
        assert prompt.prompt_text == "AI 生成的 TDD 提示词"

    def test_generate_single_skips_llm_in_pure_mode(self, gen, profile):
        """Pure mode should never call LLM."""
        mock_llm = MagicMock()

        prompt = gen.generate_single(profile, 5, mode="pure", llm_client=mock_llm)

        mock_llm.generate_prompt.assert_not_called()
        assert prompt.generation_method == "template"

    def test_generate_single_skips_llm_when_none(self, gen, profile):
        """When llm_client is None, should use template."""
        prompt = gen.generate_single(profile, 5, mode="standalone", llm_client=None)

        assert prompt.generation_method == "template"
        assert "测试驱动思路" in prompt.prompt_text

    def test_generate_all_mixed_llm_and_template(self, gen, profile):
        """Some stages succeed with LLM, others fall back."""
        mock_llm = MagicMock()
        # Succeed for stage 0, fail for all others
        def side_effect(stage_def, prof):
            if stage_def.id == 0:
                return "AI: 项目背景提示词"
            raise Exception("fail")
        mock_llm.generate_prompt.side_effect = side_effect

        result = gen.generate_all(profile, mode="standalone", llm_client=mock_llm)

        llm_count = sum(1 for p in result.prompts if p.generation_method == "llm")
        template_count = sum(1 for p in result.prompts if p.generation_method == "template")

        assert llm_count == 1  # only stage 0 succeeded
        assert template_count == 13  # rest fell back
        assert len(result.prompts) == 14

    def test_generated_prompt_has_generation_method_field(self, gen, profile):
        """All GeneratedPrompts should have the generation_method field."""
        prompt = gen.generate_single(profile, 0)
        assert hasattr(prompt, "generation_method")
        assert prompt.generation_method in ("llm", "template")


# ── System prompt builder tests ──────────────────────────────────────


class TestSystemPromptBuilder:
    def test_build_system_prompt_includes_key_info(self):
        from src.llm.prompts import build_system_prompt

        sd = StageDefinition(
            id=3,
            name="明确约束",
            name_en="constraints",
            description="识别约束和风险",
            key_points=["技术约束", "业务约束", "非目标"],
            template_file="stage_03_constraints.j2",
        )
        profile = ProjectProfile(
            project_goal="构建推荐系统",
            current_task="实现协同过滤",
        )
        result = build_system_prompt(sd, profile=profile)
        assert "明确约束" in result
        assert "识别约束和风险" in result
        assert "技术约束" in result
        assert "业务约束" in result
        assert "非目标" in result
        assert "构建推荐系统" in result  # project should be prominent
        assert "项目信息" in result

    def test_build_system_prompt_empty_key_points(self):
        from src.llm.prompts import build_system_prompt

        sd = StageDefinition(
            id=1,
            name="理解需求",
            name_en="understand",
            description="识别真实目标",
            key_points=[],
            template_file="stage_01_understand.j2",
        )
        result = build_system_prompt(sd, profile=None)
        assert "专业判断" in result  # empty key_points hint

    def test_build_user_prompt_includes_profile(self):
        from src.llm.prompts import build_user_prompt

        profile = ProjectProfile(
            project_goal="修复登录超时",
            current_task="排查 session 过期",
        )
        sd = StageDefinition(
            id=1,
            name="理解需求",
            name_en="understand",
            description="识别真实目标",
            key_points=[],
            template_file="stage_01_understand.j2",
        )
        result = build_user_prompt(profile, sd)
        assert "修复登录超时" in result
        assert "排查 session 过期" in result
        assert "理解需求" in result
        # Should contain profile info in compact format
        assert "修复登录超时" in result
        assert "排查 session 过期" in result
