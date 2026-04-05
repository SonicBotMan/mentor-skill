# 执行计划 (Execution Plan)

> mentor-skill — 从设计到发布的完整路径

---

## 当前状态（v0.2.0 已发布清单，2026-04-06）

```
✅ PRD v0.2              产品需求文档完成
✅ 技术设计文档           架构和模块设计完成
✅ 项目脚手架             Python 包结构，pyproject.toml
✅ 数据模型               Persona (7层) + RawMessage；L7 含 next_check_ins
✅ LLM 抽象层             litellm 多模型支持
✅ 数据采集模块            Markdown / PDF / WeChat / 飞书 / 钉钉
✅ 数据分析模块            DataCleaner / StatsAnalyzer / QualityAssessor / DialogExtractor
✅ 蒸馏引擎               L1-L7 七层 + 断点恢复 + 交互式确认 + token 成本预估 + Prompt 质量迭代
✅ Skill 生成器           通用 / Cursor / Claude / OpenClaw 四种格式
✅ CLI 工具               上述 + doctor / config --preset / export-import / distill --dry-run
✅ tests/ 框架            单测 + CLI 集成测试（pytest 全绿）
✅ evals/ 框架            LLM-as-judge 评估，Sample Persona + 15 个测试用例（product/tech/academic）
✅ GitHub Actions         CI（Python 3.10-3.13 矩阵）+ PyPI 发布工作流
✅ CHANGELOG              版本更新日志
✅ README v2              完整功能文档，5 分钟体验路径
✅ CONTRIBUTING.md        开发贡献指南
✅ config.yaml.example    完整注释配置模板
✅ Sample 导师文档         5 篇产品方向语料，供端到端测试
✅ ruff lint              0 警告（E/F/W 规则集）
```

---

## 里程碑进度

### ✅ Milestone 1：核心流程完整（已完成）

- [x] `mentor test` 命令
- [x] 蒸馏断点恢复 `--resume`
- [x] 飞书文档正文采集
- [x] tests/ 单测框架

### ✅ Milestone 2：质量与体验（已完成）

- [x] 多平台输出格式（Cursor / Claude / OpenClaw）
- [x] evals 评估框架
- [x] 蒸馏 UX：进度条 ETA + 交互模式完整实现
- [x] DingTalk 采集验证与修复

### ✅ Milestone 3：生态与发布准备（已完成）

- [x] `mentor demo` + `mentor list` 命令
- [x] GitHub Actions CI/CD
- [x] CHANGELOG.md
- [x] PRD.md / TECHNICAL_DESIGN.md / EXECUTION_PLAN.md

---

## 下一阶段：v0.3 计划

### P0（必须）

| 任务 | 说明 | 预估 |
|------|------|------|
| **evals 基线跑通** | 用 sample_mentor 实际运行 `run_eval.py`，确认评分流程无 bug | 1天 |
| **端到端真实测试** | 用真实 Markdown 文档跑完整 pipeline，修复实际运行中的 bug | 2天 |
| **版本号对齐** | 确认 `__version__` = `pyproject.toml` version = git tag | 0.5天 |
| **PyPI 首次发布** | `pip install mentor-skill` 可用 | 0.5天 |

### P1（重要）

| 任务 | 说明 | 预估 |
|------|------|------|
| **如流数据源** | 接入华为云如流消息采集 API | 3天 |
| **蒸馏质量优化** | 根据 evals 结果改进各层 Prompt | 持续 |
| ~~多 Persona 对比~~ | ✅ `mentor compare` 命令已实现 | 已完成 |
| ~~Skill 更新机制~~ | ✅ `mentor update` 命令已实现 | 已完成 |

### P2（有空再做）

| 任务 | 说明 | 预估 |
|------|------|------|
| **Web UI** | 可视化 Persona 编辑界面（基于 Gradio 或 Streamlit） | 5天 |
| **导师主动发布** | 导师可以主动打包自己的 Skill 并分享给学徒 | 待设计 |
| **多语言支持** | 英文 Persona 蒸馏 | 2天 |
| **异步蒸馏** | 后台运行，支持大数据量 | 3天 |

---

## 发布检查清单（v1.0）

在正式发布 v1.0 之前，需完成以下检查：

### 功能完整性
- [x] `mentor demo` 无需任何配置即可运行（至少展示 SKILL.md）← ✅
- [ ] 完整 pipeline 文档有截图/录屏
- [ ] evals sample_mentor 基线分 ≥ 7.5/10（需 LLM API）

### 代码质量
- [x] ruff lint 0 警告 ← ✅
- [x] 无 TODO/FIXME 遗留在核心路径 ← ✅（仅模板字符串中有 XXX）
- [ ] CI 全部通过（3.10 / 3.11 / 3.12 / 3.13）← 待 GitHub Actions 验证

### 文档
- [x] README 全面重写，含 5 分钟体验路径 ← ✅
- [x] 每个 CLI 命令有使用示例（README 命令参考表）← ✅
- [x] config.yaml.example 注释完整 ← ✅
- [x] CONTRIBUTING.md 开发者指南 ← ✅

### 发布
- [x] `pyproject.toml` version = `__init__.py` __version__ = 0.2.0 ← ✅
- [ ] CHANGELOG [Unreleased] → [0.2.0] 更新并打 tag
- [ ] git tag v0.2.0 并推送
- [ ] GitHub Release 自动触发 PyPI 发布

---

## 技术债务

| 项目 | 优先级 | 说明 |
|------|--------|------|
| FeishuCollector 错误处理 | 中 | API 返回异常时的 fallback 路径不够完善 |
| DingtalkCollector 浏览器方案 | 中 | Playwright DOM 选择器依赖页面结构，需定期维护 |
| 蒸馏 Prompt 版本化 | 低 | Prompt 变更时应有版本号，便于追踪质量变化 |
| LLM 调用 token 统计 | 低 | 目前没有 token 消耗统计，用户无法预估成本 |
| evals 测试用例扩充 | 中 | 目前只有 5 个 product 场景，需要补充 tech/academic 模板 |
