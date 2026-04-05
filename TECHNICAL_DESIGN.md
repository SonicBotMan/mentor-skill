# 技术设计文档 (Technical Design)

> mentor-skill v0.2

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (typer)                             │
│  init │ collect │ analyze │ distill │ generate │ test │ list   │
│  demo │ config                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Collectors  │  │  Analyzers   │  │   Distiller  │
  │  markdown   │  │  DataCleaner │  │  Engine (L1-7)│
  │  pdf        │  │  StatsAnalyz │  │  + checkpoint │
  │  wechat     │  │  QualityAssessor│  │  + interactive│
  │  feishu     │  │  DialogExtract│  └──────┬───────┘
  │  dingtalk   │  └──────────────┘         │
  └──────┬──────┘                           ▼
         │                          ┌──────────────┐
         ▼                          │  LLM Client  │
  ┌─────────────┐                   │  (litellm)   │
  │  RawMessage  │                   └──────────────┘
  │  (dataclass) │                         │
  └─────────────┘                          ▼
                                   ┌──────────────┐
                                   │   Persona    │
                                   │  (7 layers)  │
                                   └──────┬───────┘
                                          │
                         ┌────────────────┼──────────────────┐
                         ▼                ▼                  ▼
                  ┌─────────────┐ ┌────────────┐  ┌────────────────┐
                  │ SkillMD     │ │CursorRule  │  │ OpenClaw /     │
                  │ Generator   │ │Generator   │  │ Claude Skill   │
                  └─────────────┘ └────────────┘  └────────────────┘
```

---

## 2. 核心模块

### 2.1 数据模型

#### RawMessage（采集层）

```python
@dataclass
class RawMessage:
    source: str          # 数据来源平台
    timestamp: datetime
    sender: str
    content: str
    is_mentor: bool = False
    context: dict        # 群名、话题等上下文
    metadata: dict       # 原始元数据

    @property
    def is_high_value(self) -> bool:
        return self.word_count > 50  # 超过50字视为高价值
```

**设计决策**：使用 dataclass 而非 Pydantic，因为采集层是"脏数据"入口，宽松的 dataclass 避免校验失败阻塞采集。进入蒸馏层后再用 Pydantic 严格校验。

#### Persona（蒸馏层）

```python
class Persona(BaseModel):
    version: str
    distilled_at: str
    distilled_by: str    # 使用的 LLM 模型名称
    persona_name: str
    source_stats: dict
    layers: dict[int, Any]  # 层 ID → 层数据对象
```

7 个层类型通过 `LAYER_CLASSES: dict[int, type]` 映射，反序列化时自动还原为 Pydantic 对象。

### 2.2 采集器

所有采集器继承 `BaseCollector`：

```python
class BaseCollector(ABC):
    def collect(self, **kwargs) -> list[RawMessage]: ...
    def validate_input(self, **kwargs) -> bool: ...
```

| 采集器 | 策略 |
|--------|------|
| MarkdownCollector | 遍历 `**/*.md` / `**/*.txt`，解析 YAML frontmatter |
| PDFCollector | pdfplumber 提取文本，按页分割 |
| WechatCollector | 解析 WeChatMsg 导出的 CSV 格式 |
| FeishuCollector | 飞书开放平台 API，3 层用户搜索 fallback |
| DingtalkCollector | 文档用 API，消息用 Playwright 浏览器自动化 |

### 2.3 分析器

```
DataCleaner     → 过滤短消息、去重、标准化编码
StatsAnalyzer   → 统计导师消息数、高价值消息数、对话轮次
QualityAssessor → 综合评分（0-100），给出采集建议
DialogExtractor → 提取 Q&A 对话对（时间窗口 + 发送者模式匹配）
```

**DialogExtractor 策略**：向前查找最近一条非导师消息作为 Q，超过 `gap_seconds`（默认 30 分钟）则不配对，避免跨对话的错误匹配。

### 2.4 蒸馏引擎

```
DistillationEngine
  ├── load_checkpoint()       # 读取断点
  ├── _save_checkpoint()      # 每层完成后保存
  ├── run()                   # 主流程
  │     ├── 过滤已完成层
  │     ├── for layer in pending_layers:
  │     │     ├── layer.distill(persona, data)
  │     │     ├── _save_checkpoint()
  │     │     └── _interactive_confirm()  # --interactive 时
  │     └── 全部完成后删除 checkpoint
  └── _interactive_confirm()  # y/e/r 三种操作
```

**每层 Prompt 模板**：
- System：`你是专业的导师人格分析师，正在对 {name} 进行人格蒸馏`
- User：格式化数据（取前 N 条高价值消息）+ 要求 JSON 输出的结构
- 解析：先尝试直接解析 JSON，失败则正则提取 `{...}` 块

### 2.5 LLM 抽象层

基于 `litellm` 实现模型无关调用：

```python
class LLMClient:
    def call(self, prompt, system, response_format) -> str
    def call_json(self, prompt, system) -> dict   # 带 JSON 解析和重试
```

**JSON 模式降级**：对非 OpenAI 模型（GLM、DeepSeek 等），在 prompt 末尾追加"请严格输出 JSON 格式"而非使用 `response_format={"type":"json_object"}`。

### 2.6 生成器

| 生成器 | 输出 | 特点 |
|--------|------|------|
| SkillMDGenerator | 通用 `.SKILL.md` | 7层结构化 Markdown |
| CursorRuleGenerator | `.mdc` | frontmatter + alwaysApply |
| ClaudeSkillGenerator | `.claude.SKILL.md` | `<rules>` 标签 + 项目表格 |
| OpenClawSkillGenerator | `.openclaw.skill.md` | YAML frontmatter + 能力声明 |

---

## 3. 配置系统

配置优先级：环境变量 > `~/.mentor/config.yaml` > `config.yaml.example` 默认值

```yaml
project:
  name: "my-mentor"
  data_dir: ".mentor/data"
  output_dir: ".mentor/output"
  persona_dir: ".mentor/personas"

llm:
  model: "glm-4-flash"
  api_key: "YOUR_KEY"
  api_base: "https://open.bigmodel.cn/api/paas/v4/"
  temperature: 0.3
  max_tokens: 4096
  timeout: 120
```

---

## 4. 目录结构

```
mentor-skill/
├── src/mentor_skill/
│   ├── __init__.py          # 版本号
│   ├── cli.py               # 所有 CLI 命令
│   ├── config.py            # 配置加载/保存
│   ├── models/
│   │   ├── persona.py       # 7层 Persona 模型
│   │   └── raw_message.py   # 原始消息模型
│   ├── collectors/          # 数据采集器（5个平台）
│   ├── analyzers/           # 数据分析（清洗/统计/质量/对话提取）
│   ├── distiller/
│   │   ├── engine.py        # 蒸馏引擎（断点/交互）
│   │   └── layers/          # L1-L7 七层实现
│   ├── generator/           # 4种输出格式生成器
│   └── llm/
│       └── base.py          # LLM 调用抽象（litellm）
├── tests/                   # 46 个单测
├── evals/                   # 评估框架（LLM-as-judge）
│   ├── metrics.py
│   ├── run_eval.py
│   ├── personas/sample_mentor/
│   └── test_cases/
├── .github/workflows/       # CI/CD
├── pyproject.toml
├── config.yaml.example
├── CHANGELOG.md
├── PRD.md
├── TECHNICAL_DESIGN.md
└── EXECUTION_PLAN.md
```

---

## 5. 关键技术决策

### 5.1 为什么用 litellm

litellm 提供统一接口调用 100+ LLM，避免为每个厂商写适配代码。对于中文场景下常用的 GLM、DeepSeek、Qwen 等，litellm 均有良好支持。

### 5.2 为什么不用 LangChain

LangChain 太重，抽象层过多，调试困难。mentor-skill 的 LLM 调用模式简单（单轮 Prompt → 解析 JSON），直接用 litellm 更透明。

### 5.3 断点恢复设计

每层蒸馏平均耗时 5-15 秒，7 层全程约 1-2 分钟。但在网络不稳定或 API 限流时可能中途失败。断点设计：
- 以层为粒度保存（不是每次 LLM 调用），避免频繁 IO
- 保存完整 Persona 快照（而非 diff），简化恢复逻辑
- 全部完成后删除，避免误 resume

### 5.4 多平台输出策略

不同平台对 system prompt 的解析方式不同：
- **Cursor**：读取 `.cursor/rules/*.mdc` 作为 context，需要 frontmatter 声明 `alwaysApply`
- **Claude Code**：SKILL.md 放在项目根目录，使用 `<rules>` XML 标签
- **OpenClaw**：YAML frontmatter 声明 `skill.spec`、`activation`、`capabilities`

各适配器独立实现，共享同一个 `Persona` 对象作为输入。

---

## 6. 测试策略

| 层次 | 工具 | 覆盖 |
|------|------|------|
| 单元测试 | pytest | 采集器、分析器、蒸馏层、生成器 |
| 集成测试 | pytest + mock LLM | 完整 pipeline 端到端（无真实 API 调用） |
| 质量评估 | LLM-as-judge | evals 框架，三维评分 |

**Mock 策略**：蒸馏层测试使用 `MagicMock` 替换 `LLMClient`，`call_json` 返回预设 JSON，避免真实 API 调用。
