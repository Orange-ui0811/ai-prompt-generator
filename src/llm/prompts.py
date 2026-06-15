"""System and user prompt templates for LLM-based content generation.

The LLM acts as a senior developer who UNDERSTANDS the project and
PRODUCES concrete deliverables — it does NOT regurgitate templates.
"""

from ..models import ProjectProfile, StageDefinition

SYSTEM_PROMPT_TEMPLATE = """你是用户的 AI 项目协作者，你的任务是**直接产出当前阶段的完整交付物**。

---

{profile_section}

---

## 当前阶段：{stage_name}

**阶段定位**：{stage_description}

**本阶段你要产出的内容**：
{key_points_formatted}

## 关键工作原则

### 1. 推测是你的核心能力
用户可能只给了一个项目名，其余信息全是空白。这**不是**你产出空洞内容的理由。你应该：
- 基于项目名，推理出这个项目可能的功能、技术栈、用户场景、典型架构
- 基于这些推理，产出**具体的、有血有肉的**内容
- 例如用户说"论文检索器"，你应该想到：学术搜索引擎、中英文文献、ArXiv/知网数据源、关键词+语义检索、引用图谱、BibTeX导出……然后基于这些想象去写成功标准、任务计划、测试策略等
- 你的推理不需要标注"推测"——在用户看来，这些就是你的专业建议

### 2. 产出物必须是成品
- 不要输出"你需要做X"——直接输出X的内容本身
- 不要输出模板结构让用户填空——你替用户把空填了
- 不要输出"以下是给AI的提示词"——**你就是那个AI**，你的输出就是最终答案

### 3. 每个字都要贴着项目写
- 如果项目是"论文检索器"，那么成功标准里出现的是"搜索响应时间<300ms"而不是"系统响应时间达标"
- 如果项目是"论文检索器"，那么测试策略里出现的是"用1000篇ArXiv论文元数据做检索召回测试"而不是"用样本数据做功能测试"
- **禁止出现泛泛的、可以套在任何项目上的话**

### 4. 遇到真的无法推测的信息
极少数情况下，你确实无法推测（比如用户特定环境下的配置值），此时标注「待确认」并提供你的最佳建议。"""

USER_PROMPT_TEMPLATE = """请为我产出「{stage_name}」阶段的完整内容。

{profile_text}

注意：即使用户信息不完整，也请基于项目名进行充分推理，产出具体可用的交付物，不要只返回一个等用户填空的模板。

直接输出："""


def _format_key_points(key_points: list[str]) -> str:
    if not key_points:
        return "（根据项目背景自行决定需要产出什么——不要犹豫，直接做出专业判断）"
    return "\n".join(f"- {kp}" for i, kp in enumerate(key_points))


def _build_profile_section(profile: ProjectProfile) -> str:
    """Present the profile as a starting point for inference, not a constraint."""
    all_fields = [
        ("project_goal", "项目目标"),
        ("current_task", "当前任务"),
        ("impact_scope", "影响范围"),
        ("known_issues", "已知问题"),
        ("related_files_modules", "相关文件/模块"),
        ("environment_info", "环境信息"),
        ("time_constraints", "时间要求"),
        ("success_criteria", "成功标准"),
        ("risk_preference", "风险偏好"),
    ]

    filled = [(label, getattr(profile, f, "").strip())
              for f, label in all_fields
              if getattr(profile, f, "").strip()]

    if not filled:
        return '（用户未提供任何项目信息。请基于当前阶段目标，假设一个典型的软件项目场景，直接产出专业的交付物。不要因为信息少就输出模板。）'

    lines = ['## 用户提供的项目信息', '']
    for label, value in filled:
        lines.append(f'- **{label}**：{value}')

    lines.append('')
    lines.append('**重要**：以上信息是你的推理起点，不是边界。')
    lines.append('基于这些信息，大胆推理这个项目的全貌（功能、技术栈、架构、用户、约束等），')
    lines.append('然后产出围绕该项目的完整内容。标注「推测」是不必要的——你的推理就是你的专业输出。')

    return '\n'.join(lines)


def _build_profile_text(profile: ProjectProfile) -> str:
    """Short user prompt — project name is the anchor for inference."""
    goal = (profile.project_goal or "").strip()
    task = (profile.current_task or "").strip()

    # Collect other filled fields
    other = []
    for f, label in [
        ("impact_scope", "影响范围"), ("known_issues", "已知问题"),
        ("related_files_modules", "相关文件"), ("environment_info", "环境信息"),
        ("time_constraints", "时间要求"), ("success_criteria", "成功标准"),
        ("risk_preference", "风险偏好"),
    ]:
        v = getattr(profile, f, "").strip()
        if v:
            other.append(f"{label}：{v}")

    lines = []

    if goal:
        lines.append(f'项目：{goal}')
    if task:
        lines.append(f'当前任务：{task}')
    for o in other:
        lines.append(f'{o}')

    if not lines:
        lines.append('（我还没填项目信息，请基于一个典型项目场景直接产出内容）')
    else:
        lines.append('')
        lines.append('我提供的信息比较简略。请基于项目名充分推理项目的方方面面，')
        lines.append('产出一份完整的、可用的交付物，不要输出填空模板。')

    return '\n'.join(lines)


def build_system_prompt(stage_def: StageDefinition, profile: ProjectProfile | None = None) -> str:
    profile_section = _build_profile_section(profile) if profile else "（无项目信息）"
    return SYSTEM_PROMPT_TEMPLATE.format(
        profile_section=profile_section,
        stage_name=stage_def.name,
        stage_description=stage_def.description,
        key_points_formatted=_format_key_points(stage_def.key_points),
    )


def build_user_prompt(profile: ProjectProfile, stage_def: StageDefinition) -> str:
    profile_text = _build_profile_text(profile)
    return USER_PROMPT_TEMPLATE.format(
        stage_name=stage_def.name,
        profile_text=profile_text,
    )
