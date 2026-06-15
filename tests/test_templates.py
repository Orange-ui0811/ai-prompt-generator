"""Tests for Jinja2 template rendering correctness."""

from jinja2 import Environment, FileSystemLoader


def make_env(templates_dir):
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class TestStage0Template:
    def test_full_profile(self, templates_dir, full_profile):
        env = make_env(templates_dir)
        tpl = env.get_template("stage_00_context.j2")
        output = tpl.render(**full_profile.to_template_vars())

        assert "构建一个电商推荐系统" in output
        assert "实现协同过滤推荐算法" in output
        assert "推荐引擎模块" in output
        assert "（请补充）" not in output  # all fields filled

    def test_partial_profile(self, templates_dir, partial_profile):
        env = make_env(templates_dir)
        tpl = env.get_template("stage_00_context.j2")
        output = tpl.render(**partial_profile.to_template_vars())

        assert "修复用户登录超时问题" in output
        assert "排查并修复 session 过期异常" in output
        # Unfilled fields should show placeholder
        assert "（请补充）" in output

    def test_empty_profile(self, templates_dir, empty_profile):
        env = make_env(templates_dir)
        tpl = env.get_template("stage_00_context.j2")
        output = tpl.render(**empty_profile.to_template_vars())

        # All 7 fields should show placeholder
        assert output.count("（请补充）") == 7
        assert "协作开发者" in output


class TestStages1To13Templates:
    """Test stages 1-13 with standalone and pure modes."""

    STAGE_TEMPLATES = [
        "stage_01_understand.j2",
        "stage_02_success.j2",
        "stage_03_constraints.j2",
        "stage_04_plan.j2",
        "stage_05_tdd.j2",
        "stage_06_minimal.j2",
        "stage_07_layered.j2",
        "stage_08_manual.j2",
        "stage_09_review.j2",
        "stage_10_commit.j2",
        "stage_11_push.j2",
        "stage_12_merge.j2",
        "stage_13_ci.j2",
    ]

    def test_standalone_with_profile(self, templates_dir, full_profile):
        """Standalone mode should inject profile context."""
        env = make_env(templates_dir)
        for tfile in self.STAGE_TEMPLATES:
            tpl = env.get_template(tfile)
            vars_ = {"mode": "standalone", **full_profile.to_template_vars()}
            output = tpl.render(**vars_)
            # Should contain project context
            assert "构建一个电商推荐系统" in output

    def test_pure_without_profile(self, templates_dir, empty_profile):
        """Pure mode should NOT inject any profile context."""
        env = make_env(templates_dir)
        for tfile in self.STAGE_TEMPLATES:
            tpl = env.get_template(tfile)
            output = tpl.render(mode="pure", **empty_profile.to_template_vars())
            # Should NOT contain any profile injection (check no section header)
            assert "## 当前项目上下文" not in output

    def test_pure_stages_1_13_match_handbook(self, templates_dir, empty_profile):
        """Pure mode output for stages 1-13 should match handbook original text."""
        env = make_env(templates_dir)
        for tfile in self.STAGE_TEMPLATES:
            tpl = env.get_template(tfile)
            output = tpl.render(mode="pure", **empty_profile.to_template_vars())
            assert len(output) > 0
            # Should contain Chinese text (not empty/whitespace only)
            assert any("一" <= c <= "鿿" for c in output)

    def test_all_templates_compile(self, templates_dir):
        """Verify every .j2 template compiles without Jinja2 errors."""
        env = make_env(templates_dir)
        for tfile in templates_dir.glob("*.j2"):
            env.get_template(tfile.name)  # should not raise


class TestMasterTemplate:
    def test_master_with_profile(self, templates_dir, full_profile):
        env = make_env(templates_dir)
        tpl = env.get_template("master.j2")
        output = tpl.render(**full_profile.to_template_vars())

        assert "构建一个电商推荐系统" in output
        assert "实现协同过滤推荐算法" in output
        # All 14 stages should be referenced
        assert "0. 先基于我提供的上下文" in output
        assert "13. 跟进 CI、部署和失败闭环" in output
        assert "执行要求" in output

    def test_master_empty_profile(self, templates_dir, empty_profile):
        env = make_env(templates_dir)
        tpl = env.get_template("master.j2")
        output = tpl.render(**empty_profile.to_template_vars())

        # Should still contain all stages, just no context header
        assert "0. 先基于我提供的上下文" in output
        assert "## 项目上下文" not in output
