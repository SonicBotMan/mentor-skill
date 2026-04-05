"""
L2Knowledge — 知识与专业层蒸馏（领域深度、核心见解、工具偏好、边界）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer2Knowledge, Persona
from .base import BaseLayer


class L2Knowledge(BaseLayer):
    """L2: 知识与专业层 — 这位导师知道什么？精通什么？"""

    LAYER_ID = 2
    LAYER_NAME = "知识与专业层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        formatted_data = self._format_data(data, limit=60)
        system = self._get_system_prompt(persona)

        # 获取 L1 中的角色信息辅助判断专业边界
        l1 = persona.layers.get(1)
        role_hint = ""
        if l1 and hasattr(l1, "role"):
            role_hint = f"（已知该导师的角色是：{', '.join(l1.role)}）"

        prompt = f"""
## 任务：提取导师的知识体系和专业能力{role_hint}

从以下数据中，识别导师在哪些领域有深度见解，以及哪些是其独特的核心观点。

### 提取要求

**核心领域（domains）**：
- 导师反复讨论、有深度见解的 2-5 个专业方向
- 用具体领域名称，不用宽泛词（不要用"技术"，要用"系统架构"或"分布式系统"）

**核心见解（key_insights）**：
- 这是最重要的字段——提取导师独有的、有观点性的判断，不是通用知识
- 判断标准：如果换个行业普通人也会说，就不算是导师的独特见解
- 格式：每条见解用一句完整句子表达，可以包含反常识或有争议的观点
- 至少 3 条，最多 8 条

**知识边界（knowledge_boundary）**：
- 导师在数据中明确回避、不擅长或承认不懂的方向
- 只提取有直接证据的内容，不猜测

**常用工具（preferred_tools）**：
- 数据中具体提到的工具、平台、框架

### 输入数据
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "domains": ["具体领域1", "具体领域2"],
  "key_insights": [
    "独特核心见解1（一句完整的观点性陈述）",
    "独特核心见解2",
    "独特核心见解3"
  ],
  "knowledge_boundary": ["不擅长的领域1"],
  "preferred_tools": ["工具1", "工具2"]
}}
"""
        res = self.llm.call_json(prompt, system=system)
        knowledge = Layer2Knowledge(**res)
        persona.set_layer(2, knowledge)
        return persona
