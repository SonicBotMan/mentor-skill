"""
L3Thinking — 思维框架层蒸馏（问题解决路径、决策逻辑、追问风格、认知偏差）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer3Thinking, Persona
from .base import BaseLayer


class L3Thinking(BaseLayer):
    """L3: 思维框架层 — 这位导师怎么想问题？"""

    LAYER_ID = 3
    LAYER_NAME = "思维框架层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        formatted_data = self._format_data(data, limit=80)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师的思维模式和决策框架

观察导师在对话中如何分析问题、做出判断、引导学徒思考。

### 提取要求

**问题解决路径（problem_solving）**：
- 导师遇到一个问题时，第一步、第二步通常做什么？
- 例："先追问问题的根因，确认假设是否成立，再讨论解决方案"
- 用1-2句话，描述具体的行为序列

**决策框架（decision_framework）**：
- 导师在做判断时依赖什么？数据？直觉？原则？第一性原理？
- 例："优先看用户行为数据；数据不足时看竞品；没有竞品参考时回归用户第一性原理"

**追问风格（question_style）**：
- 导师如何向学徒提问？是开放式？苏格拉底式？还是直接指出问题？
- 提取1-2个具有代表性的追问句式（如从数据中找到的原话）

**反馈模式（feedback_pattern）**：
- 导师通常在什么情况下给正面反馈？什么情况下给挑战性反馈？
- 反馈的典型结构是什么？

**认知偏好（common_patterns）**：
- 导师反复使用的思维模式或分析框架，如"第一性原理"、"PMF 优先"
- 2-4个，基于数据中的反复出现

**偏见（bias）**：
- 导师明显偏向的立场或方法论，不是贬义，只是客观描述
- 例："强调数据驱动而相对轻视直觉"，可以为空数组

### 输入数据
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "problem_solving": "问题解决路径描述",
  "decision_framework": "决策框架描述",
  "question_style": "追问风格描述（可含原话示例）",
  "feedback_pattern": "反馈模式描述",
  "common_patterns": ["思维模式1", "思维模式2"],
  "bias": ["认知偏好1"]
}}
"""
        res = self.llm.call_json(prompt, system=system)
        persona.set_layer(3, Layer3Thinking(**res))
        return persona
