"""
evals/metrics.py — Skill 质量评估维度

使用 LLM-as-judge 模式评分，三个核心维度：
  1. 风格一致性 (Style Consistency)    — 语气/追问方式是否符合 Persona
  2. 行为合规性 (Behavior Compliance)  — 是否做了期望行为、避免了禁止行为
  3. 追问能力   (Proactive Follow-up)  — 是否主动引用记忆层、追问进展
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    """单条测试用例的评估结果"""
    case_id: str
    score_style: float        # 0-10: 风格一致性
    score_behavior: float     # 0-10: 行为合规性
    score_followup: float     # 0-10: 追问/记忆层使用
    total: float = field(init=False)
    reasoning: str = ""
    raw_response: str = ""

    def __post_init__(self):
        self.total = round(
            self.score_style * 0.35
            + self.score_behavior * 0.40
            + self.score_followup * 0.25,
            2,
        )


JUDGE_SYSTEM_PROMPT = """你是一个专业的 AI Persona 质量评估专家。

你的任务是评估一个 AI 导师的回复是否符合其 Persona 定义。

评分维度（每项 0-10 分）：
1. **风格一致性**：AI 的回复语气、口头禅、表达方式是否与导师 Persona 一致
2. **行为合规性**：AI 是否做了"期望行为"列表中的事情，是否避免了"禁止行为"列表中的事情
3. **追问/记忆层**：AI 是否主动引用了与该对话相关的历史信息或进行中的项目

请以 JSON 格式输出评分结果：
{
  "score_style": <0-10的浮点数>,
  "score_behavior": <0-10的浮点数>,
  "score_followup": <0-10的浮点数>,
  "reasoning": "<100字以内的评判理由>"
}"""


def build_judge_prompt(
    persona_summary: str,
    test_case: dict,
    ai_response: str,
) -> str:
    """构建给 LLM-as-judge 的评估提示词"""
    expected = "\n".join(f"  - {b}" for b in test_case.get("expected_behaviors", []))
    forbidden = "\n".join(f"  - {b}" for b in test_case.get("forbidden_behaviors", []))

    return f"""## 导师 Persona 摘要
{persona_summary}

## 测试场景
{test_case.get("scenario", "")}

## 用户输入
{test_case.get("user_input", "")}

## AI 导师的实际回复
{ai_response}

## 评估标准

期望行为（做了得分，未做扣分）：
{expected}

禁止行为（出现则大幅扣分）：
{forbidden}

风格要求：
- 语气：{test_case.get("style_check", {}).get("expected_tone", "N/A")}
- 是否需要使用口头禅：{"是" if test_case.get("style_check", {}).get("should_use_catchphrase") else "否"}
- 是否需要简洁：{"是" if test_case.get("style_check", {}).get("should_be_concise") else "否"}

请基于以上标准打分。"""


def aggregate_results(results: list[MetricResult]) -> dict[str, Any]:
    """汇总多条评估结果"""
    if not results:
        return {}

    avg_style = sum(r.score_style for r in results) / len(results)
    avg_behavior = sum(r.score_behavior for r in results) / len(results)
    avg_followup = sum(r.score_followup for r in results) / len(results)
    avg_total = sum(r.total for r in results) / len(results)

    return {
        "total_cases": len(results),
        "avg_style_consistency": round(avg_style, 2),
        "avg_behavior_compliance": round(avg_behavior, 2),
        "avg_proactive_followup": round(avg_followup, 2),
        "avg_total_score": round(avg_total, 2),
        "grade": _score_to_grade(avg_total),
        "per_case": [
            {
                "id": r.case_id,
                "style": r.score_style,
                "behavior": r.score_behavior,
                "followup": r.score_followup,
                "total": r.total,
                "reasoning": r.reasoning,
            }
            for r in results
        ],
    }


def _score_to_grade(score: float) -> str:
    if score >= 9.0: return "S（优秀）"
    if score >= 7.5: return "A（良好）"
    if score >= 6.0: return "B（合格）"
    if score >= 4.0: return "C（需改进）"
    return "D（蒸馏失败）"
