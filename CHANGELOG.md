# Changelog

All notable changes to mentor-skill are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned (v0.3+)
- 如流数据源、evals 基线跑通与持续蒸馏调优

---

## [0.2.2] — 2026-04-06

### Fixed
- **PyPI 发布**：从 `publish.yml` 中移除 `environment: pypi`，使 GitHub OIDC 的 `sub` 与 PyPI「Trusted Publisher」常见配置（仓库 + workflow，无 Environment）一致，避免 `invalid-publisher`

---

## [0.2.1] — 2026-04-06

### Fixed
- **GitHub Actions**：`ruff check` 改为读取 `pyproject.toml` 中的 lint 配置（恢复 E701 等忽略项）；暂时移除 `ruff format --check`（与当前代码风格尚未统一）
- **测试**：`mentor import` 集成测试在窄终端下因 Rich 路径换行导致断言失败，改为对输出去换行后再匹配 Persona ID
- **CLI**：导入成功提示将路径单独一行，减少终端折行
- **发布工作流**：构建产物通过 artifact 传递到 Release job，GitHub Release 可正确附带 sdist/wheel

---

## [0.2.0] — 2026-04-06

### Added
- **`mentor doctor`**：检查配置、数据目录、`*_raw.json`、Persona 与 7 层完整性、`litellm` / `playwright`；可选 **`--check-llm`** 发短请求验证连通性
- **`mentor config --preset`**：一键设置 `llm.model` + `llm.api_base`（`zhipu` / `deepseek` / `qwen` / `minimax` / `openai`）；**`--set key.subkey=value`** 支持两层配置键
- **`mentor list`**：列出 Persona，**`--verbose`** 详情
- **`mentor demo`**：内置 Sample Persona；**`--full`** 展示完整 pipeline dry-run
- **`mentor --version` / `-V`**
- **`mentor test`**：多轮对话；**`--ask`** 单次模式
- **`mentor distill --resume`**：断点恢复；**`--interactive`** 逐层确认；**`--dry-run`** 计划与 token/费用预估
- **`mentor generate --format`**：`generic` / `cursor` / `claude` / `openclaw` / `all`
- **`mentor compare`**：逐层对比两个 Persona
- **`mentor update`**：增量更新 Persona
- **`mentor export` / `mentor import`**：`.mentor.zip` 打包与导入（**`--overwrite`**）
- **`mentor analyze`** 增强：高价值比例、平均消息长度、Top-5 高价值预览
- **L7 模型字段 `next_check_ins`**：与蒸馏层输出对齐；通用 / Claude SKILL 生成中展示
- **蒸馏层 Prompt（L1–L7）**：证据约束、跨层上下文、对话对优先、L7 结构化记忆与追问要点
- **`config.yaml.example`**、**`examples/sample-mentor-docs/`**、**`CONTRIBUTING.md`**
- **evals**：`metrics.py`、`run_eval.py`；`product_qa` / `tech_qa` / `academic_qa`；`evals/personas/sample_mentor/`
- **tests/**：`test_analyzers` / `test_collectors` / `test_distiller` / `test_generator` / **`test_cli`**（Typer 集成）
- **CI**：`.github/workflows/test.yml`（Python 3.10–3.13）、`publish.yml`（Tag → PyPI）

### Generators
- **CursorRuleGenerator**（`.mdc`）、**ClaudeSkillGenerator**、**OpenClawSkillGenerator**

### Collectors
- **Feishu**：文档正文（docx/doc/wiki）；用户搜索三层 fallback
- **Dingtalk**：知识库正文；Playwright 消息采集
- **Markdown**：glob 修复（`**/*.md`）

### Distiller
- Rich 进度条（ETA / 用时）；蒸馏前 **token 用量与费用预估**（多厂商价表）

### Code quality
- ruff 清理（F821/F841/E722/E741 等）；版本 **0.2.0**（`__init__.py` + `pyproject.toml`）
- 修复：`list` 命令名遮蔽内置 `list`，导致 `compare` 内 `isinstance(..., list)` 异常（模块级保留 `_list_type`）
- 修复：CLI 实现改名为 **`list_personas`** + `@app.command("list")`，避免 Typer 子命令解析错乱（曾出现执行 `doctor` 时误跑 `list -v`）；**`mentor doctor`** 对数据目录 `Path.resolve()` 后再 glob `*_raw.json`（macOS `/var` 与 `/private/var`）

### Docs
- README 重写：徽章、快速体验、7 层示意、命令参考

---

## [0.1.0] — 2026-04-05

### Added
- 项目初始化，7 层 Persona 模型设计
- CLI 框架：`init` / `collect` / `analyze` / `distill` / `generate` / `config`
- 数据采集：Markdown / PDF / WeChat / Feishu / DingTalk
- 蒸馏引擎：L1-L7 七层顺序蒸馏，litellm 多模型支持
- 生成器：通用 SKILL.md 格式
- 数据模型：`Persona`（7 层）/ `RawMessage` / `DialogPair`
- 配置系统：`config.yaml` 支持多 LLM 厂商配置
