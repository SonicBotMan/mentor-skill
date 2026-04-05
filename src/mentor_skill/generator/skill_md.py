"""
SkillMDGenerator — 生成最终的 mentor.SKILL.md

将 Persona 七层模型转换为高质量的 AI Agent 系统提示词（Markdown 格式）。
"""
from __future__ import annotations

from pathlib import Path

from mentor_skill.models.persona import Persona


class SkillMDGenerator:
    """生成最终给 AI Agent 使用的 .SKILL.md"""

    def generate(self, persona: Persona, output_path: Path) -> Path:
        l1 = persona.get_layer_data(1)
        l2 = persona.get_layer_data(2)
        l3 = persona.get_layer_data(3)
        l4 = persona.get_layer_data(4)
        l5 = persona.get_layer_data(5)
        l6 = persona.get_layer_data(6)
        l7 = persona.get_layer_data(7)

        # 核心 Prompt 模板
        md = f"""# {persona.mentor_name}.SKILL

> 此文件由 mentor-skill v0.1 自动蒸馏生成。
> 蒸馏时间：{persona.distilled_at}
> 蒸馏模型：{persona.distilled_by}

## 1. 基础身份 (Identity)
- **角色**: {", ".join(l1.get("role", []))}
- **背景**: {l1.get("background", "N/A")}
- **性格**: {l1.get("personality", "N/A")}
- **口头禅**: {", ".join(l1.get("catchphrases", []))}

## 2. 知识与专业 (Knowledge)
- **专业领域**: {", ".join(l2.get("domains", []))}
- **核心见解**:
{self._format_list(l2.get("key_insights", []))}
- **常用工具**: {", ".join(l2.get("preferred_tools", []))}

## 3. 思维框架 (Thinking)
- **问题解决路径**: {l3.get("problem_solving", "N/A")}
- **决策逻辑**: {l3.get("decision_framework", "N/A")}
- **追问风格**: {l3.get("question_style", "N/A")}

## 4. 沟通风格 (Communication)
- **语气**: {l4.get("tone", "N/A")}
- **Emoji 习惯**: {l4.get("emoji_usage", "N/A")}
- **回复结构**: {l4.get("structure", "N/A")}

## 5. 情感表达 (Emotion)
- **共情风格**: {l5.get("empathy_style", "N/A")}
- **表扬/惩戒**: {l5.get("praise_style", "N/A")}

## 6. 指导关系 (Mentorship)
- **带人策略**: {l6.get("mentoring_style", "N/A")}
- **授权模型**: {l6.get("autonomy_grant", "N/A")}

## 7. 学徒记忆 (Apprentice Memory) ⭐⭐
- **正在进行的项目**: {self._format_list_dict(l7.get("active_projects", []), "name")}
- **历史关键反馈**: {self._format_list_dict(l7.get("feedback_history", []), "topic")}
- **下次追问要点**: {", ".join(l7.get("next_check_ins", [])) or "(无)"}

---

## 指导原则 (System Instructions)
1. **严格保持上述人格特征**，尤其是口头禅和沟通节奏。
2. **知识边界外的内容请拒绝回答**，并引导学徒思考。
3. **对话时需根据《学徒记忆》中的进展进行追问**。

"""
        output_path.write_text(md, encoding="utf-8")
        return output_path

    def _format_list(self, items: list) -> str:
        if not items: return "  (无)"
        return "\n".join([f"  - {i}" for i in items])

    def _format_list_dict(self, items: list, key: str) -> str:
        if not items: return "(无)"
        return ", ".join([str(i.get(key, "")) for i in items])
