"""
L1Identity — 基础身份层蒸馏（姓名、角色、背景、性格、口头禅、红线）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer1Identity, Persona
from .base import BaseLayer


class L1Identity(BaseLayer):
    """L1: 基础身份层 — 这位导师是谁？"""

    LAYER_ID = 1
    LAYER_NAME = "基础身份层"

    def distill(
        self,
        persona: Persona,
        data: List[Any],
        interactive: bool = False,
        **kwargs
    ) -> Persona:
        formatted_data = self._format_data(data, limit=40)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师的基础身份信息

从以下对话和文档数据中，提取这位导师的核心身份特征。

### 提取要求
- **姓名**：数据中明确出现的名字或称谓（如"王老师"）
- **角色**：职业头衔或功能角色，如"产品总监"、"技术导师"，不超过 3 个
- **背景**：工作经历、行业背景，只提取有直接证据的内容，2-3 句话
- **性格**：从对话中观察到的性格特征（注意：用行为描述，不用形容词堆砌）
- **口头禅**：数据中实际出现的、具有辨识度的词汇或短语，至少 3 个，越原汁原味越好
- **行为红线**：导师明确拒绝做的事、反复强调的底线，如"不接受没有数据支撑的判断"

### 注意
- 只能提取数据中有直接证据的信息，不能基于常识或假设填充
- 口头禅必须是数据中原文出现的词句，不能是你总结的
- 如果没有足够证据，字段请留空或填空数组

### 输入数据
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "name": "导师姓名",
  "role": ["角色1", "角色2"],
  "background": "背景描述",
  "personality": "性格特征（基于行为的描述）",
  "catchphrases": ["原话口头禅1", "原话口头禅2", "原话口头禅3"],
  "red_lines": ["行为红线1", "行为红线2"]
}}
"""
        res = self.llm.call_json(prompt, system=system)
        identity = Layer1Identity(**res)
        persona.set_layer(1, identity)
        return persona
