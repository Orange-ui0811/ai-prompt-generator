"""Tests for Pydantic data models."""

import json
import tempfile
from pathlib import Path
import pytest
from src.models import (
    ProjectProfile,
    StageDefinition,
    GeneratedPrompt,
    GenerationResult,
)


class TestProjectProfile:
    def test_full_profile(self, full_profile):
        assert full_profile.project_goal == "构建一个电商推荐系统"
        assert full_profile.current_task == "实现协同过滤推荐算法"
        assert full_profile.is_empty() is False
        assert full_profile.filled_field_count() == 9

    def test_partial_profile(self, partial_profile):
        assert partial_profile.filled_field_count() == 3
        assert partial_profile.is_empty() is False

    def test_empty_profile(self, empty_profile):
        assert empty_profile.is_empty() is True
        assert empty_profile.filled_field_count() == 0
        # All fields should default to empty string
        for f in empty_profile.model_fields:
            assert getattr(empty_profile, f) == ""

    def test_to_template_vars_excludes_empty(self, empty_profile):
        """Empty fields should not appear in template vars, only has_any_context."""
        vars_ = empty_profile.to_template_vars()
        assert vars_ == {"has_any_context": False}

    def test_to_template_vars_includes_filled(self, partial_profile):
        """Only filled fields should appear."""
        vars_ = partial_profile.to_template_vars()
        assert "project_goal" in vars_
        assert "current_task" in vars_
        assert "impact_scope" in vars_
        assert "known_issues" not in vars_

    def test_save_and_load_roundtrip(self, full_profile):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            full_profile.save(f.name)
            path = f.name

        try:
            loaded = ProjectProfile.load(path)
            assert loaded == full_profile
        finally:
            Path(path).unlink()

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            ProjectProfile.load("/nonexistent/path/profile.json")


class TestStageDefinition:
    def test_valid_definition(self):
        sd = StageDefinition(
            id=0,
            name="提供项目背景与上下文",
            name_en="context",
            description="先给我最关键的上下文",
            key_points=["点1", "点2"],
            template_file="stage_00_context.j2",
            has_user_variables=True,
            user_variable_fields=["project_goal"],
        )
        assert sd.id == 0
        assert len(sd.key_points) == 2

    def test_defaults(self):
        sd = StageDefinition(
            id=5,
            name="TDD",
            name_en="tdd",
            description="测试驱动开发",
            template_file="stage_05_tdd.j2",
        )
        assert sd.key_points == []
        assert sd.has_user_variables is False
        assert sd.user_variable_fields == []


class TestGeneratedPrompt:
    def test_construction(self, full_profile):
        gp = GeneratedPrompt(
            stage_id=0,
            stage_name="测试阶段",
            prompt_text="这是生成后的提示词文本",
            profile_snapshot=full_profile.model_dump(),
        )
        assert gp.stage_id == 0
        assert "提示词文本" in gp.prompt_text
        assert gp.rendered_at  # auto-generated timestamp


class TestGenerationResult:
    def test_construction(self, full_profile):
        prompts = [
            GeneratedPrompt(
                stage_id=0,
                stage_name="阶段0",
                prompt_text="test",
            ),
        ]
        result = GenerationResult(profile=full_profile, prompts=prompts)
        assert len(result.prompts) == 1
        assert result.generated_at  # auto-generated timestamp
