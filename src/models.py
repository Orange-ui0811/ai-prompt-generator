"""Pydantic data models and shared constants for the AI Project Prompt Generator."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

# ── Shared profile field definitions ──────────────────────────────────
# (field_name, chinese_label, hint)
PROFILE_FIELDS: list[tuple[str, str, str]] = [
    ("project_goal", "项目目标", "这个项目整体是做什么的？"),
    ("current_task", "本次任务", "这次要完成什么具体任务？"),
    ("impact_scope", "影响范围", "会影响哪些模块、文件或系统？"),
    ("known_issues", "已知问题/现象", "当前有什么已知问题、报错或截图？"),
    ("related_files_modules", "相关文件/模块", "涉及哪些文件、分支或接口？"),
    ("environment_info", "环境信息", "运行环境、设备、版本信息？"),
    ("time_constraints", "时间或交付要求", "有时间限制或交付要求吗？"),
    ("success_criteria", "成功标准", "怎样算完成？有什么验收条件？"),
    ("risk_preference", "时间与风险偏好", "是求稳还是求快？风险容忍度如何？"),
]

# Shared stage display labels for selectboxes etc.
STAGE_OPTIONS: dict[int, str] = {
    0: "0. 提供项目背景与上下文",
    1: "1. 理解需求",
    2: "2. 定义成功标准",
    3: "3. 明确约束、风险与非目标",
    4: "4. 创建任务计划",
    5: "5. 尽量使用测试驱动开发",
    6: "6. 最小化实现",
    7: "7. 分层验证",
    8: "8. 本地人工测试",
    9: "9. 独立审查",
    10: "10. 变更摘要、回滚点与提交准备",
    11: "11. 干净提交",
    12: "12. 推送并创建合并请求",
    13: "13. 观察 CI、部署与失败闭环",
}

FIELD_LABELS: dict[str, str] = {
    "project_goal": "项目目标",
    "current_task": "本次任务",
    "impact_scope": "影响范围",
    "known_issues": "已知问题/现象",
    "related_files_modules": "相关文件/模块",
    "environment_info": "环境信息",
    "time_constraints": "时间或交付要求",
    "success_criteria": "成功标准",
    "risk_preference": "时间与风险偏好",
}


class LLMConfig(BaseModel):
    """Configuration for LLM-based prompt enhancement.

    Supports any OpenAI-compatible API (OpenAI, 豆包/Doubao, DeepSeek, Zhipu, etc.).
    Reads from environment variables by default: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL.
    """

    api_key: str = Field(
        default="",
        description="API key for the LLM provider",
    )
    base_url: str = Field(
        default="",
        description="OpenAI-compatible base URL",
    )
    model: str = Field(
        default="",
        description="Model name to use",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Generation temperature",
    )
    max_tokens: int = Field(
        default=16384,
        ge=1,
        le=32768,
        description="Maximum tokens in the generated response",
    )
    enabled: bool = Field(
        default=False,
        description="Whether LLM enhancement is enabled",
    )

    def is_ready(self) -> bool:
        """Check if all required fields are set for making API calls."""
        return bool(self.api_key and self.base_url and self.model)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create LLMConfig from environment variables.

        Reads: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        """
        import os
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", ""),
            enabled=bool(os.getenv("LLM_API_KEY")),
        )


class ProjectProfile(BaseModel):
    """User-provided project context. All fields optional for progressive filling."""

    project_goal: str = Field(
        default="",
        description="项目目标 — overall project objective",
    )
    current_task: str = Field(
        default="",
        description="本次任务 — specific task for this session",
    )
    impact_scope: str = Field(
        default="",
        description="影响范围 — which modules/areas this affects",
    )
    known_issues: str = Field(
        default="",
        description="已知问题/现象 — known issues, errors, screenshots, logs",
    )
    related_files_modules: str = Field(
        default="",
        description="相关文件/模块 — relevant files, branches, interfaces",
    )
    environment_info: str = Field(
        default="",
        description="环境信息 — environment, device, runtime info",
    )
    time_constraints: str = Field(
        default="",
        description="时间或交付要求 — time or delivery requirements",
    )
    success_criteria: str = Field(
        default="",
        description="成功标准 — what counts as done",
    )
    risk_preference: str = Field(
        default="",
        description="时间与风险偏好 — speed vs stability preference",
    )

    def is_empty(self) -> bool:
        """Check if no fields have been filled at all."""
        return all(getattr(self, f) == "" for f in self.model_fields)

    def filled_field_count(self) -> int:
        """Return count of non-empty fields."""
        return sum(1 for f in self.model_fields if getattr(self, f) != "")

    @property
    def has_any_context(self) -> bool:
        """True if at least one profile field is non-empty."""
        return any(getattr(self, f) != "" for f in self.model_fields)

    def to_template_vars(self) -> dict:
        """Convert to dict with only non-empty fields, plus has_any_context flag."""
        result = {f: getattr(self, f) for f in self.model_fields if getattr(self, f) != ""}
        result["has_any_context"] = self.has_any_context
        return result

    @classmethod
    def load(cls, path: str) -> "ProjectProfile":
        """Load profile from JSON file."""
        import json
        from pathlib import Path
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)

    def save(self, path: str) -> None:
        """Save profile to JSON file."""
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )


class StageDefinition(BaseModel):
    """Definition of a single workflow stage loaded from YAML config."""

    id: int
    name: str
    name_en: str
    description: str
    key_points: list[str] = []
    template_file: str
    has_user_variables: bool = False
    user_variable_fields: list[str] = []


class GeneratedPrompt(BaseModel):
    """A single rendered prompt for one stage."""

    stage_id: int
    stage_name: str
    prompt_text: str
    rendered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    profile_snapshot: dict = {}
    generation_method: str = Field(
        default="template",
        description="How this prompt was generated: 'llm' or 'template'",
    )


class GenerationResult(BaseModel):
    """Container for a full generation session."""

    profile: ProjectProfile = Field(default_factory=ProjectProfile)
    prompts: list[GeneratedPrompt] = []
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
