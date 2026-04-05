"""
pytest 全局 fixtures
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from mentor_skill.models.raw_message import RawMessage
from mentor_skill.models.persona import (
    Persona,
    Layer1Identity,
    Layer2Knowledge,
    Layer3Thinking,
    Layer4Communication,
    Layer5Emotion,
    Layer6Mentorship,
    Layer7ApprenticeMemory,
)


# ── 基础数据 fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_messages() -> list[RawMessage]:
    """一组典型的导师-学徒对话消息（使用固定绝对时间，避免 replace() 分钟错乱）"""
    def ts(h: int, m: int = 0) -> datetime:
        return datetime(2026, 4, 5, h, m, 0, tzinfo=timezone.utc)

    # is_high_value 是 property（word_count > 50），导师消息内容需足够长以触发
    return [
        RawMessage(
            source="markdown",
            timestamp=ts(9, 0),
            sender="学徒",
            content="老师，我这个用户增长方案您觉得怎么样？",
            is_mentor=False,
        ),
        RawMessage(
            source="markdown",
            timestamp=ts(9, 5),
            sender="王老师",
            content="你先想想，你的核心用户是谁？他们最痛的问题是什么？"
                    "方案先从这两个问题出发，不要上来就铺功能列表。",
            is_mentor=True,
        ),
        RawMessage(
            source="markdown",
            timestamp=ts(9, 20),
            sender="学徒",
            content="核心用户是刚毕业的大学生，最痛的是找不到实习机会。",
            is_mentor=False,
        ),
        RawMessage(
            source="markdown",
            timestamp=ts(9, 25),
            sender="王老师",
            content="好，那你的方案里有没有解决这个问题？我看了一下，你的方案更多是在说功能，"
                    "用户为什么要用你而不是 Boss 直聘？你的差异化到底在哪里？数据说话。",
            is_mentor=True,
        ),
        RawMessage(
            source="markdown",
            timestamp=ts(10, 0),
            sender="学徒",
            content="老师我改完了，请再看看",
            is_mentor=False,
        ),
        RawMessage(
            source="markdown",
            timestamp=ts(10, 10),
            sender="王老师",
            content="好多了。但你还需要再想想你的商业模式，这个方向市场空间有多大？"
                    "你做过竞品分析吗？先把这些搞清楚，再来和我讨论落地策略。",
            is_mentor=True,
        ),
    ]


@pytest.fixture
def full_persona() -> Persona:
    """一个完整的 7 层 Persona"""
    p = Persona(persona_name="wang-laoshi")
    p.set_layer(1, Layer1Identity(
        name="王老师",
        role=["产品总监", "导师"],
        background="10 年互联网产品经验，曾任职于字节跳动、美团",
        personality="直接、务实、注重第一性原理",
        catchphrases=["你再想想", "先回答这两个问题", "数据说话"],
        red_lines=["不接受没有数据支撑的判断"],
    ))
    p.set_layer(2, Layer2Knowledge(
        domains=["用户增长", "产品设计", "商业模式"],
        key_insights=["用户价值先于商业价值", "做减法比做加法难"],
        preferred_tools=["飞书", "Figma", "SQL"],
    ))
    p.set_layer(3, Layer3Thinking(
        problem_solving="从第一性原理出发，先问核心用户是谁",
        decision_framework="数据验证 → 小范围试验 → 放大",
        question_style="反问式追问，引导对方自己找答案",
    ))
    p.set_layer(4, Layer4Communication(
        tone="直接但不刻薄",
        emoji_usage="sparse",
        structure="先问题 → 再拆解 → 最后给方向",
    ))
    p.set_layer(5, Layer5Emotion(
        empathy_style="理解情绪但快速切换到解决方案",
        praise_style="具体行为夸奖，不泛夸",
        frustration_signs=["沉默", "你再想想"],
    ))
    p.set_layer(6, Layer6Mentorship(
        mentoring_style="引导式为主，重大决策前直接给建议",
        autonomy_grant="给方向，不给答案",
        growth_expectation="3 个月内能独立拆解产品问题",
    ))
    p.set_layer(7, Layer7ApprenticeMemory(
        active_projects=[{"name": "用户增长方案 v2", "status": "进行中", "next_check": "下周一"}],
        feedback_history=[{"topic": "核心用户定义", "advice": "先想清楚用户是谁再写方案"}],
        apprentice_profile={"name": "小李", "level": "应届生", "strengths": ["学习快"], "weaknesses": ["缺乏数据思维"]},
    ))
    p.distilled_by = "glm-4-flash"
    return p


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLM 客户端，返回预设 JSON"""
    client = MagicMock()
    client.config = MagicMock()
    client.config.model = "mock-model"
    client.call_json.return_value = {
        "name": "王老师",
        "role": ["产品总监"],
        "background": "10 年产品经验",
        "personality": "直接务实",
        "catchphrases": ["你再想想"],
        "red_lines": [],
    }
    client.call.return_value = "这是一个模拟的回复。"
    return client


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """临时数据目录"""
    d = tmp_path / "data"
    d.mkdir()
    return d
