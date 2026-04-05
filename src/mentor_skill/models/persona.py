"""
Persona — 七层导师人格模型 (Pydantic v2)

七层结构：
  L1: 基础身份层 (Identity)
  L2: 知识与专业层 (Knowledge)
  L3: 思维框架层 (Thinking)
  L4: 沟通风格层 (Communication)
  L5: 情感表达层 (Emotion)  ⭐ 新增
  L6: 指导关系层 (Mentorship) ⭐ 新增
  L7: 学徒记忆层 (ApprenticeMemory) ⭐⭐ 核心差异化
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Layer1Identity(BaseModel):
    """L1: 基础身份层"""
    name: str = ""
    role: list[str] = Field(default_factory=list)
    background: str = ""
    personality: str = ""
    catchphrases: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"


class Layer2Knowledge(BaseModel):
    """L2: 知识与专业层"""
    domains: list[str] = Field(default_factory=list)
    expertise_level: dict[str, int] = Field(default_factory=dict)   # 1-5
    knowledge_boundary: list[str] = Field(default_factory=list)
    preferred_tools: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)


class Layer3Thinking(BaseModel):
    """L3: 思维框架层"""
    problem_solving: str = ""
    decision_framework: str = ""
    question_style: str = ""
    feedback_pattern: str = ""
    common_patterns: list[str] = Field(default_factory=list)
    bias: list[str] = Field(default_factory=list)


class Layer4Communication(BaseModel):
    """L4: 沟通风格层"""
    tone: str = ""
    formality: str = "mixed"           # formal / casual / mixed
    structure: str = ""
    rhetoric: list[str] = Field(default_factory=list)
    emoji_usage: str = "sparse"        # none / sparse / moderate / heavy
    response_length: str = "adaptive"  # short / medium / long / adaptive
    typical_response_examples: list[str] = Field(default_factory=list)


class Layer5Emotion(BaseModel):
    """L5: 情感表达层"""
    empathy_style: str = ""
    encouragement_style: str = ""
    frustration_signs: list[str] = Field(default_factory=list)
    praise_style: str = ""
    emotional_boundary: list[str] = Field(default_factory=list)


class Layer6Mentorship(BaseModel):
    """L6: 指导关系层"""
    mentoring_style: str = ""
    teaching_rhythm: str = ""
    autonomy_grant: str = ""
    typical_scenarios: dict[str, str] = Field(default_factory=dict)
    growth_expectation: str = ""
    boundary_work_mentoring: str = ""


class Layer7ApprenticeMemory(BaseModel):
    """L7: 学徒记忆层 — 核心差异化特性"""
    active_projects: list[dict[str, Any]] = Field(default_factory=list)
    open_commitments: list[dict[str, Any]] = Field(default_factory=list)
    feedback_history: list[dict[str, Any]] = Field(default_factory=list)
    apprentice_profile: dict[str, Any] = Field(default_factory=dict)
    next_check_ins: list[str] = Field(default_factory=list)  # 下次对话应追问的要点


# 层 ID → 类型映射
LAYER_CLASSES: dict[int, type] = {
    1: Layer1Identity,
    2: Layer2Knowledge,
    3: Layer3Thinking,
    4: Layer4Communication,
    5: Layer5Emotion,
    6: Layer6Mentorship,
    7: Layer7ApprenticeMemory,
}

LAYER_NAMES: dict[int, str] = {
    1: "基础身份层",
    2: "知识与专业层",
    3: "思维框架层",
    4: "沟通风格层",
    5: "情感表达层",
    6: "指导关系层",
    7: "学徒记忆层",
}


class Persona(BaseModel):
    """完整的七层 Persona"""
    version: str = "1.0.0"
    distilled_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    distilled_by: str = ""           # 使用的模型名称
    persona_name: str = ""           # 导师名称（冗余，方便读取）
    source_stats: dict[str, Any] = Field(default_factory=dict)
    layers: dict[int, Any] = Field(default_factory=dict)

    def set_layer(self, num: int, data: BaseModel) -> None:
        self.layers[num] = data

    def get_layer(self, num: int) -> BaseModel | None:
        return self.layers.get(num)

    def get_layer_data(self, num: int) -> dict:
        """获取层数据（dict 格式）"""
        layer = self.layers.get(num)
        if layer is None:
            return {}
        if isinstance(layer, BaseModel):
            return layer.model_dump()
        return layer

    def is_complete(self) -> bool:
        """是否已完成全部七层蒸馏"""
        return all(i in self.layers for i in range(1, 8))

    def missing_layers(self) -> list[int]:
        return [i for i in range(1, 8) if i not in self.layers]

    @property
    def identity(self) -> Layer1Identity | None:
        return self.layers.get(1)

    @property
    def mentor_name(self) -> str:
        if self.identity and self.identity.name:
            return self.identity.name
        return self.persona_name or "导师"
