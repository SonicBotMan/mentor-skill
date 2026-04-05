"""
DialogExtractor — 对话对提取器

负责将消息流按发送时间、发送者关系提取 Q&A（学徒问 → 导师答）对话对。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from mentor_skill.models.raw_message import RawMessage


@dataclass
class DialogPair:
    """一组 Q&A 对话对"""
    question: RawMessage
    answer: RawMessage
    context_before: List[RawMessage] = field(default_factory=list)  # 前文上下文
    topic: str = ""                                               # 提取的话题（可选）

    def to_summary(self) -> str:
        s = f"Q ({self.question.sender}): {self.question.content}\n"
        s += f"A ({self.answer.sender}): {self.answer.content}\n"
        return s


class DialogExtractor:
    """提取对话对及其上下文"""

    def __init__(self, gap_seconds: int = 1800, context_window: int = 5):
        self.gap_seconds = gap_seconds   # 超过 30 分钟视为新对话
        self.context_window = context_window

    def extract(self, messages: List[RawMessage], mentor_name: str) -> List[DialogPair]:
        """
        全量提取 Q&A

        策略：
          1. 按时间排序。
          2. 当发现导师的回复 (is_mentor=True) 时，
             回找前面的非导师消息作为提问。
          3. 如果时间差过大则重置。
        """
        if not messages: return []

        # 排序
        sorted_msgs = sorted(messages, key=lambda x: x.timestamp)

        pairs = []
        for i, m in enumerate(sorted_msgs):
            # 找到一条导师的消息作为 "Answer"
            if m.is_mentor:
                # 寻找最近一条学徒（非导师）的消息作为 "Question"
                q_idx = -1
                for j in range(i-1, -1, -1):
                    prev = sorted_msgs[j]

                    # 检查时间间隔是否过大
                    if (m.timestamp - prev.timestamp).total_seconds() > self.gap_seconds:
                        break

                    if not prev.is_mentor:
                        q_idx = j
                        break

                if q_idx != -1:
                    q_msg = sorted_msgs[q_idx]
                    # 提取前文上下文（排除 Q 消息）
                    start_ctx = max(0, q_idx - self.context_window)
                    context = sorted_msgs[start_ctx : q_idx]

                    pairs.append(DialogPair(
                        question=q_msg,
                        answer=m,
                        context_before=context
                    ))

        return pairs
