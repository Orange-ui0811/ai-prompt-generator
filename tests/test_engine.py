"""Tests for the core PromptGenerator engine."""

import pytest
from src.models import ProjectProfile
from src.engine import PromptGenerator


@pytest.fixture
def gen(templates_dir, config_dir):
    return PromptGenerator(templates_dir=templates_dir, config_dir=config_dir)


class TestGenerateSingle:
    def test_stage_0_standalone(self, gen, full_profile):
        prompt = gen.generate_single(full_profile, 0, mode="standalone")
        assert prompt.stage_id == 0
        assert "提供项目背景与上下文" in prompt.stage_name
        assert "构建一个电商推荐系统" in prompt.prompt_text
        assert prompt.profile_snapshot

    def test_stage_0_pure(self, gen, full_profile):
        """Stage 0 in pure mode still gets profile (it has explicit variables)."""
        prompt = gen.generate_single(full_profile, 0, mode="pure")
        assert "构建一个电商推荐系统" in prompt.prompt_text

    def test_stage_5_standalone(self, gen, full_profile):
        prompt = gen.generate_single(full_profile, 5, mode="standalone")
        assert prompt.stage_id == 5
        assert "构建一个电商推荐系统" in prompt.prompt_text  # context injected

    def test_stage_5_pure(self, gen, empty_profile):
        """Pure mode should NOT inject profile context for stages 1-13."""
        prompt = gen.generate_single(empty_profile, 5, mode="pure")
        assert "测试驱动思路" in prompt.prompt_text
        assert "## 当前项目上下文" not in prompt.prompt_text

    def test_invalid_stage_id(self, gen, empty_profile):
        with pytest.raises(KeyError):
            gen.generate_single(empty_profile, 99)

    def test_invalid_mode(self, gen, empty_profile):
        with pytest.raises(ValueError):
            gen.generate_single(empty_profile, 0, mode="invalid")

    def test_stage_13(self, gen, full_profile):
        prompt = gen.generate_single(full_profile, 13, mode="standalone")
        assert prompt.stage_id == 13
        assert "CI" in prompt.prompt_text or "部署" in prompt.prompt_text


class TestGenerateAll:
    def test_all_14_stages(self, gen, empty_profile):
        result = gen.generate_all(empty_profile)
        assert len(result.prompts) == 14
        ids = [p.stage_id for p in result.prompts]
        assert ids == list(range(14))

    def test_all_with_profile(self, gen, partial_profile):
        result = gen.generate_all(partial_profile)
        assert len(result.prompts) == 14
        assert result.profile == partial_profile

    def test_all_pure_mode(self, gen, empty_profile):
        result = gen.generate_all(empty_profile, mode="pure")
        assert len(result.prompts) == 14
        # Stage 5 in pure mode should not have context header
        stage5 = result.prompts[5]
        assert "## 当前项目上下文" not in stage5.prompt_text


class TestGenerateMaster:
    def test_master_with_profile(self, gen, full_profile):
        prompt = gen.generate_master(full_profile)
        assert prompt.stage_id == -1
        assert "总提示词" in prompt.stage_name
        assert "构建一个电商推荐系统" in prompt.prompt_text
        assert "执行要求" in prompt.prompt_text

    def test_master_empty_profile(self, gen, empty_profile):
        prompt = gen.generate_master(empty_profile)
        assert len(prompt.prompt_text) > 0


class TestGenerateSubset:
    def test_subset_three_stages(self, gen, empty_profile):
        result = gen.generate_subset(empty_profile, [0, 7, 13])
        assert len(result.prompts) == 3
        ids = [p.stage_id for p in result.prompts]
        assert ids == [0, 7, 13]

    def test_subset_invalid_id(self, gen, empty_profile):
        with pytest.raises(KeyError):
            gen.generate_subset(empty_profile, [0, 99])


class TestModesDifference:
    """Verify standalone and pure modes produce different output."""

    def test_modes_differ_for_stage_1_to_13(self, gen, full_profile, empty_profile):
        for sid in range(1, 14):
            standalone = gen.generate_single(full_profile, sid, mode="standalone")
            pure = gen.generate_single(empty_profile, sid, mode="pure")
            # standalone should have more content (context injected)
            assert len(standalone.prompt_text) >= len(pure.prompt_text)
