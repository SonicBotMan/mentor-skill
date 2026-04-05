"""
BaseLayer — 蒸馏层的基类
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List

from mentor_skill.llm.base import LLMClient
from mentor_skill.models.persona import Persona


class BaseLayer(ABC):
    """
    Persona 蒸馏层的抽象基类

    每个层负责：
      1. 接收输入数据 (RawMessage, DialogPair)
      2. 接收已蒸馏的 Persona 前序层作为上下文
      3. 生成本层的 Prompt 并调用 LLM
      4. 解析 LLM 返回并更新 Persona
    """

    LAYER_ID: int = 0
    LAYER_NAME: str = "Base"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    @abstractmethod
    def distill(
        self,
        persona: Persona,
        data: List[Any],
        interactive: bool = False,
        **kwargs
    ) -> Persona:
        """执行本层蒸馏"""
        ...

    # ── 系统 Prompt ──────────────────────────────────────────────────

    def _get_system_prompt(self, persona: Persona) -> str:
        """获取系统 Prompt，包含任务背景 + 防幻觉约束"""
        mentor_name = persona.mentor_name or persona.persona_name
        prior = self._format_prior_layers(persona)
        prior_section = f"\n\n## 已提取的前序层信息（供参考，避免重复）\n{prior}" if prior else ""

        return (
            f"你是一位专业的导师人格蒸馏师。你正在对 [{mentor_name}] 进行深度 Persona 蒸馏。\n\n"
            "## 核心原则\n"
            "1. **只提取数据中有直接证据的信息**——禁止基于通用知识或假设填充。"
            "如果数据中没有足够证据，输出空字符串 \"\" 或空数组 []，不要编造。\n"
            "2. **具体优于抽象**——尽量引用数据中出现的原话、用词或场景，而非抽象描述。\n"
            "3. **差异化优先**——提取这位导师与普通人不同的独特特征，而非通用描述。\n"
            f"4. **不重复前序层已提取的内容**——专注本层职责。"
            f"{prior_section}"
        )

    # ── 层间上下文 ────────────────────────────────────────────────────

    def _format_prior_layers(self, persona: Persona) -> str:
        """将已蒸馏的前序层整理为简洁摘要，避免重复提取"""
        if not persona.layers:
            return ""

        lines = []
        layer_labels = {
            1: "L1 基础身份",
            2: "L2 知识专业",
            3: "L3 思维框架",
            4: "L4 沟通风格",
            5: "L5 情感表达",
            6: "L6 指导关系",
        }
        for lid in sorted(persona.layers.keys()):
            if lid >= self.LAYER_ID:
                continue
            label = layer_labels.get(lid, f"L{lid}")
            layer_data = persona.layers[lid]
            # 取模型的 dict，只展示最关键字段，避免上下文太长
            if hasattr(layer_data, "model_dump"):
                d = layer_data.model_dump()
            else:
                d = dict(layer_data) if hasattr(layer_data, "items") else {}
            # 保留前 5 个非空字段
            summary_parts = []
            for k, v in list(d.items())[:5]:
                if v:
                    v_str = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
                    summary_parts.append(f"{k}: {v_str[:80]}")
            if summary_parts:
                lines.append(f"[{label}] " + "  |  ".join(summary_parts))
        return "\n".join(lines)

    # ── 数据格式化 ────────────────────────────────────────────────────

    def _format_data(self, data: List[Any], limit: int = 60) -> str:
        """
        格式化蒸馏输入数据：
        - 优先展示高价值消息（长消息，is_high_value）
        - DialogPair 以 Q/A 形式展示
        - 包含时间戳帮助 LLM 理解时序关系
        """
        from mentor_skill.models.raw_message import RawMessage
        from mentor_skill.analyzers.extractor import DialogPair

        # 分类：对话对 + 高价值消息 + 普通消息
        pairs: list[DialogPair] = []
        high_value: list[RawMessage] = []
        normal: list[RawMessage] = []

        for item in data:
            if isinstance(item, DialogPair):
                pairs.append(item)
            elif isinstance(item, RawMessage):
                if item.is_high_value and item.is_mentor:
                    high_value.append(item)
                else:
                    normal.append(item)

        # 高价值消息按长度降序
        high_value.sort(key=lambda m: len(m.content), reverse=True)

        # 按优先级组装，总条数不超过 limit
        selected: list[Any] = []
        for pool in (pairs, high_value, normal):
            remaining = limit - len(selected)
            if remaining <= 0:
                break
            selected.extend(pool[:remaining])

        lines = []
        for i, item in enumerate(selected):
            if isinstance(item, DialogPair):
                ts = item.answer.timestamp.strftime("%m-%d %H:%M") if hasattr(item.answer.timestamp, "strftime") else ""
                lines.append(
                    f"[Q{i+1}] {item.question.sender}: {item.question.content}\n"
                    f"[A{i+1}] {item.answer.sender} ({ts}): {item.answer.content}"
                )
            elif isinstance(item, RawMessage):
                ts = item.timestamp.strftime("%m-%d %H:%M") if hasattr(item.timestamp, "strftime") else ""
                hv = "★" if item.is_high_value else " "
                lines.append(f"[{hv}{i+1}] {item.sender} ({ts}): {item.content}")

        return "\n\n".join(lines)

    def _format_data_text_only(self, data: List[Any], limit: int = 40) -> str:
        """只取导师的文本消息（纯文本，无格式），用于语言特征分析"""
        from mentor_skill.models.raw_message import RawMessage

        mentor_msgs = [
            m for m in data
            if isinstance(m, RawMessage) and m.is_mentor and len(m.content) > 20
        ]
        mentor_msgs.sort(key=lambda m: len(m.content), reverse=True)
        return "\n---\n".join(m.content for m in mentor_msgs[:limit])
