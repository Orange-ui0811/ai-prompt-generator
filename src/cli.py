"""Command-line interface for the AI Project Prompt Generator.

Usage:
    prompt-gen profile              Interactive project profile collection
    prompt-gen show                 Show current profile
    prompt-gen reset                Clear saved profile
    prompt-gen llm config           Configure LLM API settings
    prompt-gen single --stage 0     Generate single stage prompt
    prompt-gen all                  Generate all 14 stages
    prompt-gen master               Generate combined master prompt
    prompt-gen export -o output.md  Export to Markdown file
"""

import argparse
import sys
import os
from pathlib import Path

from jinja2 import TemplateError
from .models import ProjectProfile, PROFILE_FIELDS, LLMConfig
from .engine import PromptGenerator
from .exporter import export_to_file


# Resolve project root relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = PROJECT_ROOT / ".profile.json"
LLM_CONFIG_PATH = PROJECT_ROOT / ".llm_config.json"

# ── Shared generator factory (avoid repeated instantiation) ──────────
_generator: PromptGenerator | None = None


def _get_generator() -> PromptGenerator:
    """Lazy-create and cache the PromptGenerator instance."""
    global _generator
    if _generator is None:
        _generator = PromptGenerator(
            templates_dir=PROJECT_ROOT / "templates",
            config_dir=PROJECT_ROOT / "config",
        )
    return _generator


def _load_profile() -> ProjectProfile:
    """Load existing profile from disk, or return empty profile."""
    if PROFILE_PATH.exists():
        return ProjectProfile.load(str(PROFILE_PATH))
    return ProjectProfile()


def _load_llm_config() -> LLMConfig:
    """Load LLM config, preferring env vars over saved file."""
    # Env vars take priority
    env_config = LLMConfig.from_env()
    if env_config.is_ready():
        return env_config

    # Fall back to config file
    if LLM_CONFIG_PATH.exists():
        try:
            import json
            data = json.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8"))
            return LLMConfig(**data)
        except Exception:
            pass

    return env_config  # Return env config even if incomplete


def _get_llm_client():
    """Build an LLMClient if configuration is ready, else return None."""
    try:
        from .llm.client import LLMClient
    except ImportError:
        return None

    config = _load_llm_config()
    if config.is_ready() and config.enabled:
        try:
            return LLMClient(config)
        except Exception as e:
            print(f"⚠️  LLM 配置有误，将使用模板生成: {e}", file=sys.stderr)
    return None


def _output_prompt(prompt, output_path: str | None = None) -> int:
    """Write a single prompt to stdout or file. Returns exit code."""
    tag = "🤖 AI" if prompt.generation_method == "llm" else "📄 模板"
    if output_path:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(prompt.prompt_text, encoding="utf-8")
        print(f"✅ [{tag}] 已输出到 {p}")
    else:
        print()
        print(f"━━━ 阶段 {prompt.stage_id}: {prompt.stage_name} [{tag}] ━━━")
        print(prompt.prompt_text)
    return 0


def interactive_profile_collection(
    existing: ProjectProfile | None = None,
) -> ProjectProfile:
    """Interactive prompt to collect/edit project profile.

    Press Enter to skip a field or keep its existing value.
    """
    if existing is None:
        existing = ProjectProfile()

    values = {}
    print("=" * 60)
    print("   AI 项目提示词生成器 — 项目信息收集")
    print("   （按回车跳过该字段，输入内容后回车确认）")
    print("=" * 60)
    print()

    for field_name, label, hint in PROFILE_FIELDS:
        current = getattr(existing, field_name, "")
        display = f" [当前: {current}]" if current else ""
        response = input(f"📋 {label}\n   {hint}{display}\n   > ").strip()
        values[field_name] = response if response else current
        print()

    profile = ProjectProfile(**values)
    return profile


# ── Command handlers ─────────────────────────────────────────────────


def cmd_profile() -> int:
    """Handle 'profile' subcommand."""
    existing = _load_profile()
    if not existing.is_empty():
        print("发现已有项目信息：")
        print(f"  已填写字段数: {existing.filled_field_count()}/9")
        print()
        choice = input("是否编辑？[Y/n] ").strip().lower()
        if choice == "n":
            return 0

    profile = interactive_profile_collection(existing)
    profile.save(str(PROFILE_PATH))
    print(f"✅ 项目信息已保存到 {PROFILE_PATH}")
    print(f"   已填写 {profile.filled_field_count()}/9 个字段")
    return 0


def cmd_show() -> int:
    """Handle 'show' subcommand — display current profile and LLM status."""
    profile = _load_profile()
    llm_config = _load_llm_config()

    print()
    print("━" * 40)
    print("  当前项目信息")
    print("━" * 40)
    if profile.is_empty():
        print("  （尚无项目信息）")
    else:
        for field_name, label, hint in PROFILE_FIELDS:
            value = getattr(profile, field_name, "")
            if value:
                print(f"  📋 {label}: {value}")
            else:
                print(f"  📋 {label}: （未填写）")
    print("━" * 40)
    print(f"已填写 {profile.filled_field_count()}/9 个字段")
    print()

    # LLM status
    print("━" * 40)
    print("  LLM 配置状态")
    print("━" * 40)
    if llm_config.is_ready():
        print(f"  ✅ 已配置")
        print(f"  Base URL: {llm_config.base_url}")
        print(f"  Model: {llm_config.model}")
        print(f"  API Key: {'*' * 12}{llm_config.api_key[-4:] if len(llm_config.api_key) >= 4 else '（未设置）'}")
    else:
        missing = []
        if not llm_config.api_key:
            missing.append("LLM_API_KEY")
        if not llm_config.base_url:
            missing.append("LLM_BASE_URL")
        if not llm_config.model:
            missing.append("LLM_MODEL")
        print(f"  ⚠️  未配置（缺少: {', '.join(missing)}）")
        print(f"  设置环境变量后重试，或运行: prompt-gen llm config")
    print("━" * 40)
    return 0


def cmd_reset() -> int:
    """Handle 'reset' subcommand — clear saved profile."""
    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()
        print("✅ 已清除保存的项目信息")
    else:
        print("（没有已保存的项目信息）")
    return 0


def cmd_llm_config() -> int:
    """Handle 'llm config' subcommand — interactive LLM setup."""
    existing = _load_llm_config()

    print("=" * 60)
    print("   LLM API 配置")
    print("   （按回车保持当前值，输入内容后回车确认）")
    print("=" * 60)
    print()
    print("支持所有 OpenAI 兼容的 API，例如：")
    print("  豆包(Doubao):  https://ark.cn-beijing.volces.com/api/v3")
    print("  DeepSeek:      https://api.deepseek.com")
    print("  Zhipu(GLM):    https://open.bigmodel.cn/api/paas/v4")
    print("  OpenAI:        https://api.openai.com/v1")
    print()

    base_url = input(
        f"Base URL\n  当前: {existing.base_url or '（未设置）'}\n  > "
    ).strip()
    model = input(
        f"Model 名称\n  当前: {existing.model or '（未设置）'}\n  > "
    ).strip()
    api_key = input(
        f"API Key\n  当前: {'***' if existing.api_key else '（未设置）'}\n  > "
    ).strip()

    config = LLMConfig(
        api_key=api_key or existing.api_key,
        base_url=base_url or existing.base_url,
        model=model or existing.model,
        enabled=True,
    )

    # Save to config file
    import json
    LLM_CONFIG_PATH.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print()
    print(f"✅ LLM 配置已保存到 {LLM_CONFIG_PATH}")
    print(f"   Base URL: {config.base_url}")
    print(f"   Model: {config.model}")
    print(f"   API Key: {'***' if config.api_key else '（未设置）'}")

    # Test connection
    if config.is_ready():
        print()
        choice = input("是否测试连接？[Y/n] ").strip().lower()
        if choice != "n":
            from .llm.client import LLMClient
            try:
                client = LLMClient(config)
                if client.test_connection():
                    print("✅ 连接测试成功！LLM 增强已就绪。")
                else:
                    print("❌ 连接测试失败，请检查配置。")
            except Exception as e:
                print(f"❌ 连接测试失败: {e}")

    return 0


def _get_llm_for_args(args) -> object | None:
    """Get LLM client if not --no-ai and config is ready."""
    if getattr(args, "no_ai", False):
        return None
    return _get_llm_client()


def cmd_single(args) -> int:
    """Handle 'single' subcommand."""
    profile = _load_profile()
    gen = _get_generator()
    llm_client = _get_llm_for_args(args)

    try:
        prompt = gen.generate_single(profile, args.stage, mode=args.mode, llm_client=llm_client)
    except (KeyError, ValueError, TemplateError) as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1

    return _output_prompt(prompt, args.output)


def cmd_all(args) -> int:
    """Handle 'all' subcommand."""
    profile = _load_profile()
    gen = _get_generator()
    llm_client = _get_llm_for_args(args)

    try:
        result = gen.generate_all(profile, mode=args.mode, llm_client=llm_client)
    except (KeyError, ValueError, TemplateError) as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1

    if args.output:
        export_to_file(result, gen.stages, Path(args.output))
        llm_count = sum(1 for p in result.prompts if p.generation_method == "llm")
        print(f"✅ 已输出 {len(result.prompts)} 个阶段到 {args.output}" +
              (f"（其中 {llm_count} 个由 AI 生成）" if llm_count else ""))
        return 0

    for prompt in result.prompts:
        _output_prompt(prompt)
    return 0


def cmd_master(args) -> int:
    """Handle 'master' subcommand."""
    profile = _load_profile()
    gen = _get_generator()
    llm_client = _get_llm_for_args(args)

    try:
        prompt = gen.generate_master(profile, mode=args.mode, llm_client=llm_client)
    except (KeyError, ValueError, TemplateError) as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1

    return _output_prompt(prompt, args.output)


def cmd_export(args) -> int:
    """Handle 'export' subcommand."""
    profile = _load_profile()
    gen = _get_generator()
    llm_client = _get_llm_for_args(args)

    try:
        result = gen.generate_all(profile, mode=args.mode, llm_client=llm_client)
        output_path = export_to_file(result, gen.stages, Path(args.output))
    except (KeyError, ValueError, TemplateError) as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1

    llm_count = sum(1 for p in result.prompts if p.generation_method == "llm")
    print(f"✅ 已导出 Markdown 文档到 {output_path}")
    print(f"   包含 {len(result.prompts)} 个阶段 + 项目概况" +
          (f"（其中 {llm_count} 个由 AI 生成）" if llm_count else ""))
    print(f"   {output_path.stat().st_size} 字节")
    return 0


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="prompt-gen",
        description="AI项目提示词生成器 — 基于项目指导提示词手册生成定制化 AI 提示词",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  prompt-gen profile                    交互式填写项目信息
  prompt-gen show                       查看项目信息 & LLM 状态
  prompt-gen llm config                 配置 LLM API
  prompt-gen single --stage 0           生成第 0 阶段提示词
  prompt-gen single -s5 --no-ai         跳过 AI，强制模板生成
  prompt-gen all                        生成全部 14 阶段
  prompt-gen master                     生成总提示词（全阶段组合）
  prompt-gen export -o prompts.md       导出完整 Markdown 文档

LLM 环境变量（优先级高于配置文件）:
  LLM_API_KEY     API 密钥
  LLM_BASE_URL    OpenAI 兼容端点
  LLM_MODEL       模型名称
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # profile
    subparsers.add_parser("profile", help="交互式收集/编辑项目信息")

    # show
    subparsers.add_parser("show", help="查看当前项目信息 & LLM 状态")

    # reset
    subparsers.add_parser("reset", help="清除已保存的项目信息")

    # llm
    subparsers.add_parser("llm", help="配置 LLM API 设置 (等同于 llm config)")

    # ── Generation commands (share --no-ai and --mode) ───────────────

    def _add_generation_args(subparser, stage_required=False):
        subparser.add_argument(
            "--mode", choices=["standalone", "pure"], default="standalone",
            help="渲染模式 (默认: standalone)"
        )
        subparser.add_argument(
            "--output", "-o", help="输出文件路径（不指定则打印到标准输出）"
        )
        subparser.add_argument(
            "--no-ai", action="store_true",
            help="禁用 LLM 增强，强制使用模板生成"
        )

    # single
    single_parser = subparsers.add_parser("single", help="生成单个阶段的提示词")
    single_parser.add_argument(
        "--stage", "-s", type=int, required=True, choices=range(14),
        metavar="0-13", help="阶段编号"
    )
    _add_generation_args(single_parser)

    # all
    all_parser = subparsers.add_parser("all", help="生成全部 14 个阶段的提示词")
    _add_generation_args(all_parser)

    # master
    master_parser = subparsers.add_parser("master", help="生成总提示词（全阶段组合）")
    master_parser.add_argument(
        "--mode", choices=["standalone", "pure"], default="standalone",
        help="渲染模式 (默认: standalone)"
    )
    master_parser.add_argument(
        "--output", "-o", help="输出文件路径"
    )
    master_parser.add_argument(
        "--no-ai", action="store_true",
        help="禁用 LLM 增强"
    )

    # export
    export_parser = subparsers.add_parser("export", help="导出完整 Markdown 文档")
    export_parser.add_argument(
        "--output", "-o", required=True, help="输出 Markdown 文件路径"
    )
    export_parser.add_argument(
        "--mode", choices=["standalone", "pure"], default="standalone",
        help="渲染模式 (默认: standalone)"
    )
    export_parser.add_argument(
        "--no-ai", action="store_true",
        help="禁用 LLM 增强"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    handlers = {
        "profile": cmd_profile,
        "show": cmd_show,
        "reset": cmd_reset,
        "single": lambda: cmd_single(args),
        "all": lambda: cmd_all(args),
        "master": lambda: cmd_master(args),
        "export": lambda: cmd_export(args),
    }

    # "llm config" is parsed as command="llm" but we need to handle the subcommand
    # argparse doesn't support nested subparsers easily; handle "llm" command here
    if args.command in ("llm", "llm config"):
        return cmd_llm_config()

    return handlers[args.command]()


if __name__ == "__main__":
    sys.exit(main())
