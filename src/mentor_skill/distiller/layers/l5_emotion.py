"""
L5Emotion — 情感表达层蒸馏（共情方式、鼓励与批评、情绪信号、情绪边界）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer5Emotion, Persona
from .base import BaseLayer


class L5Emotion(BaseLayer):
    """L5: 情感表达层 — 这位导师如何表达和处理情绪？"""

    LAYER_ID = 5
    LAYER_NAME = "情感表达层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        formatted_data = self._format_data(data, limit=60)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师的情感模式和共情方式

从对话中识别导师如何在情感层面与学徒互动。

### 提取要求

**共情方式（empathy_style）**：
- 当学徒感到困惑、压力大或沮丧时，导师通常如何回应？
- 例："先用一句话承认对方的处境（如'这个阶段确实很难'），然后快速切换到行动建议"
- 要基于数据中的实际表现，不要用通用描述

**鼓励方式（encouragement_style）**：
- 导师如何给正向反馈？是具体行为夸奖还是泛夸？
- 例："夸具体行为，如'这次你主动带了数据来讨论，比上次好很多'"，不说"你很棒"
- 如果数据中没有鼓励的例子，请留空

**不满/挫折信号（frustration_signs）**：
- 当导师感到不耐烦或不满时，有哪些语言/行为信号？
- 例：["沉默不接话", "重复说'你再想想'", "直接结束话题"]
- 只列举数据中有证据的

**表扬风格（praise_style）**：
- 导师夸人的方式，要与 encouragement_style 互补（一个说形式，一个说内容）
- 例："表扬时会引用具体数字或具体改变"

**情绪边界（emotional_boundary）**：
- 导师明显不愿触碰或讨论的话题、保持距离的方面
- 例：["不谈个人感情生活", "不讨论公司内部政治"]
- 如果没有证据，请输出空数组

### 输入数据
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "empathy_style": "共情方式描述",
  "encouragement_style": "鼓励方式描述",
  "frustration_signs": ["信号1", "信号2"],
  "praise_style": "表扬风格描述",
  "emotional_boundary": ["边界1", "边界2"]
}}
"""
        res = self.llm.call_json(prompt, system=system)
        persona.set_layer(5, Layer5Emotion(**res))
        return persona
