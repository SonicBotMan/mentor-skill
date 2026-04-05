"""
L4Communication — 沟通风格层蒸馏（语气、结构、修辞、Emoji、回复长度、典型句式）
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer4Communication, Persona
from .base import BaseLayer


class L4Communication(BaseLayer):
    """L4: 沟通风格层 — 这位导师怎么说话？"""

    LAYER_ID = 4
    LAYER_NAME = "沟通风格层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        # 语言特征分析用纯文本，保留原汁原味
        text_data = self._format_data_text_only(data, limit=50)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师的语言风格和沟通模式

仔细阅读以下导师的原始消息，分析其语言特征。

### 提取要求

**语气（tone）**：
- 用具体描述，不用空洞词汇（不要"专业严肃"，要"不寒暄，直入主题；批评时用反问而非否定"）
- 1-2句话

**结构（structure）**：
- 导师的典型回复是什么结构？
- 例："先提反问→等待回应→给方向（不给答案）" 或 "问题拆解→逐一分析→行动项"

**修辞手法（rhetoric）**：
- 导师喜欢用什么修辞？反问？比喻？举例子？直接举数据？
- 只列举数据中有证据的，不猜测

**Emoji 使用（emoji_usage）**：
- "none"（不用）、"sparse"（偶尔用）、"moderate"（经常用）
- 如果有常用的具体 Emoji，列出来

**典型句式（typical_response_examples）**：
- 从原文中直接摘录 2-3 句最具代表性的回复句式（原话，非总结）
- 这是最重要的字段，要从原文中直接摘抄

**回复长度（response_length）**：
- "brief"（<50字）、"medium"（50-200字）、"detailed"（>200字）
- 或描述不同场景下的差异

### 导师原始消息（用于语言分析）
---
{text_data}
---

### 输出格式（JSON）
{{
  "tone": "语气描述",
  "structure": "回复结构描述",
  "rhetoric": ["修辞手法1", "修辞手法2"],
  "emoji_usage": "none/sparse/moderate",
  "typical_response_examples": ["原话示例1", "原话示例2"],
  "response_length": "brief/medium/detailed 或具体描述"
}}
"""
        res = self.llm.call_json(prompt, system=system)
        persona.set_layer(4, Layer4Communication(**res))
        return persona
