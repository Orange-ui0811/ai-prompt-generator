"""Core prompt generation engine.

Supports two generation backends:
1. Template mode (default): Jinja2 template rendering with profile variable injection.
2. LLM-enhanced mode: Uses an OpenAI-compatible LLM to generate richer, more
   customized prompts. Falls back to template mode on any failure.
"""

import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from .models import ProjectProfile, StageDefinition, GeneratedPrompt, GenerationResult
from .parser import load_stage_definitions

if TYPE_CHECKING:
    from .llm.client import LLMClient

logger = logging.getLogger(__name__)


class PromptGenerator:
    """Core generation engine for project workflow prompts."""

    def __init__(self, templates_dir: Path, config_dir: Path):
        """
        Args:
            templates_dir: Directory containing .j2 template files
            config_dir: Directory containing stages.yaml
        """
        self.templates_dir = Path(templates_dir)
        self.config_dir = Path(config_dir)

        # Load stage definitions from YAML
        self.stages: dict[int, StageDefinition] = load_stage_definitions(
            self.config_dir / "stages.yaml"
        )

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ── Internal helpers ─────────────────────────────────────────────

    def _render_template(
        self, profile: ProjectProfile, stage_id: int, mode: str
    ) -> GeneratedPrompt:
        """Render a single stage using Jinja2 template (original behavior)."""
        stage_def = self.stages[stage_id]
        template = self.jinja_env.get_template(stage_def.template_file)

        template_vars = {"mode": mode}
        if stage_id == 0 or mode == "standalone":
            template_vars.update(profile.to_template_vars())

        prompt_text = template.render(**template_vars)

        return GeneratedPrompt(
            stage_id=stage_id,
            stage_name=stage_def.name,
            prompt_text=prompt_text,
            rendered_at=datetime.now(timezone.utc).isoformat(),
            profile_snapshot=profile.model_dump(),
            generation_method="template",
        )

    def _try_llm_generate(
        self, profile: ProjectProfile, stage_id: int, llm_client: "LLMClient"
    ) -> GeneratedPrompt | None:
        """Attempt LLM generation for a stage. Returns None on failure."""
        stage_def = self.stages[stage_id]
        try:
            prompt_text = llm_client.generate_prompt(stage_def, profile)
            return GeneratedPrompt(
                stage_id=stage_id,
                stage_name=stage_def.name,
                prompt_text=prompt_text,
                rendered_at=datetime.now(timezone.utc).isoformat(),
                profile_snapshot=profile.model_dump(),
                generation_method="llm",
            )
        except Exception as e:
            logger.warning(
                "LLM generation failed for stage %d (%s), falling back to template: %s",
                stage_id, stage_def.name, e,
            )
            return None

    # ── Public API ───────────────────────────────────────────────────

    def generate_single(
        self,
        profile: ProjectProfile,
        stage_id: int,
        mode: str = "standalone",
        llm_client: "Optional[LLMClient]" = None,
    ) -> GeneratedPrompt:
        """Generate a single stage's prompt.

        Args:
            profile: User's project profile
            stage_id: Which stage (0-13) to generate
            mode: "standalone" (injects profile context) or "pure" (verbatim)
            llm_client: Optional LLM client for AI-enhanced generation.
                When provided and mode is "standalone", LLM generation is
                attempted first; on failure, falls back to template rendering.

        Returns:
            GeneratedPrompt with rendered text

        Raises:
            KeyError: If stage_id is invalid
            ValueError: If mode is invalid
        """
        if stage_id not in self.stages:
            available = sorted(self.stages.keys())
            raise KeyError(
                f"Invalid stage_id {stage_id}. Available: {available}"
            )

        if mode not in ("standalone", "pure"):
            raise ValueError(f"Invalid mode '{mode}'. Use 'standalone' or 'pure'.")

        # LLM enhancement only applies to standalone mode
        if llm_client is not None and mode == "standalone":
            llm_result = self._try_llm_generate(profile, stage_id, llm_client)
            if llm_result is not None:
                return llm_result

        return self._render_template(profile, stage_id, mode)

    def generate_all(
        self,
        profile: ProjectProfile,
        mode: str = "standalone",
        llm_client: "Optional[LLMClient]" = None,
    ) -> GenerationResult:
        """Generate prompts for all stages in order.

        Args:
            profile: User's project profile
            mode: Rendering mode for stages 1-13
            llm_client: Optional LLM client for AI-enhanced generation.

        Returns:
            GenerationResult with all GeneratedPrompts
        """
        prompts = []
        for stage_id in sorted(self.stages.keys()):
            prompts.append(
                self.generate_single(profile, stage_id, mode, llm_client=llm_client)
            )

        return GenerationResult(
            profile=profile,
            prompts=prompts,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_master(
        self,
        profile: ProjectProfile,
        mode: str = "standalone",
        llm_client: "Optional[LLMClient]" = None,
    ) -> GeneratedPrompt:
        """Generate the combined master prompt (all stages in one message).

        Args:
            profile: User's project profile
            mode: "standalone" (injects profile context) or "pure" (no injection)
            llm_client: Optional LLM client. When provided and mode is
                "standalone", uses LLM to generate a comprehensive master prompt.
                On failure, falls back to template rendering.

        Returns:
            GeneratedPrompt with the full combined prompt
        """
        if mode not in ("standalone", "pure"):
            raise ValueError(f"Invalid mode '{mode}'. Use 'standalone' or 'pure'.")

        # Try LLM for master prompt in standalone mode
        if llm_client is not None and mode == "standalone":
            try:
                from .llm.prompts import build_system_prompt, build_user_prompt

                # Build a synthetic stage def representing the combined workflow
                master_stage_def = StageDefinition(
                    id=-1,
                    name="完整项目交付（全阶段）",
                    name_en="master",
                    description="按 14 阶段流程，为项目产出从需求理解到 CI 跟进的完整交付物",
                    key_points=[
                        "建立项目理解，复述目标、边界与假设",
                        "理解需求并明确范围",
                        "定义可验证的成功标准",
                        "识别约束、风险与非目标",
                        "创建可执行的任务计划",
                        "编写或补全测试",
                        "最小化实现核心功能",
                        "分层验证（代码/模块/集成/回归）",
                        "人工测试方案与执行",
                        "独立审查：找 bug、风险和改进点",
                        "整理变更摘要与回滚方案",
                        "干净提交（范围聚焦、信息清晰）",
                        "准备推送与合并请求",
                        "跟进 CI、部署与失败闭环",
                    ],
                    template_file="master.j2",
                )
                prompt_text = llm_client.generate_prompt(master_stage_def, profile)
                return GeneratedPrompt(
                    stage_id=-1,
                    stage_name="总提示词（全阶段组合）",
                    prompt_text=prompt_text,
                    rendered_at=datetime.now(timezone.utc).isoformat(),
                    profile_snapshot=profile.model_dump(),
                    generation_method="llm",
                )
            except Exception as e:
                logger.warning("LLM master generation failed, falling back: %s", e)

        # Fallback: template rendering
        template = self.jinja_env.get_template("master.j2")
        template_vars = profile.to_template_vars()
        template_vars["mode"] = mode
        prompt_text = template.render(**template_vars)

        return GeneratedPrompt(
            stage_id=-1,
            stage_name="总提示词（全阶段组合）",
            prompt_text=prompt_text,
            rendered_at=datetime.now(timezone.utc).isoformat(),
            profile_snapshot=profile.model_dump(),
            generation_method="template",
        )

    def generate_subset(
        self,
        profile: ProjectProfile,
        stage_ids: list[int],
        mode: str = "standalone",
        llm_client: "Optional[LLMClient]" = None,
    ) -> GenerationResult:
        """Generate prompts for a specific subset of stages.

        Args:
            profile: User's project profile
            stage_ids: List of stage IDs to generate
            mode: Rendering mode
            llm_client: Optional LLM client for AI-enhanced generation.

        Returns:
            GenerationResult containing only the requested stages

        Raises:
            KeyError: If any stage_id is invalid
        """
        prompts = []
        for sid in stage_ids:
            prompts.append(
                self.generate_single(profile, sid, mode, llm_client=llm_client)
            )

        return GenerationResult(
            profile=profile,
            prompts=prompts,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
