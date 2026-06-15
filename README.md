# AI 项目提示词生成器

基于《项目指导提示词手册》的命令行工具，通过**一次填写项目上下文**，生成 14 个标准化阶段的定制 AI 提示词。

## 快速开始

```bash
pip install -r requirements.txt
python -m src.cli profile              # 交互式填写项目信息
python -m src.cli single --stage 0     # 生成单个阶段提示词
python -m src.cli all                  # 生成全部 14 阶段
python -m src.cli master               # 生成总提示词（全阶段组合）
python -m src.cli export -o output.md  # 导出完整 Markdown 文档
```

## 14 个阶段

| # | 阶段 | 说明 |
|---|------|------|
| 0 | 提供项目背景与上下文 | 建立项目理解基础 |
| 1 | 理解需求 | 识别真实目标与边界 |
| 2 | 定义成功标准 | 明确可验证的完成条件 |
| 3 | 明确约束、风险与非目标 | 避免范围蔓延 |
| 4 | 创建任务计划 | 建立可执行路径 |
| 5 | 尽量使用测试驱动开发 | 先验证再实现 |
| 6 | 最小化实现 | 只做满足目标的最小改动 |
| 7 | 分层验证 | 代码/模块/集成/回归逐层验证 |
| 8 | 本地人工测试 | 补充自动化无法覆盖的场景 |
| 9 | 独立审查 | Reviewer 视角主动找问题 |
| 10 | 变更摘要与提交准备 | 整理交付信息与回滚方案 |
| 11 | 干净提交 | 可读、可追踪、可审查的提交 |
| 12 | 推送并创建合并请求 | 让 reviewer 快速理解 |
| 13 | 观察 CI、部署与失败闭环 | 提交后继续跟进直至稳定 |

## 两种生成模式

| 模式 | Stage 0 | Stages 1-13 |
|------|---------|-------------|
| **standalone**（默认） | 注入项目信息 | 注入上下文前缀，每阶段可独立使用 |
| **pure** | 注入项目信息 | 手册原文逐字输出，不做任何注入 |

```bash
python -m src.cli single --stage 5 --mode pure    # 手册原文
python -m src.cli single --stage 5 --mode standalone  # 含项目上下文（默认）
```

## 项目结构

```
├── config/
│   └── stages.yaml       # 14 阶段元数据定义
├── templates/
│   ├── stage_00_context.j2   # ~ stage_13_ci.j2
│   └── master.j2             # 总提示词模板
├── src/
│   ├── models.py         # Pydantic 数据模型
│   ├── parser.py         # YAML 配置加载
│   ├── engine.py         # 核心生成引擎
│   ├── exporter.py       # Markdown 导出
│   └── cli.py            # 命令行入口
└── tests/
```

## 运行测试

```bash
pytest tests/ -v
```
