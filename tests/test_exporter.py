"""Tests for Markdown export functionality."""

import tempfile
from pathlib import Path
import pytest
from src.engine import PromptGenerator
from src.exporter import generate_markdown, export_to_file


@pytest.fixture
def gen(templates_dir, config_dir):
    return PromptGenerator(templates_dir=templates_dir, config_dir=config_dir)


class TestGenerateMarkdown:
    def test_full_export(self, gen, full_profile):
        result = gen.generate_all(full_profile)
        md = generate_markdown(result, gen.stages)

        # Header
        assert "# AI 项目提示词生成报告" in md
        assert "## 项目信息概览" in md

        # Profile fields
        assert "构建一个电商推荐系统" in md
        assert "实现协同过滤推荐算法" in md

        # All 14 stages
        for sid in range(14):
            assert f"### {sid}. " in md

        # Key points and prompts
        assert "**要点：**" in md
        assert "**提示词：**" in md
        assert "```text" in md

        # Final recommendations
        assert "## 使用建议" in md
        assert "5 类输入" in md

    def test_empty_profile_export(self, gen, empty_profile):
        result = gen.generate_all(empty_profile)
        md = generate_markdown(result, gen.stages)

        assert "（未填写项目信息）" in md
        # Should still have all stages
        assert md.count("### ") >= 14

    def test_export_is_valid_utf8(self, gen, full_profile):
        result = gen.generate_all(full_profile)
        md = generate_markdown(result, gen.stages)
        # Should encode/decode without errors
        encoded = md.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == md


class TestExportToFile:
    def test_export_writes_file(self, gen, full_profile):
        result = gen.generate_all(full_profile)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "output.md"
            path = export_to_file(result, gen.stages, out)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert len(content) > 0
            assert "AI 项目提示词生成报告" in content

    def test_export_creates_parent_dirs(self, gen, full_profile):
        result = gen.generate_all(full_profile)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "subdir" / "deep" / "output.md"
            path = export_to_file(result, gen.stages, out)
            assert path.exists()
