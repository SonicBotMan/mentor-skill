"""
测试 generator 模块：SkillMDGenerator / PersonaFileGenerator / PersonaValidator
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mentor_skill.generator import SkillMDGenerator, PersonaValidator
from mentor_skill.generator.persona_files import PersonaFileGenerator
from mentor_skill.models.persona import Persona, Layer1Identity


class TestSkillMDGenerator:
    def test_generates_file(self, full_persona: Persona, tmp_path: Path):
        output = tmp_path / "test.SKILL.md"
        SkillMDGenerator().generate(full_persona, output)
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert len(content) > 100

    def test_output_contains_all_layers(self, full_persona: Persona, tmp_path: Path):
        output = tmp_path / "test.SKILL.md"
        SkillMDGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        for keyword in ["Identity", "Knowledge", "Thinking", "Communication", "Emotion", "Mentorship", "Apprentice"]:
            assert keyword in content, f"SKILL.md 缺少 {keyword} 部分"

    def test_mentor_name_in_output(self, full_persona: Persona, tmp_path: Path):
        output = tmp_path / "test.SKILL.md"
        SkillMDGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "王老师" in content

    def test_catchphrases_included(self, full_persona: Persona, tmp_path: Path):
        output = tmp_path / "test.SKILL.md"
        SkillMDGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "你再想想" in content


class TestPersonaFileGenerator:
    def test_saves_yaml_and_json(self, full_persona: Persona, tmp_path: Path):
        PersonaFileGenerator().save(full_persona, tmp_path)
        assert (tmp_path / "persona.yaml").exists()
        assert (tmp_path / "persona.json").exists()

    def test_json_is_loadable(self, full_persona: Persona, tmp_path: Path):
        PersonaFileGenerator().save(full_persona, tmp_path)
        with open(tmp_path / "persona.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["persona_name"] == "wang-laoshi"
        assert "layers" in data

    def test_json_layers_have_string_keys(self, full_persona: Persona, tmp_path: Path):
        """YAML/JSON 中层的 key 应为字符串"""
        PersonaFileGenerator().save(full_persona, tmp_path)
        with open(tmp_path / "persona.json", encoding="utf-8") as f:
            data = json.load(f)
        for key in data["layers"].keys():
            assert isinstance(key, str), f"层 key {key!r} 不是字符串"


class TestCursorRuleGenerator:
    def test_generates_mdc_file(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.cursor_rule import CursorRuleGenerator

        output = tmp_path / "wang-laoshi.mdc"
        CursorRuleGenerator().generate(full_persona, output)
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "---" in content  # frontmatter
        assert "alwaysApply" in content

    def test_cursor_rule_contains_persona_name(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.cursor_rule import CursorRuleGenerator

        output = tmp_path / "test.mdc"
        CursorRuleGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "王老师" in content
        assert "你再想想" in content

    def test_cursor_rule_contains_active_projects(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.cursor_rule import CursorRuleGenerator

        output = tmp_path / "test.mdc"
        CursorRuleGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "用户增长方案" in content


class TestClaudeSkillGenerator:
    def test_generates_skill_file(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.claude_skill import ClaudeSkillGenerator

        output = tmp_path / "wang-laoshi.claude.SKILL.md"
        ClaudeSkillGenerator().generate(full_persona, output)
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert len(content) > 200

    def test_contains_rules_section(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.claude_skill import ClaudeSkillGenerator

        output = tmp_path / "test.md"
        ClaudeSkillGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "<rules>" in content
        assert "</rules>" in content

    def test_contains_projects_table(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.claude_skill import ClaudeSkillGenerator

        output = tmp_path / "test.md"
        ClaudeSkillGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        assert "用户增长方案" in content


class TestOpenClawSkillGenerator:
    def test_generates_skill_file(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.openclaw_skill import OpenClawSkillGenerator

        output = tmp_path / "wang-laoshi.openclaw.skill.md"
        OpenClawSkillGenerator().generate(full_persona, output)
        assert output.exists()

    def test_has_yaml_frontmatter(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.openclaw_skill import OpenClawSkillGenerator
        import yaml

        output = tmp_path / "test.md"
        OpenClawSkillGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")

        # 提取 frontmatter
        parts = content.split("---\n", 2)
        assert len(parts) >= 3
        fm = yaml.safe_load(parts[1])
        assert "skill" in fm
        assert fm["skill"]["spec"] == "1.0"

    def test_frontmatter_contains_tags(self, full_persona: Persona, tmp_path: Path):
        from mentor_skill.generator.openclaw_skill import OpenClawSkillGenerator
        import yaml

        output = tmp_path / "test.md"
        OpenClawSkillGenerator().generate(full_persona, output)
        content = output.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        fm = yaml.safe_load(parts[1])
        assert "mentor" in fm["skill"]["tags"]


class TestPersonaValidator:
    def test_valid_persona_passes(self, full_persona: Persona):
        assert PersonaValidator().validate(full_persona) is True

    def test_missing_l1_fails(self):
        p = Persona(persona_name="empty")
        assert PersonaValidator().validate(p) is False

    def test_l1_without_name_fails(self):
        p = Persona(persona_name="noname")
        p.set_layer(1, Layer1Identity(name=""))  # 空 name
        assert PersonaValidator().validate(p) is False

    def test_partial_persona_passes_with_warning(self, capsys):
        """部分层缺失时仍应通过验证（但会打印警告）"""
        p = Persona(persona_name="partial")
        p.set_layer(1, Layer1Identity(name="导师"))
        # 只有 L1，缺失 L2-L7
        result = PersonaValidator().validate(p)
        assert result is True
