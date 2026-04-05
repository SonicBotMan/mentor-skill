"""
测试 analyzers 模块：DataCleaner / StatsAnalyzer / QualityAssessor / DialogExtractor
"""
from __future__ import annotations

import pytest

from mentor_skill.analyzers import DataCleaner, StatsAnalyzer, QualityAssessor, DialogExtractor
from mentor_skill.models.raw_message import RawMessage


class TestDataCleaner:
    def test_removes_short_messages(self, sample_messages):
        from datetime import datetime, timezone
        short_msg = RawMessage(
            source="markdown",
            timestamp=datetime.now(timezone.utc),
            sender="王老师",
            content="好",   # 1字，低于清洗阈值
            is_mentor=True,
        )
        cleaner = DataCleaner()
        result = cleaner.clean(sample_messages + [short_msg])
        contents = [m.content for m in result]
        assert "好" not in contents

    def test_keeps_high_value_messages(self, sample_messages):
        cleaner = DataCleaner()
        result = cleaner.clean(sample_messages)
        assert any(m.is_high_value for m in result)

    def test_empty_input_returns_empty(self):
        cleaner = DataCleaner()
        assert cleaner.clean([]) == []


class TestStatsAnalyzer:
    def test_counts_mentor_messages(self, sample_messages):
        cleaner = DataCleaner()
        cleaned = cleaner.clean(sample_messages)
        stats = StatsAnalyzer().analyze(cleaned)
        assert stats.mentor_messages >= 1
        assert stats.total_messages >= 1

    def test_high_value_count(self, sample_messages):
        cleaner = DataCleaner()
        cleaned = cleaner.clean(sample_messages)
        stats = StatsAnalyzer().analyze(cleaned)
        assert stats.high_value_count >= 1


class TestQualityAssessor:
    def test_score_range(self, sample_messages):
        cleaner = DataCleaner()
        cleaned = cleaner.clean(sample_messages)
        stats = StatsAnalyzer().analyze(cleaned)
        score = QualityAssessor().assess(stats)
        assert 0 <= score <= 100

    def test_recommendation_not_empty(self, sample_messages):
        cleaner = DataCleaner()
        cleaned = cleaner.clean(sample_messages)
        stats = StatsAnalyzer().analyze(cleaned)
        score = QualityAssessor().assess(stats)
        rec = QualityAssessor().get_recommendation(score)
        assert isinstance(rec, str) and len(rec) > 0


class TestDialogExtractor:
    def test_extracts_qa_pairs(self, sample_messages):
        extractor = DialogExtractor()
        pairs = extractor.extract(sample_messages, mentor_name="王老师")
        assert len(pairs) >= 2

    def test_pair_structure(self, sample_messages):
        extractor = DialogExtractor()
        pairs = extractor.extract(sample_messages, mentor_name="王老师")
        for pair in pairs:
            assert not pair.answer.is_mentor or pair.answer.is_mentor  # answer is always from mentor
            assert pair.question is not None
            assert pair.answer is not None

    def test_empty_messages(self):
        extractor = DialogExtractor()
        pairs = extractor.extract([], mentor_name="导师")
        assert pairs == []

    def test_time_gap_breaks_pairing(self, sample_messages):
        """超时间间隔的消息不应配对"""
        from datetime import datetime, timezone, timedelta
        from mentor_skill.models.raw_message import RawMessage

        old_msg = RawMessage(
            source="test",
            timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
            sender="学徒",
            content="老师这个方案怎么样",
            is_mentor=False,
        )
        new_msg = RawMessage(
            source="test",
            timestamp=datetime(2020, 1, 2, tzinfo=timezone.utc),  # 隔了一天
            sender="王老师",
            content="你先想想问题是什么，不要急着写方案，先把核心用户和核心痛点想清楚。",
            is_mentor=True,
        )
        extractor = DialogExtractor(gap_seconds=1800)
        pairs = extractor.extract([old_msg, new_msg], mentor_name="王老师")
        assert len(pairs) == 0
