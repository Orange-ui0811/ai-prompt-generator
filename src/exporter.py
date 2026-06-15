"""Markdown export for generated prompts.

Produces a document mirroring the structure of the original handbook:
title, profile summary, and per-stage description + key points + rendered prompt.
"""

from pathlib import Path
from datetime import datetime, timezone, timedelta
from .models import GenerationResult, StageDefinition, GeneratedPrompt, FIELD_LABELS


def _format_timestamp(iso_str: str) -> str:
    """Convert UTC ISO timestamp to a human-readable local time string."""
    try:
        dt = datetime.fromisoformat(iso_str)
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_str


def generate_markdown(
    result: GenerationResult, stage_defs: dict[int, StageDefinition]
) -> str:
    """
    Generate a complete Markdown document from a GenerationResult.

    Args:
        result: Full generation result with profile and prompts
        stage_defs: Stage definitions (for descriptions and key points)

    Returns:
        Complete Markdown string
    """
    lines = []

    # --- Header ---
    lines.append("# AI 项目提示词生成报告")
    lines.append("")
    lines.append(f"**生成时间**：{_format_timestamp(result.generated_at)}")
    lines.append(f"**生成阶段数**：{len(result.prompts)}")
    lines.append("")

    # --- Project profile summary ---
    lines.append("## 项目信息概览")
    lines.append("")
    profile = result.profile

    filled_any = False
    for field, label in FIELD_LABELS.items():
        value = getattr(profile, field, "")
        if value:
            filled_any = True
            lines.append(f"- **{label}**：{value}")

    if not filled_any:
        lines.append("（未填写项目信息）")
    lines.append("")

    # --- Per-stage sections ---
    for prompt in result.prompts:
        sd = stage_defs.get(prompt.stage_id)
        if not sd:
            continue

        lines.append("---")
        lines.append("")

        # Stage header
        if prompt.stage_id >= 0:
            lines.append(f"### {sd.id}. {sd.name}")
        else:
            lines.append(f"### {sd.name}")
        lines.append("")

        # Description as blockquote
        lines.append(f"> {sd.description}")
        lines.append("")

        # Key points
        if sd.key_points:
            lines.append("**要点：**")
            lines.append("")
            for kp in sd.key_points:
                lines.append(f"- {kp}")
            lines.append("")

        # Rendered prompt in code block
        lines.append("**提示词：**")
        lines.append("")
        lines.append("```text")
        lines.append(prompt.prompt_text)
        lines.append("```")
        lines.append("")

    # --- Final recommendations ---
    lines.append("---")
    lines.append("")
    lines.append("## 使用建议")
    lines.append("")
    lines.append("建议在每次给 AI 布置项目任务时，至少提供以下 5 类输入：")
    lines.append("")
    lines.append("- **任务目标** — 要完成什么")
    lines.append("- **当前现象或问题** — 为什么需要做")
    lines.append("- **影响范围** — 涉及哪些模块/系统")
    lines.append("- **成功标准** — 怎样算完成")
    lines.append("- **时间与风险偏好** — 求稳还是求快")
    lines.append("")
    lines.append(
        "只要这 5 类信息比较完整，AI 通常能更稳定地把项目推进到可交付状态。"
    )

    return "\n".join(lines)


def export_to_file(
    result: GenerationResult,
    stage_defs: dict[int, StageDefinition],
    output_path: Path,
) -> Path:
    """
    Export generation result to a Markdown file.

    Args:
        result: Full generation result
        stage_defs: Stage definitions
        output_path: Destination file path

    Returns:
        The output path that was written to

    Raises:
        OSError: If file cannot be written
    """
    md_content = generate_markdown(result, stage_defs)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_content, encoding="utf-8")
    return output_path
