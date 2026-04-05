# 导师.SKILL (mentor-skill)

> **"导师可以走，但她的判断力可以留下。"**

[![Tests](https://github.com/SonicBotMan/mentor-skill/actions/workflows/test.yml/badge.svg)](https://github.com/SonicBotMan/mentor-skill/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/mentor-skill.svg)](https://badge.fury.io/py/mentor-skill)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

把你的导师蒸馏成 AI Skill——她的思维方式、反馈风格、知识体系、甚至口头禅，全部保留。

---

## 5 分钟体验

```bash
pip install mentor-skill

# 无需任何配置，立即与内置导师「王老师」对话
mentor demo

# 配置 LLM 后，与她实时对话（可用 --preset 一键设置模型与 api_base）
mentor doctor
mentor config --preset zhipu
mentor config --set llm.api_key YOUR_KEY
mentor demo --ask "老师，帮我看看这个用户增长方案"
```

---

## 它能做什么

```
你的输入                      导师.SKILL 的输出
─────────────────────────     ──────────────────────────────────────────
导师写的 Markdown 文档    →   在 Cursor IDE 中以导师口吻给你反馈
飞书/钉钉/微信对话记录    →   Claude Code 里的专属导师 Persona
PDF 论文/方法论文档       →   OpenClaw AgentSkills 兼容格式
                              …
```

核心特性：**导师会记得你的项目，主动追问进展，检查你有没有真的改。**

---

## 7 层 Persona 模型

```
┌─────────────────────────────────────────┐
│  Layer 7: 学徒记忆层  ⭐ 核心差异化      │  记得你的项目、追问进展、检查修改
├─────────────────────────────────────────┤
│  Layer 6: 指导关系层                    │  她怎么带人、放手程度、指导节奏
├─────────────────────────────────────────┤
│  Layer 5: 情感表达层                    │  鼓励方式、不满信号、共情风格
├─────────────────────────────────────────┤
│  Layer 4: 沟通风格层                    │  语气、节奏、修辞、口头禅
├─────────────────────────────────────────┤
│  Layer 3: 思维框架层                    │  方法论、决策逻辑、追问方式
├─────────────────────────────────────────┤
│  Layer 2: 知识与专业层                  │  领域深度、知识边界、核心见解
├─────────────────────────────────────────┤
│  Layer 1: 基础身份层                    │  姓名、背景、性格、行为红线
└─────────────────────────────────────────┘
```

---

## 完整使用流程

### Step 0：安装

```bash
pip install mentor-skill

# 如需采集钉钉消息（浏览器自动化），额外安装 chromium
playwright install chromium
```

### Step 1：初始化

```bash
mentor init --name wang-laoshi --template product
# 模板可选：product（产品）| tech（技术）| academic（学术）
```

### Step 2：采集数据

```bash
# 本地文档（最简单，推荐先从这里开始）
mentor collect --source markdown --input ./mentor-docs/ --persona wang-laoshi
mentor collect --source pdf --input ./mentor-papers/ --persona wang-laoshi

# 微信（需先用 WeChatMsg 工具导出为 CSV）
mentor collect --source wechat --input ./wechat_export.csv --persona wang-laoshi

# 飞书（需配置 App ID/Secret，见 config.yaml.example）
mentor collect --source feishu --name "王老师" --persona wang-laoshi

# 钉钉（文档走 API，消息走 Playwright）
mentor collect --source dingtalk --name "王老师" --persona wang-laoshi
```

### Step 3：检查数据质量

```bash
mentor analyze --persona wang-laoshi --stats
# 输出：消息数、高价值消息数、质量评分（0-100）及建议
```

### Step 4：蒸馏

```bash
# 自检环境（配置、数据、依赖；可选 --check-llm 验证 API 连通）
mentor doctor

# 配置 LLM：一键预设（zhipu / deepseek / qwen / minimax / openai）或手动逐项设置
mentor config --preset zhipu
mentor config --set llm.api_key YOUR_API_KEY

# 手动示例（与 preset 二选一即可）
# mentor config --set llm.model glm-4-flash
# mentor config --set llm.api_base https://open.bigmodel.cn/api/paas/v4/

# 执行 7 层蒸馏（约 5-15 分钟）
mentor distill --persona wang-laoshi

# 中途中断后续跑
mentor distill --persona wang-laoshi --resume

# 逐层确认（每层结果可编辑/重蒸馏）
mentor distill --persona wang-laoshi --interactive
```

### Step 5：生成 Skill 文件

```bash
# 一次生成全部格式（推荐）
mentor generate --persona wang-laoshi --format all

# 只生成 Cursor 规则文件
mentor generate --persona wang-laoshi --format cursor

# 输出格式说明
# generic  → wang-laoshi.SKILL.md            通用 Markdown
# cursor   → wang-laoshi.mdc                 放入 .cursor/rules/ 即可
# claude   → wang-laoshi.claude.SKILL.md     Claude Code / Projects
# openclaw → wang-laoshi.openclaw.skill.md   OpenClaw AgentSkills
```

### Step 6：验证效果

```bash
# 多轮交互对话
mentor test --persona wang-laoshi

# 单次提问
mentor test --persona wang-laoshi --ask "帮我看看这个用户增长方案"
```

---

## 支持的 LLM

| 服务商 | 推荐模型 | api_base |
|--------|---------|----------|
| 智谱 GLM | `glm-4-flash` | `https://open.bigmodel.cn/api/paas/v4/` |
| DeepSeek | `deepseek-chat` | `https://api.deepseek.com/v1` |
| Qwen（百炼） | `qwen-turbo` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| MiniMax | `abab6.5s-chat` | `https://api.minimax.chat/v1` |
| OpenAI | `gpt-4o-mini` | 默认（无需 api_base） |
| Anthropic | `claude-3-haiku-20240307` | 默认 |
| Ollama（本地） | `ollama/llama3` | `http://localhost:11434` |

---

## 支持的数据源

| 平台 | 采集方式 | 状态 |
|------|---------|------|
| Markdown / Text | 本地文件递归读取 | ✅ |
| PDF | pdfplumber 解析 | ✅ |
| 微信 | WeChatMsg 导出 CSV | ✅ |
| 飞书 | 开放平台 API（群聊/私聊/文档） | ✅ |
| 钉钉 | API（文档）+ Playwright（消息） | ✅ |
| 如流 | API | 🔜 规划中 |

---

## 多平台 Skill 输出

生成的文件可直接放入对应平台使用：

### Cursor IDE

```bash
mentor generate --persona wang-laoshi --format cursor
cp .mentor/personas/wang-laoshi/wang-laoshi.mdc your-project/.cursor/rules/
```

重启 Cursor 后，AI 助手将以王老师的口吻给你反馈。

### Claude Code

```bash
mentor generate --persona wang-laoshi --format claude
cp .mentor/personas/wang-laoshi/wang-laoshi.claude.SKILL.md your-project/SKILL.md
```

### OpenClaw

```bash
mentor generate --persona wang-laoshi --format openclaw
# 将 .openclaw.skill.md 上传到 OpenClaw 平台
```

---

## CLI 命令参考

```
mentor init       初始化新 Persona 项目
mentor collect    采集导师数据（5 个平台）
mentor analyze    检查数据质量（评分 + 建议）
mentor distill    执行 7 层蒸馏（支持断点恢复）
mentor generate   生成 Skill 文件（4 种格式）
mentor test       与 Persona 多轮对话验收
mentor list       查看所有已有 Persona
mentor demo       内置 Sample Persona 演示（无需数据）
mentor doctor     诊断配置、数据与环境（可选 --check-llm）
mentor config     查看/修改全局配置（支持 --preset / --set）

# 全局选项
mentor --version  查看版本号
mentor --help     查看帮助
```

---

## Skill 质量评估（evals）

```bash
# 使用内置 sample_mentor 运行自动评估
python evals/run_eval.py --persona sample-mentor

# 评估维度（满分 10）
# 风格一致性（35%）：AI 语气是否符合导师 Persona
# 行为合规性（40%）：是否做了期望行为、避免了禁止行为
# 追问记忆层（25%）：是否主动追问进展、引用历史反馈
```

---

## 与同类项目的区别

| 维度 | colleague-skill | 导师.SKILL |
|------|-----------------|-----------|
| 定位 | 同事模拟 | **导师-学徒关系** |
| Persona 层数 | 5 层 | **7 层** |
| 学徒记忆 | ❌ | ✅ **记得你的项目、追问进展** |
| 指导风格建模 | ❌ | ✅ 引导式/直接式/放手程度 |
| 情感表达 | ❌ | ✅ 鼓励方式、不满信号 |
| 断点恢复 | ❌ | ✅ 每层 checkpoint |
| 输出平台 | 仅 Claude Code | **Cursor / Claude / OpenClaw / 通用** |
| LLM 支持 | 仅 Claude | **任意模型（litellm）** |
| evals 框架 | ❌ | ✅ LLM-as-judge 三维评分 |

---

## 开发

```bash
git clone https://github.com/SonicBotMan/mentor-skill
cd mentor-skill
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 格式检查
ruff check src/
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 文档

- [PRD.md](PRD.md) — 产品需求文档
- [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) — 技术设计
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — 执行计划与路线图
- [CHANGELOG.md](CHANGELOG.md) — 版本更新记录

---

## License

MIT License — 可商业使用，保留署名即可。

## 致谢

- [colleague-skill](https://github.com/soraliu/colleague-skill) — 开创了「人物蒸馏」方向的灵感来源
- [litellm](https://github.com/BerriAI/litellm) — 模型无关的 LLM 调用抽象层
