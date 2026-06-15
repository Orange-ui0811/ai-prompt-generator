"""Shared test fixtures for the prompt generator tests."""

import pytest
from pathlib import Path
from src.models import ProjectProfile, StageDefinition, GeneratedPrompt, GenerationResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def full_profile() -> ProjectProfile:
    """A fully populated project profile."""
    return ProjectProfile(
        project_goal="构建一个电商推荐系统",
        current_task="实现协同过滤推荐算法",
        impact_scope="推荐引擎模块、用户画像服务、API 网关",
        known_issues="当前热门推荐接口响应超过 2 秒",
        related_files_modules="src/recommender/、src/api/gateway.py",
        environment_info="Python 3.11, Linux x86_64, Redis 7.0, PostgreSQL 15",
        time_constraints="两周内完成核心功能",
        success_criteria="推荐接口 P99 延迟 < 500ms，A/B 测试点击率提升 10%",
        risk_preference="求稳，优先保证线上稳定性",
    )


@pytest.fixture
def partial_profile() -> ProjectProfile:
    """A profile with only the essential fields filled."""
    return ProjectProfile(
        project_goal="修复用户登录超时问题",
        current_task="排查并修复 session 过期异常",
        impact_scope="auth 模块",
    )


@pytest.fixture
def empty_profile() -> ProjectProfile:
    """A completely empty profile."""
    return ProjectProfile()


@pytest.fixture
def templates_dir() -> Path:
    return PROJECT_ROOT / "templates"


@pytest.fixture
def config_dir() -> Path:
    return PROJECT_ROOT / "config"
