"""
OpenClawSkillGenerator — 生成 OpenClaw AgentSkills 格式

OpenClaw AgentSkills 使用结构化 YAML frontmatter + Markdown 正文的标准格式。
参考：https://github.com/OpenClaw/agent-skills-spec
"""
from __future__ import annotations

from pathlib import Path

import yaml

from mentor_skill.models.persona import Persona


class OpenClawSkillGenerator:
    """生成 OpenClaw AgentSkills 兼容格式"""

    SPEC_VERSION = "1.0"

    def generate(self, persona: Persona, output_path: Path) -> Path:
        l1 = persona.get_layer_data(1)
        l2 = persona.get_layer_data(2)
        l3 = persona.get_layer_data(3)
        l4 = persona.get_layer_data(4)
        l5 = persona.get_layer_data(5)
        l6 = persona.get_layer_data(6)
        l7 = persona.get_layer_data(7)

        mentor_name = persona.mentor_name

        # ── YAML frontmatter（AgentSkills 元数据）─────────────────────
        frontmatter = {
            "skill": {
                "id": f"mentor-{persona.persona_name}",
                "name": f"{mentor_name} Mentor Skill",
                "version": "1.0.0",
                "spec": self.SPEC_VERSION,
                "description": f"AI mentor persona distilled from {mentor_name}. "
                               f"Domains: {', '.join(l2.get('domains', ['General']))}.",
                "author": "mentor-skill",
                "generated_by": persona.distilled_by,
                "generated_at": persona.distilled_at[:10],
                "tags": ["mentor", "persona", "coaching"] + l2.get("domains", []),
                "language": l1.get("language", "zh-CN"),
            },
            "activation": {
                "trigger": "always",
                "priority": 100,
            },
            "capabilities": {
                "memory": True,
                "multi_turn": True,
                "tool_use": False,
            },
        }

        frontmatter_str = yaml.dump(
            frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
        )

        # ── 正文（Persona 系统提示词）────────────────────────────────
        catchphrases = l1.get("catchphrases", [])
        domains = l2.get("domains", [])
        active_projects = l7.get("active_projects", [])

        body = f"""## Persona

You are **{mentor_name}**. {l1.get("background", "")}

Your personality: {l1.get("personality", "")}

Signature catchphrases: {", ".join(f'"{p}"' for p in catchphrases) if catchphrases else "N/A"}

---

## Expertise

Domains: {", ".join(domains) if domains else "General"}

Key insights:
{self._bullet(l2.get("key_insights", []))}

---

## Thinking & Feedback Style

- Problem approach: {l3.get("problem_solving", "")}
- Decision logic: {l3.get("decision_framework", "")}
- Question style: {l3.get("question_style", "")} — never give answers directly, always ask first.

---

## Communication

Tone: {l4.get("tone", "")} | Structure: {l4.get("structure", "")} | Emoji: {l4.get("emoji_usage", "sparse")}

---

## Mentorship

Style: {l6.get("mentoring_style", "")}
Autonomy: {l6.get("autonomy_grant", "")}

Signs of frustration (use when apprentice repeats same mistakes):
{self._bullet(l5.get("frustration_signs", []))}

---

## Memory: Active Projects

{self._projects_table(active_projects)}

*When the conversation touches any of these projects, proactively ask for an update.*

---

## Behavioral Constraints

{self._bullet(self._build_constraints(l1, l2, l7, mentor_name, catchphrases))}
"""

        output = f"---\n{frontmatter_str}---\n\n{body}"
        output_path.write_text(output, encoding="utf-8")
        return output_path

    def _bullet(self, items: list) -> str:
        if not items:
            return "- N/A"
        return "\n".join(f"- {i}" for i in items)

    def _projects_table(self, projects: list) -> str:
        if not projects:
            return "_No active projects._"
        rows = [f"| {p.get('name','')} | {p.get('status','')} | {p.get('next_check','')} |"
                for p in projects]
        return "| Project | Status | Next check |\n|---------|--------|------------|\n" + "\n".join(rows)

    def _build_constraints(
        self,
        l1: dict,
        l2: dict,
        l7: dict,
        mentor_name: str,
        catchphrases: list,
    ) -> list[str]:
        constraints = [
            f"Stay in character as {mentor_name} at all times.",
            "Never give direct answers — guide through Socratic questioning.",
            "Track apprentice projects and proactively follow up on progress.",
        ]
        red_lines = l1.get("red_lines", [])
        for r in red_lines:
            constraints.append(f"RED LINE: {r}")
        boundaries = l2.get("knowledge_boundary", [])
        if boundaries:
            constraints.append(
                f"Outside your domains ({', '.join(boundaries)}), redirect: "
                f'"这不是我擅长的，你去问 XXX".'
            )
        if catchphrases:
            constraints.append(
                f'Use "{catchphrases[0]}" when apprentice needs to think deeper.'
            )
        return constraints
