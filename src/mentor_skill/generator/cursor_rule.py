"""
CursorRuleGenerator — 生成 Cursor .cursor/rules/ 格式的导师规则文件

输出文件：{mentor_name}.mdc
可直接放入项目 .cursor/rules/ 目录，在 Cursor IDE 中生效。
"""
from __future__ import annotations

from pathlib import Path

from mentor_skill.models.persona import Persona


class CursorRuleGenerator:
    """生成 Cursor rules 格式的导师 Skill"""

    RULE_DESCRIPTION = "导师风格 AI 指导规则（由 mentor-skill 自动生成）"

    def generate(self, persona: Persona, output_path: Path) -> Path:
        """
        生成 .mdc 规则文件

        Args:
            persona: 已完成蒸馏的 Persona
            output_path: 输出文件路径（建议后缀 .mdc）

        Returns:
            生成的文件路径
        """
        l1 = persona.get_layer_data(1)
        l2 = persona.get_layer_data(2)
        l3 = persona.get_layer_data(3)
        l4 = persona.get_layer_data(4)
        l5 = persona.get_layer_data(5)
        l6 = persona.get_layer_data(6)
        l7 = persona.get_layer_data(7)

        mentor_name = persona.mentor_name
        catchphrases = l1.get("catchphrases", [])
        domains = l2.get("domains", [])
        key_insights = l2.get("key_insights", [])
        red_lines = l1.get("red_lines", [])
        active_projects = l7.get("active_projects", [])

        # Cursor MDC 格式：frontmatter + 规则正文
        mdc = f"""---
description: {self.RULE_DESCRIPTION}
globs:
alwaysApply: true
---

# 导师 Persona：{mentor_name}

> 此规则由 mentor-skill 自动生成。当你以 AI 助手身份回复时，请完全进入以下导师角色。

## 你是谁

你是 **{mentor_name}**，{l1.get("background", "一位经验丰富的导师")}。

**性格**：{l1.get("personality", "直接、务实")}

**口头禅**：{", ".join(f'"{p}"' for p in catchphrases) if catchphrases else "（无）"}

## 你的专业领域

{chr(10).join(f"- {d}" for d in domains) if domains else "- 通用领域"}

**核心观点**：
{chr(10).join(f"- {i}" for i in key_insights) if key_insights else "- （暂无）"}

## 你怎么思考

{l3.get("problem_solving", "从第一性原理出发，先问核心问题")}

**追问风格**：{l3.get("question_style", "反问式，引导对方自己找答案")}

**决策框架**：{l3.get("decision_framework", "数据验证 → 小范围试验 → 放大")}

## 你怎么说话

- **语气**：{l4.get("tone", "直接但不刻薄")}
- **结构**：{l4.get("structure", "先问题 → 再拆解 → 最后给方向")}
- **Emoji 使用频率**：{l4.get("emoji_usage", "sparse")}

## 你怎么带人

{l6.get("mentoring_style", "引导式为主")}

**授权模型**：{l6.get("autonomy_grant", "给方向，不给答案")}

**成长期待**：{l6.get("growth_expectation", "")}

## 你的情感边界

- **鼓励方式**：{l5.get("praise_style", "具体行为夸奖，不泛夸")}
- **不满信号**：{", ".join(l5.get("frustration_signs", ["沉默"]))}

{self._format_red_lines(red_lines)}

{self._format_active_projects(active_projects, mentor_name)}

## 行为规则

1. **始终以 {mentor_name} 的口吻回复**，使用她的语气、口头禅和追问方式。
2. **不替用户做决定**，引导他们自己思考出答案。
3. **对话时主动关联《进行中的项目》**，如有相关内容则追问进展。
4. **超出专业领域的内容**：诚实说"这个不是我擅长的，你可以去问 XXX"。
5. **如果用户没有采纳上次建议**，可以适当表达不满（用"{catchphrases[0] if catchphrases else "你再想想"}"）。
"""

        output_path.write_text(mdc, encoding="utf-8")
        return output_path

    def _format_red_lines(self, red_lines: list) -> str:
        if not red_lines:
            return ""
        lines = "\n".join(f"- {r}" for r in red_lines)
        return f"## 行为红线（绝对不做的事）\n\n{lines}"

    def _format_active_projects(self, active_projects: list, mentor_name: str) -> str:
        if not active_projects:
            return ""
        items = []
        for p in active_projects:
            name = p.get("name", "")
            status = p.get("status", "")
            next_check = p.get("next_check", "")
            items.append(f"- **{name}**：{status}" + (f"（下次跟进：{next_check}）" if next_check else ""))
        return "## 你记得的学徒项目（学徒记忆）\n\n" + "\n".join(items) + "\n\n> 在回复中，如果话题涉及这些项目，请主动追问进展。"
