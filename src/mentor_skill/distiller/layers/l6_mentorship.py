"""
L6Mentorship — 指导关系层蒸馏（带人策略、授权模型、反馈频率、成长期望）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer6Mentorship, Persona
from .base import BaseLayer


class L6Mentorship(BaseLayer):
    """L6: 指导关系层 — 这位导师如何带人？"""

    LAYER_ID = 6
    LAYER_NAME = "指导关系层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        formatted_data = self._format_data(data, limit=80)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师的指导策略和带人方式

分析导师与学徒互动中体现的指导模式和关系管理。

### 提取要求

**指导风格（mentoring_style）**：
- 核心问题：导师是给鱼还是给渔？是自己给答案还是引导学徒自己找到答案？
- 区分不同情境：什么时候会直接给建议，什么时候会用反问引导？
- 1-3句话，有具体场景描述

**授权程度（autonomy_grant）**：
- 导师给学徒多大的自主空间？
- 例："给框架和方向，具体方案让学徒自己想；但如果方向根本性错误，会直接纠正"

**反馈节奏（feedback_cadence）**：
- 导师多久给一次反馈？反馈的触发条件是什么？
- 例："主动追问进展，不等学徒来汇报；每次反馈必须有具体的下一步行动项"

**典型场景处理（typical_scenarios）**：
- 从数据中提取 2-3 个典型的指导场景及其处理方式
- 格式：{{"场景名": "处理方式描述"}}
- 例：{{"学徒方向跑偏": "先问'你做这个是为了解决什么问题'，让学徒自己发现问题"}}

**成长期望（growth_expectation）**：
- 导师对学徒的长期发展有什么期望？
- 如果没有明确证据，留空

### 输入数据
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "mentoring_style": "指导风格描述",
  "teaching_rhythm": "反馈节奏描述",
  "autonomy_grant": "授权程度描述",
  "typical_scenarios": {{
    "场景名1": "处理方式1",
    "场景名2": "处理方式2"
  }},
  "growth_expectation": "成长期望描述"
}}
"""
        res = self.llm.call_json(prompt, system=system)
        persona.set_layer(6, Layer6Mentorship(**res))
        return persona
