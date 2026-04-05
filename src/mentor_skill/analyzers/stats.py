"""
StatsAnalyzer — 数据统计分析器

统计数据源分布、消息数量、导师/学徒比例、平均长度等。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from mentor_skill.models.raw_message import RawMessage


@dataclass
class AnalysisStats:
    total_messages: int = 0
    mentor_messages: int = 0
    apprentice_messages: int = 0
    source_distribution: Dict[str, int] = field(default_factory=dict)
    avg_mentor_length: float = 0.0
    avg_apprentice_length: float = 0.0
    top_senders: Dict[str, int] = field(default_factory=dict)
    # 高价值消息统计
    high_value_count: int = 0


class StatsAnalyzer:
    """计算统计指标"""

    def analyze(self, messages: List[RawMessage]) -> AnalysisStats:
        stats = AnalysisStats()
        if not messages:
            return stats

        stats.total_messages = len(messages)

        mentor_len_sum = 0
        appr_len_sum = 0

        for m in messages:
            # 数据源统计
            stats.source_distribution[m.source] = stats.source_distribution.get(m.source, 0) + 1

            # 发送者统计
            stats.top_senders[m.sender] = stats.top_senders.get(m.sender, 0) + 1

            # 导师/学徒统计
            if m.is_mentor:
                stats.mentor_messages += 1
                mentor_len_sum += len(m.content)
                if len(m.content) > 50:
                    stats.high_value_count += 1
            else:
                stats.apprentice_messages += 1
                appr_len_sum += len(m.content)

        # 计算平均长度
        if stats.mentor_messages > 0:
            stats.avg_mentor_length = mentor_len_sum / stats.mentor_messages
        if stats.apprentice_messages > 0:
            stats.avg_apprentice_length = appr_len_sum / stats.apprentice_messages

        return stats
