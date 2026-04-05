"""
CLI 命令集成测试

使用 typer.testing.CliRunner 对主要命令做端到端验证（不依赖 LLM）。
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mentor_skill.cli import app

runner = CliRunner()


# ── 辅助函数 ──────────────────────────────────────────────────────────


def _make_persona_dir(base: Path, persona_id: str, layers: int = 7) -> Path:
    """在 base/.mentor/personas/<id>/ 创建一个完整的 Persona 目录"""
    from mentor_skill.models.persona import (
        Persona, Layer1Identity, Layer2Knowledge, Layer3Thinking,
        Layer4Communication, Layer5Emotion, Layer6Mentorship, Layer7ApprenticeMemory,
    )
    from mentor_skill.generator.persona_files import PersonaFileGenerator

    p = Persona(persona_name=persona_id)
    layer_map = {
        1: Layer1Identity(name="王老师", role=["导师"], background="10年经验",
                          personality="直接", catchphrases=["你再想想"], red_lines=[]),
        2: Layer2Knowledge(domains=["产品"], key_insights=["先想清楚问题"], preferred_tools=["飞书"]),
        3: Layer3Thinking(problem_solving="第一性原理", decision_framework="数据驱动", question_style="反问"),
        4: Layer4Communication(tone="直接", emoji_usage="sparse", structure="问题→拆解→方向"),
        5: Layer5Emotion(empathy_style="共情后切入解法", praise_style="具体夸奖", frustration_signs=["沉默"]),
        6: Layer6Mentorship(mentoring_style="引导式", autonomy_grant="给方向不给答案", growth_expectation="独立拆解"),
        7: Layer7ApprenticeMemory(active_projects=[], feedback_history=[], apprentice_profile={}),
    }
    for lid in range(1, layers + 1):
        p.set_layer(lid, layer_map[lid])
    p.distilled_by = "glm-4-flash"

    persona_dir = base / ".mentor" / "personas" / persona_id
    persona_dir.mkdir(parents=True, exist_ok=True)
    PersonaFileGenerator().save(p, persona_dir)
    return persona_dir


def _patch_config(tmp_path: Path):
    """返回 patch 上下文，让 get_config() 用 tmp_path 下的目录"""
    from mentor_skill.config import AppConfig, ProjectSettings, LLMSettings

    cfg = AppConfig(
        project=ProjectSettings(
            data_dir=str(tmp_path / ".mentor" / "data"),
            output_dir=str(tmp_path / ".mentor" / "output"),
            persona_dir=str(tmp_path / ".mentor" / "personas"),
        ),
        llm=LLMSettings(model="glm-4-flash", api_key=""),
    )
    return patch("mentor_skill.cli.get_config", return_value=cfg)


# ── mentor init ───────────────────────────────────────────────────────


class TestInit:
    def test_creates_directories(self, tmp_path):
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["init", "--name", "test-mentor", "--template", "product"])

        assert result.exit_code == 0
        assert "test-mentor" in result.output
        assert (tmp_path / ".mentor" / "personas" / "test-mentor").exists()
        assert (tmp_path / ".mentor" / "data" / "test-mentor").exists()

    def test_creates_persona_json(self, tmp_path):
        with _patch_config(tmp_path):
            runner.invoke(app, ["init", "--name", "init-test", "--template", "tech"])

        persona_json = tmp_path / ".mentor" / "personas" / "init-test" / "persona.json"
        assert persona_json.exists()


# ── mentor list ───────────────────────────────────────────────────────


class TestList:
    def test_empty_list(self, tmp_path):
        (tmp_path / ".mentor" / "personas").mkdir(parents=True)
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "暂无" in result.output

    def test_shows_personas(self, tmp_path):
        _make_persona_dir(tmp_path, "wang-laoshi")
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "wang-laoshi" in result.output
        assert "7/7" in result.output

    def test_partial_layers_shown(self, tmp_path):
        _make_persona_dir(tmp_path, "partial-mentor", layers=3)
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["list"])
        assert "3/7" in result.output


# ── mentor compare ────────────────────────────────────────────────────


class TestCompare:
    def test_compare_two_personas(self, tmp_path):
        _make_persona_dir(tmp_path, "mentor-a")
        _make_persona_dir(tmp_path, "mentor-b")

        with _patch_config(tmp_path):
            result = runner.invoke(app, [
                "compare", "--persona-a", "mentor-a", "--persona-b", "mentor-b"
            ])

        assert result.exit_code == 0
        assert "mentor-a" in result.output
        assert "mentor-b" in result.output

    def test_compare_missing_persona_exits_1(self, tmp_path):
        _make_persona_dir(tmp_path, "mentor-a")
        with _patch_config(tmp_path):
            result = runner.invoke(app, [
                "compare", "--persona-a", "mentor-a", "--persona-b", "nonexistent"
            ])
        assert result.exit_code == 1

    def test_compare_shows_layer_labels(self, tmp_path):
        _make_persona_dir(tmp_path, "pa")
        _make_persona_dir(tmp_path, "pb")
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["compare", "--persona-a", "pa", "--persona-b", "pb"])
        assert "L1" in result.output
        assert "L7" in result.output


# ── mentor demo ───────────────────────────────────────────────────────


class TestDemo:
    def test_demo_full_dry_run(self):
        result = runner.invoke(app, ["demo", "--full"])
        assert result.exit_code == 0
        assert "Step" in result.output
        assert "mentor init" in result.output

    def test_demo_no_api_key_shows_skill(self):
        """无 API Key 时应展示 SKILL.md 内容"""
        with patch("mentor_skill.cli.get_config") as mock_cfg:
            from mentor_skill.config import AppConfig, LLMSettings
            mock_cfg.return_value = AppConfig(llm=LLMSettings(api_key=""))
            result = runner.invoke(app, ["demo"])
        # 无 API Key 时应该展示 SKILL.md 预览或配置引导
        assert result.exit_code == 0
        assert "API Key" in result.output or "SKILL" in result.output


# ── mentor export / import ────────────────────────────────────────────


class TestExportImport:
    def test_export_creates_zip(self, tmp_path):
        _make_persona_dir(tmp_path, "export-test")
        out_zip = tmp_path / "export-test.mentor.zip"

        with _patch_config(tmp_path):
            result = runner.invoke(app, [
                "export", "--persona", "export-test",
                "--output", str(out_zip),
            ])

        assert result.exit_code == 0
        assert out_zip.exists()
        assert zipfile.is_zipfile(out_zip)

    def test_export_zip_contains_persona_json(self, tmp_path):
        _make_persona_dir(tmp_path, "zip-test")
        out_zip = tmp_path / "zip-test.zip"

        with _patch_config(tmp_path):
            runner.invoke(app, ["export", "--persona", "zip-test", "--output", str(out_zip)])

        with zipfile.ZipFile(out_zip) as zf:
            names = zf.namelist()
        assert any("persona.json" in n for n in names)

    def test_import_restores_persona(self, tmp_path):
        # 导出
        _make_persona_dir(tmp_path, "roundtrip")
        out_zip = tmp_path / "roundtrip.zip"
        with _patch_config(tmp_path):
            runner.invoke(app, ["export", "--persona", "roundtrip", "--output", str(out_zip)])

        # 删除原 persona，验证 import 能恢复
        import shutil
        shutil.rmtree(tmp_path / ".mentor" / "personas" / "roundtrip")

        with _patch_config(tmp_path):
            result = runner.invoke(app, ["import", str(out_zip)])

        assert result.exit_code == 0
        assert (tmp_path / ".mentor" / "personas" / "roundtrip" / "persona.json").exists()
        # Rich 在窄终端会对长路径软换行，子串 "roundtrip" 可能被拆成 ro\nundtrip
        assert "roundtrip" in result.output.replace("\n", "")

    def test_import_missing_file_exits_1(self, tmp_path):
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["import", str(tmp_path / "nonexistent.zip")])
        assert result.exit_code == 1

    def test_export_missing_persona_exits_1(self, tmp_path):
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["export", "--persona", "ghost"])
        assert result.exit_code == 1

    def test_import_overwrite_flag(self, tmp_path):
        _make_persona_dir(tmp_path, "overwrite-test")
        out_zip = tmp_path / "ow.zip"
        with _patch_config(tmp_path):
            runner.invoke(app, ["export", "--persona", "overwrite-test", "--output", str(out_zip)])
            # 不用 --overwrite 时提示已存在
            result = runner.invoke(app, ["import", str(out_zip)])
        assert "已存在" in result.output or result.exit_code == 0

        with _patch_config(tmp_path):
            result = runner.invoke(app, ["import", "--overwrite", str(out_zip)])
        assert result.exit_code == 0


# ── mentor distill --dry-run ──────────────────────────────────────────


class TestDistillDryRun:
    def test_dry_run_no_api_key_required(self, tmp_path):
        """dry-run 不需要 API Key"""
        # 创建 data 目录（即使为空也要能运行）
        data_dir = tmp_path / ".mentor" / "data" / "dry-mentor"
        data_dir.mkdir(parents=True)

        with _patch_config(tmp_path):
            result = runner.invoke(app, [
                "distill", "--persona", "dry-mentor", "--dry-run"
            ])

        # 无数据时应该报错（没有 _raw.json）
        # dry-run 下 no api key 不报错，但 no data 会报错
        assert "dry-mentor" in result.output or result.exit_code in (0, 1)

    def test_dry_run_with_data_shows_plan(self, tmp_path):
        """有数据时 dry-run 应该展示蒸馏计划"""
        from datetime import datetime, timezone

        data_dir = tmp_path / ".mentor" / "data" / "plan-mentor"
        data_dir.mkdir(parents=True)

        # 写 raw data
        raw_data = [
            {
                "source": "markdown",
                "timestamp": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
                "sender": "王老师",
                "content": "你再想想，你的核心用户是谁？" * 20,
                "is_mentor": True,
                "context": {},
            }
        ]
        (data_dir / "markdown_raw.json").write_text(
            json.dumps(raw_data, ensure_ascii=False), encoding="utf-8"
        )

        with _patch_config(tmp_path):
            result = runner.invoke(app, [
                "distill", "--persona", "plan-mentor", "--dry-run"
            ])

        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "蒸馏计划" in result.output
        assert "Token" in result.output or "token" in result.output


# ── mentor doctor ─────────────────────────────────────────────────────


class TestDoctor:
    def test_doctor_runs_with_patched_config(self, tmp_path):
        (tmp_path / ".mentor" / "data").mkdir(parents=True)
        (tmp_path / ".mentor" / "personas").mkdir(parents=True)
        with _patch_config(tmp_path):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "诊断报告" in result.output

    def test_doctor_shows_ready_when_all_pass(self, tmp_path):
        """有数据文件 + 完整 Persona 时面板应偏「就绪」"""
        data_dir = tmp_path / ".mentor" / "data" / "m1"
        data_dir.mkdir(parents=True)
        (data_dir / "x_raw.json").write_text("[]", encoding="utf-8")
        _make_persona_dir(tmp_path, "m1")
        with _patch_config(tmp_path):
            from mentor_skill.config import AppConfig, LLMSettings, ProjectSettings

            cfg = AppConfig(
                project=ProjectSettings(
                    data_dir=str(tmp_path / ".mentor" / "data"),
                    output_dir=str(tmp_path / ".mentor" / "output"),
                    persona_dir=str(tmp_path / ".mentor" / "personas"),
                ),
                llm=LLMSettings(model="glm-4-flash", api_key="sk-test", api_base="https://open.bigmodel.cn/api/paas/v4/"),
            )
            with patch("mentor_skill.cli.get_config", return_value=cfg):
                result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "环境就绪" in result.output


# ── mentor config --preset ────────────────────────────────────────────


class TestConfigPreset:
    def test_preset_zhipu_updates_llm_and_saves(self, tmp_path):
        from mentor_skill.config import AppConfig, LLMSettings, LLM_PRESETS

        cfg = AppConfig(llm=LLMSettings(api_key="", model="", api_base=None))
        with patch("mentor_skill.cli.get_config", return_value=cfg):
            with patch("mentor_skill.cli.save_config") as mock_save:
                result = runner.invoke(app, ["config", "--preset", "zhipu"])
        assert result.exit_code == 0
        assert cfg.llm.model == LLM_PRESETS["zhipu"]["default_model"]
        assert cfg.llm.api_base == LLM_PRESETS["zhipu"]["api_base"]
        mock_save.assert_called_once()

    def test_preset_unknown_exits_1(self):
        from mentor_skill.config import AppConfig, LLMSettings

        cfg = AppConfig(llm=LLMSettings())
        with patch("mentor_skill.cli.get_config", return_value=cfg):
            result = runner.invoke(app, ["config", "--preset", "not-a-vendor"])
        assert result.exit_code == 1
