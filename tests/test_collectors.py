"""
测试 collectors 模块：本地文件采集器（Markdown / PDF / WeChat）
API 采集器（Feishu / DingTalk）仅测试 validate_input，不发真实请求。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mentor_skill.models.raw_message import RawMessage


class TestMarkdownCollector:
    def test_collect_single_file(self, tmp_path: Path):
        from mentor_skill.collectors import MarkdownCollector

        md_file = tmp_path / "notes.md"
        md_file.write_text(
            "# 产品方向\n\n你的核心用户是谁？先回答这个问题，再写方案。\n\n数据说话，不要拍脑袋。",
            encoding="utf-8",
        )
        collector = MarkdownCollector()
        msgs = collector.collect(input_path=str(tmp_path), mentor_name="王老师")
        assert len(msgs) >= 1
        assert all(isinstance(m, RawMessage) for m in msgs)
        assert any("核心用户" in m.content for m in msgs)

    def test_collect_directory(self, tmp_path: Path):
        from mentor_skill.collectors import MarkdownCollector

        for i in range(3):
            (tmp_path / f"doc{i}.md").write_text(
                f"# 文档{i}\n\n这是导师写的第 {i} 份文档，包含方法论和思考框架。",
                encoding="utf-8",
            )
        collector = MarkdownCollector()
        msgs = collector.collect(input_path=str(tmp_path), mentor_name="导师")
        assert len(msgs) >= 3

    def test_empty_directory_returns_empty(self, tmp_path: Path):
        from mentor_skill.collectors import MarkdownCollector

        collector = MarkdownCollector()
        msgs = collector.collect(input_path=str(tmp_path), mentor_name="导师")
        assert msgs == []


class TestWechatCollector:
    def test_collect_csv(self, tmp_path: Path):
        from mentor_skill.collectors import WechatCollector

        csv_file = tmp_path / "wechat.csv"
        csv_file.write_text(
            "时间,发送者,内容\n"
            "2024-01-01 09:00:00,王老师,你再想想，核心用户是谁\n"
            "2024-01-01 09:05:00,小李,老师我重新想了一下\n"
            "2024-01-01 09:10:00,王老师,好，那你的解决方案是什么？数据说话。\n",
            encoding="utf-8",
        )
        collector = WechatCollector()
        msgs = collector.collect(input_file=str(csv_file), mentor_name="王老师")
        mentor_msgs = [m for m in msgs if m.is_mentor]
        assert len(mentor_msgs) >= 1

    def test_missing_file_returns_empty(self, tmp_path: Path):
        from mentor_skill.collectors import WechatCollector

        collector = WechatCollector()
        msgs = collector.collect(input_file=str(tmp_path / "nonexistent.csv"), mentor_name="导师")
        assert msgs == []


class TestFeishuCollectorValidation:
    def test_validate_fails_without_credentials(self):
        from mentor_skill.collectors import FeishuCollector

        collector = FeishuCollector(config={})
        assert collector.validate_input() is False

    def test_validate_passes_with_credentials(self):
        from mentor_skill.collectors import FeishuCollector

        collector = FeishuCollector(config={"app_id": "cli_xxx", "app_secret": "secret"})
        assert collector.validate_input() is True


class TestDingtalkCollectorValidation:
    def test_validate_fails_without_credentials(self):
        from mentor_skill.collectors import DingtalkCollector

        collector = DingtalkCollector(config={})
        assert collector.validate_input() is False
