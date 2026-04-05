"""
L7ApprenticeMemory — 学徒记忆层蒸馏（⭐ 最核心差异化功能）

这一层让 AI 导师"记得"：
  - 你现在在做什么项目
  - 上次反馈了什么
  - 你有没有真的改
  - 下次见面要追问什么
"""
from __future__ import annotations

from typing import Any, List

from mentor_skill.models.persona import Layer7ApprenticeMemory, Persona
from .base import BaseLayer


class L7ApprenticeMemory(BaseLayer):
    """L7: 学徒记忆层 — 导师记得你什么？"""

    LAYER_ID = 7
    LAYER_NAME = "学徒记忆层"

    def distill(self, persona: Persona, data: List[Any], **kwargs) -> Persona:
        # L7 使用全部数据（限 100 条），时序信息尤为重要
        formatted_data = self._format_data(data, limit=100)
        system = self._get_system_prompt(persona)

        prompt = f"""
## 任务：提取导师对学徒的记忆（⭐ 这是最重要的层）

这一层的目标是让 AI 导师能够"记住"过往发生的事，在下次对话时主动追问进展、
检查学徒有没有真的行动。这是普通 AI 助手没有、但真实导师有的最关键能力。

### 提取要求

**正在进行的项目（active_projects）**：
- 学徒在数据中提到的、还没完成的工作或项目
- 每个项目包含：名称、当前状态、上次讨论的时间（如果有）
- 最多 5 个，按最近讨论时间排序

**开放承诺（open_commitments）**：
- 学徒在对话中答应要做的事，或导师要提供的东西，但还没有后续确认
- 例：学徒说"下周我带数据来"——这是一个开放承诺
- 格式：任务描述 + 谁负责 + 截止时间（如果有）

**历史关键反馈（feedback_history）**：
- 导师给过的最重要的建议/批评，尤其是学徒多次犯同样错误的
- 格式：话题 + 核心建议内容
- 按重要性排序，最多 5 条

**学徒档案（apprentice_profile）**：
- 从对话中观察到的学徒特征：名字（如果有）、背景、优势、常见盲点/弱点
- 这帮助 AI 导师个性化指导风格

**追问清单（next_check_ins）**：
- 根据以上信息，下次对话时 AI 导师应该主动追问的问题
- 例：["用户访谈做了吗，结论是什么？", "上次说要改的数据分析有没有更新？"]
- 2-4 条，具体可执行

### 注意
- 时序很重要：请关注消息的时间戳，理解"过去说了什么"和"现在还没做"
- 只提取数据中有证据的信息，不要猜测未来

### 输入数据（包含时间戳，请关注时序）
---
{formatted_data}
---

### 输出格式（JSON）
{{
  "active_projects": [
    {{"name": "项目名称", "status": "当前状态", "last_discussed": "YYYY-MM-DD 或 null"}}
  ],
  "open_commitments": [
    {{"task": "承诺内容", "owner": "学徒/导师", "due": "截止时间或 null"}}
  ],
  "feedback_history": [
    {{"topic": "反馈话题", "advice": "核心建议内容", "times_repeated": 1}}
  ],
  "apprentice_profile": {{
    "name": "学徒名字（如果有）",
    "background": "背景",
    "strengths": ["优势1"],
    "weaknesses": ["盲点/弱点1"]
  }},
  "next_check_ins": [
    "下次应追问的具体问题1",
    "下次应追问的具体问题2"
  ]
}}
"""
        res = self.llm.call_json(prompt, system=system)
        persona.set_layer(7, Layer7ApprenticeMemory(**res))
        return persona
