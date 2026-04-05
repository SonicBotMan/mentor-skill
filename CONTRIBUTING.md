# 贡献指南 (Contributing Guide)

感谢你对 mentor-skill 的关注！欢迎提交 Issue、PR 或建议。

---

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/SonicBotMan/mentor-skill
cd mentor-skill

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 安装浏览器（钉钉采集需要）
playwright install chromium
```

---

## 目录结构

```
src/mentor_skill/
├── cli.py              CLI 入口（所有命令）
├── config.py           配置加载
├── models/             数据模型（Persona + RawMessage）
├── collectors/         采集器（5 个平台）
├── analyzers/          数据分析
├── distiller/          蒸馏引擎 + 7 层实现
├── generator/          4 种格式生成器
└── llm/                LLM 抽象层

tests/                  单测（46 个）
evals/                  Skill 质量评估框架
examples/               示例数据
```

---

## 运行测试

```bash
# 全量测试
pytest tests/ -v

# 单模块测试
pytest tests/test_distiller.py -v

# 带覆盖率（需要 pytest-cov）
pytest tests/ --cov=src/mentor_skill --cov-report=term-missing
```

---

## 代码规范

使用 `ruff` 做格式检查：

```bash
# 检查
ruff check src/

# 自动修复
ruff check --fix src/

# 格式化
ruff format src/
```

提交前请确保 `ruff check src/` 0 警告。

---

## 提交新功能的步骤

### 1. 新增数据采集器

在 `src/mentor_skill/collectors/` 下创建新文件，继承 `BaseCollector`：

```python
from .base import BaseCollector
from mentor_skill.models.raw_message import RawMessage

class NewPlatformCollector(BaseCollector):
    SOURCE_NAME = "new_platform"

    def collect(self, mentor_name: str, **kwargs) -> list[RawMessage]:
        # 实现采集逻辑
        ...

    def validate_input(self, **kwargs) -> bool:
        # 验证必要的配置是否存在
        ...
```

然后在 `collectors/__init__.py` 中导出，并在 `cli.py` 的 `collect` 命令中注册。

### 2. 新增蒸馏层

在 `src/mentor_skill/distiller/layers/` 下创建 `l8_*.py`，继承 `BaseLayer`：

```python
from .base import BaseLayer
from mentor_skill.models.persona import Persona

class L8NewLayer(BaseLayer):
    LAYER_ID = 8
    LAYER_NAME = "新层名称"

    def distill(self, persona: Persona, data, interactive=False, **kwargs) -> Persona:
        system = self._get_system_prompt(persona)
        prompt = f"""
        从以下数据中提取...
        {self._format_data(data)}
        """
        result = self.llm.call_json(prompt, system=system)
        # 解析并更新 Persona
        ...
        return persona
```

记得在 `Persona` 模型中添加对应的层类型，并在 `engine.py` 中注册。

### 3. 新增输出格式

在 `src/mentor_skill/generator/` 下创建新文件：

```python
class NewPlatformGenerator:
    def generate(self, persona: Persona, output_path: Path) -> Path:
        # 生成对应格式的文件
        ...
        output_path.write_text(content, encoding="utf-8")
        return output_path
```

在 `generator/__init__.py` 中导出，并在 `cli.py` 的 `generate` 命令的 `generators` 字典中注册。

---

## PR 规范

- **PR 标题**：简洁描述改动，如 `feat: add Lark collector` / `fix: markdown glob pattern`
- **PR 描述**：说明改动原因、影响范围、如何测试
- **测试**：每个新功能都应有对应的测试，不减少已有测试通过率
- **文档**：如影响 CLI 用法，更新 README.md 和 CHANGELOG.md

---

## Issue 分类

| 标签 | 用途 |
|------|------|
| `bug` | 功能不符合预期 |
| `enhancement` | 功能改进建议 |
| `new-collector` | 请求新数据源支持 |
| `new-platform` | 请求新 Skill 输出格式 |
| `docs` | 文档问题 |
| `question` | 使用问题 |

---

## 本地验证完整 Pipeline

在 PR 合并前，建议本地跑一遍 sample 数据的端到端流程：

```bash
# 使用 sample 文档测试采集
mentor init --name test-mentor --template product
mentor collect --source markdown \
  --input examples/sample-mentor-docs/ \
  --persona test-mentor

mentor analyze --persona test-mentor --stats

# （可选，需要 API Key）
mentor distill --persona test-mentor
mentor generate --persona test-mentor --format all
mentor test --persona test-mentor --ask "帮我看看这个方案"
```

---

## 联系

- GitHub Issues: [issues](https://github.com/SonicBotMan/mentor-skill/issues)
- 作者: [@SonicBotMan](https://github.com/SonicBotMan)
