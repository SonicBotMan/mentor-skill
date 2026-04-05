"""
QualityAssessor — 蒸馏质量评估器

计算数据多样性、覆盖度，并给出一个 0-100 的分值建议。
"""
from __future__ import annotations


from .stats import AnalysisStats


class QualityAssessor:
    """质量得分计算 (0-100)"""

    def assess(self, stats: AnalysisStats) -> int:
        score = 0

        # 1. 数量权重 (Max 30)
        # 1000 条及以上满分
        score += min(30, (stats.mentor_messages / 1000) * 30)

        # 2. 高价值权重 (Max 40)
        # 200 条及以上满分，通常导师的一条长回复更有价值
        score += min(40, (stats.high_value_count / 200) * 40)

        # 3. 多样性权重 (Max 30)
        # 覆盖 3 个及以上平台满分
        sources = len(stats.source_distribution)
        if sources >= 3:
            score += 30
        elif sources == 2:
            score += 20
        elif sources == 1:
            score += 10

        return int(score)

    def get_recommendation(self, score: int) -> str:
        if score > 80:
            return "🚀 极佳：数据非常充分，可以一键蒸馏。"
        if score > 50:
            return "⚡ 良好：数据覆盖度不错，建议进行交互式蒸馏。"
        if score > 25:
            return "🚧 欠缺：数据量较少，建议继续补充更多对话记录或文档资料。"
        return "❌ 危险：数据严重不足，蒸馏效果可能非常差。"
