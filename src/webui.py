"""Streamlit Web UI for the AI Project Prompt Generator.

Launch with:
    streamlit run src/webui.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.models import ProjectProfile, PROFILE_FIELDS, STAGE_OPTIONS, LLMConfig
from src.engine import PromptGenerator
from src.exporter import generate_markdown

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 项目提示词生成器",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Fixed paths ─────────────────────────────────────────────────────
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CONFIG_DIR = PROJECT_ROOT / "config"
PROFILE_PATH = PROJECT_ROOT / ".profile.json"
LLM_CONFIG_PATH = PROJECT_ROOT / ".llm_config.json"


# ── LLM helpers ─────────────────────────────────────────────────────
def _load_llm_config() -> LLMConfig:
    """Load LLM config from env vars or saved file."""
    env_config = LLMConfig.from_env()
    if env_config.is_ready():
        return env_config
    if LLM_CONFIG_PATH.exists():
        try:
            import json
            data = json.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8"))
            return LLMConfig(**data)
        except Exception:
            pass
    return env_config


def _build_llm_client(config: LLMConfig):
    """Build LLMClient from config. Returns None if not ready or on error."""
    if not config.is_ready():
        return None
    try:
        from src.llm.client import LLMClient
        return LLMClient(config)
    except Exception:
        return None


# ── Session state init ─────────────────────────────────────────────
def _init_session():
    """Initialize Streamlit session state."""
    if "generator" not in st.session_state:
        st.session_state.generator = PromptGenerator(TEMPLATES_DIR, CONFIG_DIR)

    if "profile" not in st.session_state:
        st.session_state.profile = ProjectProfile()

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    if "last_md" not in st.session_state:
        st.session_state.last_md = ""

    if "expand_all" not in st.session_state:
        st.session_state.expand_all = False

    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None

    # LLM state
    if "llm_config" not in st.session_state:
        st.session_state.llm_config = _load_llm_config()

    if "llm_client" not in st.session_state:
        st.session_state.llm_client = _build_llm_client(st.session_state.llm_config)

    if "llm_enabled" not in st.session_state:
        st.session_state.llm_enabled = st.session_state.llm_config.is_ready()


def _load_profile():
    """Load profile from disk into session state."""
    if PROFILE_PATH.exists():
        st.session_state.profile = ProjectProfile.load(str(PROFILE_PATH))
        return True
    return False


def _save_profile():
    """Save profile from session state to disk."""
    try:
        st.session_state.profile.save(str(PROFILE_PATH))
    except OSError as e:
        st.error(f"保存失败：{e}")


# ── Sidebar: Project Info ──────────────────────────────────────────
def render_sidebar():
    st.sidebar.title("📋 项目信息")

    profile = st.session_state.profile

    # Use a form so that save is explicit and values don't leak mid-edit
    with st.sidebar.form("profile_form"):
        new_values = {}
        for field_name, label, hint in PROFILE_FIELDS:
            current = getattr(profile, field_name, "")
            new_values[field_name] = st.text_area(
                label,
                value=current,
                placeholder=hint,
                height=68,
                key=f"field_{field_name}",
            )

        submitted = st.form_submit_button("💾 保存项目信息", use_container_width=True)
        if submitted:
            # Apply all values at once — only on explicit submit
            for field_name, value in new_values.items():
                setattr(st.session_state.profile, field_name, value.strip() if value else "")
            _save_profile()
            st.toast("✅ 项目信息已保存", icon="✅")

    # Load / Clear buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📂 加载", use_container_width=True):
            if _load_profile():
                st.toast("已加载保存的项目信息", icon="📂")
                st.rerun()
            else:
                st.toast("没有已保存的信息", icon="⚠️")
    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state.profile = ProjectProfile()
            _save_profile()
            st.toast("已清空", icon="🗑️")
            st.rerun()

    # Status line
    count = profile.filled_field_count()
    st.sidebar.caption(f"已填写 **{count}**/9 个字段")

    # ── Settings ──────────────────────────────────────────────────
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ 设置")

    mode = st.sidebar.radio(
        "渲染模式",
        options=["standalone", "pure"],
        format_func=lambda m: "🔗 standalone（注入项目上下文）" if m == "standalone" else "📄 pure（手册原文）",
        help="standalone: 每阶段独立可用，注入你的项目信息\n\npure: 输出手册原文，不做任何注入",
    )

    # ── LLM Configuration ─────────────────────────────────────────
    st.sidebar.divider()
    st.sidebar.subheader("🤖 AI 增强")

    # Toggle
    llm_enabled = st.sidebar.toggle(
        "启用 AI 增强生成",
        value=st.session_state.llm_enabled,
        help="使用 LLM 参考模板生成更智能的定制化提示词。失败时自动降级到模板渲染。",
    )
    st.session_state.llm_enabled = llm_enabled

    if llm_enabled:
        cfg = st.session_state.llm_config

        # Use on_change callbacks to persist to session_state immediately,
        # because password fields clear on rerender.
        def _on_api_key_change():
            st.session_state.llm_config.api_key = st.session_state.llm_api_key_input

        def _on_base_url_change():
            st.session_state.llm_config.base_url = st.session_state.llm_base_url_input

        def _on_model_change():
            st.session_state.llm_config.model = st.session_state.llm_model_input

        api_key = st.sidebar.text_input(
            "API Key",
            value=cfg.api_key,
            type="password",
            placeholder="sk-...",
            key="llm_api_key_input",
            on_change=_on_api_key_change,
            help="LLM_API_KEY 环境变量或直接输入",
        )
        base_url = st.sidebar.text_input(
            "Base URL",
            value=cfg.base_url,
            placeholder="https://api.openai.com/v1",
            key="llm_base_url_input",
            on_change=_on_base_url_change,
            help="OpenAI 兼容的 API 端点",
        )
        model = st.sidebar.text_input(
            "Model",
            value=cfg.model,
            placeholder="gpt-4o-mini",
            key="llm_model_input",
            on_change=_on_model_change,
            help="模型名称",
        )

        # Also capture values that Streamlit returns on this render
        # (for the case where widget already has state)
        if api_key:
            cfg.api_key = api_key
        if base_url:
            cfg.base_url = base_url
        if model:
            cfg.model = model

        # Rebuild client — but NEVER set it to None if it was already valid.
        # Password fields clear on rerender, which would falsely invalidate.
        if cfg.is_ready():
            st.session_state.llm_client = _build_llm_client(cfg)
        # else: keep existing llm_client — it was built from valid config earlier

        llm_ready = st.session_state.llm_client is not None

        # Connection test button
        col_t1, col_t2 = st.sidebar.columns([3, 2])
        with col_t1:
            if st.button("🔌 测试连接", use_container_width=True):
                if st.session_state.llm_client is not None:
                    with st.spinner("测试中..."):
                        ok = st.session_state.llm_client.test_connection()
                        if ok:
                            st.toast("✅ 连接成功！", icon="✅")
                        else:
                            st.toast("❌ 连接失败，请检查配置", icon="❌")
                else:
                    st.toast("⚠️ 请先填写完整的 API 配置", icon="⚠️")
        with col_t2:
            llm_status = "✅ 就绪" if llm_ready else "⚠️ 未配置"
            st.caption(llm_status)
    else:
        st.session_state.llm_client = None
        st.sidebar.caption("AI 增强已关闭，使用模板生成")

    return mode


# ── Helpers for tabs ───────────────────────────────────────────────
def _get_llm_client_for_generation():
    """Return LLM client if enabled and ready, else None."""
    if st.session_state.llm_enabled and st.session_state.llm_client is not None:
        return st.session_state.llm_client
    return None


def _generation_info(method: str, llm_configured: bool):
    """Show generation method info with prominent warnings when AI is expected but unused."""
    if method == "llm":
        st.success("🤖 AI 已根据你的项目信息直接产出本阶段完整交付物")
        return
    # Template was used
    if llm_configured:
        st.error("🚨 AI 调用失败，已降级为模板渲染。请在侧边栏点击「🔌 测试连接」检查配置。如连接正常但仍失败，请展开下方「🔍 调试信息」查看详情。")
    else:
        st.warning("⚠️ AI 增强未启用。当前为模板生成，输出的是通用提示词而非围绕你项目的定制内容。请在侧边栏打开 AI 开关并填写 API 配置。")


# ── Tab 1: Single Stage ────────────────────────────────────────────
def render_tab_single(mode: str):
    st.subheader("🎯 单阶段生成")
    st.caption("选择一个阶段，生成定制化的 AI 提示词")

    gen = st.session_state.generator
    profile = st.session_state.profile
    llm_client = _get_llm_client_for_generation()

    col1, col2 = st.columns([2, 1], vertical_alignment="bottom")
    with col1:
        stage_id = st.selectbox(
            "选择阶段",
            options=list(STAGE_OPTIONS.keys()),
            format_func=lambda sid: STAGE_OPTIONS[sid],
            key="single_stage_select",
            label_visibility="collapsed",
        )
    with col2:
        btn_label = "🤖 AI 直接产出" if llm_client else "🚀 生成提示词"
        generate_btn = st.button(btn_label, use_container_width=True, type="primary")

    # Show stage info
    sd = gen.stages[stage_id]
    with st.expander("📖 阶段说明", expanded=False):
        st.markdown(f"**{sd.name}**")
        st.caption(sd.description)
        if sd.key_points:
            st.markdown("**要点：**")
            for kp in sd.key_points:
                st.markdown(f"- {kp}")

    if generate_btn:
        spinner_text = "AI 正在根据你的项目信息产出阶段交付物..." if llm_client else "模板生成中..."
        with st.spinner(spinner_text):
            try:
                prompt = gen.generate_single(
                    profile, stage_id, mode=mode,
                    llm_client=llm_client,
                )
                st.session_state.last_prompt = prompt
            except Exception as e:
                st.error(f"生成失败：{e}")

    if "last_prompt" in st.session_state and st.session_state.last_prompt:
        prompt = st.session_state.last_prompt
        st.divider()
        st.markdown(f"### 📝 阶段 {prompt.stage_id}：{prompt.stage_name}")

        # Show generation status
        llm_configured = st.session_state.llm_client is not None
        _generation_info(prompt.generation_method, llm_configured)

        st.code(prompt.prompt_text, language="text", line_numbers=False)

        st.download_button(
            "💾 下载 .txt",
            data=prompt.prompt_text,
            file_name=f"stage_{prompt.stage_id:02d}_{sd.name_en}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ── Debug panel ──────────────────────────────────────────────
    with st.expander("🔍 调试信息", expanded=False):
        _show_debug_info(profile, llm_client)


def _show_debug_info(profile: ProjectProfile, llm_client):
    """Show diagnostic info: profile state, LLM status, last prompt sent."""
    st.markdown("### 📋 当前 Profile 状态")
    field_names = [
        ("project_goal", "项目目标"), ("current_task", "当前任务"),
        ("impact_scope", "影响范围"), ("known_issues", "已知问题"),
        ("related_files_modules", "相关文件"), ("environment_info", "环境信息"),
        ("time_constraints", "时间要求"), ("success_criteria", "成功标准"),
        ("risk_preference", "风险偏好"),
    ]
    for field, label in field_names:
        value = getattr(profile, field, "")
        if value:
            st.write(f"- **{label}**: {value}")
        else:
            st.write(f"- **{label}**: *(空)*")
    st.write(f"→ has_any_context: {profile.has_any_context}")
    st.write(f"→ filled_field_count: {profile.filled_field_count()}/9")

    st.markdown("### 🤖 LLM 状态")
    if llm_client is not None:
        st.success(f"已连接 — model={llm_client.config.model}, base_url={llm_client.config.base_url}")
    else:
        llm_cfg = st.session_state.llm_config
        enabled = st.session_state.llm_enabled
        st.write(f"- llm_enabled: {enabled}")
        st.write(f"- api_key 已设置: {bool(llm_cfg.api_key)}")
        st.write(f"- base_url: {llm_cfg.base_url or '*(空)*'}")
        st.write(f"- model: {llm_cfg.model or '*(空)*'}")
        st.write(f"- is_ready(): {llm_cfg.is_ready()}")
        if enabled and not llm_cfg.is_ready():
            st.warning("LLM 开关已打开但配置不完整，将使用模板生成")


# ── Tab 2: All Stages ─────────────────────────────────────────────
def render_tab_all(mode: str):
    st.subheader("📦 全部生成")
    st.caption("一次生成全部 14 个阶段的提示词")

    gen = st.session_state.generator
    profile = st.session_state.profile
    llm_client = _get_llm_client_for_generation()

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        btn_label = "🤖 AI 直接产出全部" if llm_client else "🚀 生成全部 14 阶段"
        generate_btn = st.button(btn_label, use_container_width=True, type="primary")
    with col2:
        if st.button("📖 全部展开", use_container_width=True):
            st.session_state.expand_all = True
    with col3:
        if st.button("📕 全部折叠", use_container_width=True):
            st.session_state.expand_all = False

    if generate_btn:
        spinner_text = "AI 正在根据你的项目信息产出 14 阶段交付物..." if llm_client else "模板生成中..."
        with st.spinner(spinner_text):
            try:
                result = gen.generate_all(profile, mode=mode, llm_client=llm_client)
                st.session_state.last_result = result
                st.session_state.last_md = generate_markdown(result, gen.stages)
            except Exception as e:
                st.error(f"生成失败：{e}")

    if "last_result" not in st.session_state or not st.session_state.last_result:
        st.info("点击上方按钮生成全部阶段的提示词")
        return

    result = st.session_state.last_result
    st.divider()

    llm_count = sum(1 for p in result.prompts if p.generation_method == "llm")
    summary = f"共 {len(result.prompts)} 个阶段"
    if llm_count:
        summary += f"，其中 {llm_count} 个由 AI 生成"
    st.caption(summary)

    # Show generation status
    llm_configured = st.session_state.llm_client is not None
    if llm_count == 0:
        _generation_info("template", llm_configured)

    for prompt in result.prompts:
        sd = gen.stages.get(prompt.stage_id)
        method_badge = "🤖" if prompt.generation_method == "llm" else "📄"
        with st.expander(
            f"{method_badge} 阶段 {prompt.stage_id}：{prompt.stage_name}",
            expanded=st.session_state.expand_all,
        ):
            st.code(prompt.prompt_text, language="text", line_numbers=False)

    # Export at bottom
    st.divider()
    if st.session_state.last_md:
        st.download_button(
            "💾 下载完整 Markdown 文档",
            data=st.session_state.last_md,
            file_name="AI项目提示词.md",
            mime="text/markdown",
            use_container_width=True,
        )


# ── Tab 3: Export ──────────────────────────────────────────────────
def render_tab_export(mode: str):
    st.subheader("📄 导出文档")
    st.caption("生成并预览完整的 Markdown 文档")

    gen = st.session_state.generator
    profile = st.session_state.profile
    llm_client = _get_llm_client_for_generation()

    col1, col2 = st.columns([1, 3])
    with col1:
        btn_label = "🤖 AI 生成预览" if llm_client else "🔄 生成预览"
        preview_btn = st.button(btn_label, use_container_width=True, type="primary")

    if preview_btn:
        spinner_text = "AI 正在根据你的项目信息生成文档..." if llm_client else "模板生成中..."
        with st.spinner(spinner_text):
            try:
                result = gen.generate_all(profile, mode=mode, llm_client=llm_client)
                st.session_state.last_result = result
                st.session_state.last_md = generate_markdown(result, gen.stages)
            except Exception as e:
                st.error(f"生成失败：{e}")

    if not st.session_state.last_md:
        st.info("点击「生成预览」查看 Markdown 文档")
        return

    st.divider()

    # Download button
    st.download_button(
        "💾 下载 Markdown 文件",
        data=st.session_state.last_md,
        file_name="AI项目提示词.md",
        mime="text/markdown",
        use_container_width=True,
    )

    # Preview
    st.markdown("### 👁️ 文档预览")
    st.markdown(st.session_state.last_md)


# ── Main ────────────────────────────────────────────────────────────
def main():
    _init_session()

    st.title("🧠 AI 项目提示词生成器")
    st.caption("基于《项目指导提示词手册》14 阶段标准流程 · 生成定制化 AI 协作提示词")

    mode = render_sidebar()

    tab1, tab2, tab3 = st.tabs(["🎯 单阶段生成", "📦 全部生成", "📄 导出文档"])

    with tab1:
        render_tab_single(mode)
    with tab2:
        render_tab_all(mode)
    with tab3:
        render_tab_export(mode)


if __name__ == "__main__":
    main()
