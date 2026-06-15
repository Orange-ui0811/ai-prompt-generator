"""Edge case tests for the prompt generator."""

import pytest
from src.models import ProjectProfile
from src.engine import PromptGenerator


@pytest.fixture
def gen(templates_dir, config_dir):
    return PromptGenerator(templates_dir=templates_dir, config_dir=config_dir)


class TestSpecialCharacters:
    """Profile fields with special characters should render safely."""

    def test_quotes_in_profile(self, gen):
        profile = ProjectProfile(
            project_goal='构建"智能"推荐系统',
            current_task="实现 O(n) 的排序 && 过滤",
        )
        prompt = gen.generate_single(profile, 0)
        assert '"智能"' in prompt.prompt_text
        assert "&&" in prompt.prompt_text

    def test_angle_brackets(self, gen):
        profile = ProjectProfile(
            project_goal="测试 <important> 标签",
            current_task="处理 <div> 渲染",
        )
        # Jinja2 auto-escapes HTML by default? No — with FileSystemLoader
        # autoescape defaults to False for .j2 files. But this is a text
        # generator, not HTML, so brackets should pass through.
        prompt = gen.generate_single(profile, 0)
        assert "<important>" in prompt.prompt_text
        assert "<div>" in prompt.prompt_text

    def test_sql_injection_like_input(self, gen):
        profile = ProjectProfile(
            current_task="DROP TABLE users; -- malicious",
        )
        prompt = gen.generate_single(profile, 0)
        # Should be rendered as plain text, not executed
        assert "DROP TABLE users" in prompt.prompt_text

    def test_newlines_in_profile_field(self, gen):
        profile = ProjectProfile(
            known_issues="问题1: 超时\n问题2: 内存泄漏\n问题3: 死锁",
        )
        prompt = gen.generate_single(profile, 0)
        assert "问题1: 超时" in prompt.prompt_text
        assert "问题2: 内存泄漏" in prompt.prompt_text


class TestLongText:
    def test_very_long_field(self, gen):
        long_text = "这是一个非常长的项目描述。" * 500
        profile = ProjectProfile(project_goal=long_text)
        prompt = gen.generate_single(profile, 0)
        assert len(prompt.prompt_text) > 500
        # Should still contain the template structure
        assert "协作开发者" in prompt.prompt_text

    def test_chinese_long_text(self, gen):
        long_cn = "项目目标是构建一个高性能、高可用、可扩展的分布式微服务架构系统。" * 200
        profile = ProjectProfile(current_task=long_cn)
        prompt = gen.generate_single(profile, 0)
        # Verify Chinese characters are preserved
        assert "微服务" in prompt.prompt_text


class TestRegeneration:
    def test_edit_and_regenerate(self, gen):
        profile_v1 = ProjectProfile(current_task="任务A")
        p1 = gen.generate_single(profile_v1, 0)
        assert "任务A" in p1.prompt_text

        profile_v2 = ProjectProfile(current_task="任务B")
        p2 = gen.generate_single(profile_v2, 0)
        assert "任务B" in p2.prompt_text
        assert "任务A" not in p2.prompt_text

    def test_profile_snapshots_differ(self, gen):
        """Each GeneratedPrompt should capture the profile used."""
        p1 = gen.generate_single(
            ProjectProfile(current_task="v1"), 0
        )
        p2 = gen.generate_single(
            ProjectProfile(current_task="v2"), 0
        )
        assert p1.profile_snapshot["current_task"] == "v1"
        assert p2.profile_snapshot["current_task"] == "v2"


class TestEmptyFields:
    def test_single_field_filled(self, gen):
        """Only current_task filled, everything else empty."""
        profile = ProjectProfile(current_task="修复登录超时")
        prompt = gen.generate_single(profile, 0)
        assert "修复登录超时" in prompt.prompt_text
        # Other fields should show placeholder
        assert prompt.prompt_text.count("（请补充）") == 6

    def test_all_fields_except_one(self, gen):
        """Fill 8 out of 9 fields."""
        profile = ProjectProfile(
            project_goal="goal",
            current_task="task",
            impact_scope="scope",
            known_issues="issues",
            related_files_modules="files",
            environment_info="env",
            time_constraints="time",
            success_criteria="success",
            # risk_preference left empty
        )
        prompt = gen.generate_single(profile, 0)
        # risk_preference is not a Stage 0 variable, so still 0 placeholders
        assert "（请补充）" not in prompt.prompt_text


class TestConsistentOrder:
    def test_stages_always_in_order(self, gen, empty_profile):
        for _ in range(3):
            result = gen.generate_all(empty_profile)
            ids = [p.stage_id for p in result.prompts]
            assert ids == list(range(14))
