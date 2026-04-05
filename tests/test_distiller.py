"""
测试 distiller 模块：各层 Prompt 生成与 LLM 结果解析（使用 Mock LLM）
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mentor_skill.distiller.engine import DistillationEngine, CHECKPOINT_FILENAME
from mentor_skill.models.persona import Persona, Layer1Identity


class TestL1Identity:
    def test_distill_updates_persona(self, sample_messages, mock_llm_client):
        from mentor_skill.distiller.layers.l1_identity import L1Identity

        layer = L1Identity(mock_llm_client)
        persona = Persona(persona_name="test")
        result = layer.distill(persona, sample_messages)

        assert 1 in result.layers
        l1 = result.get_layer_data(1)
        assert l1.get("name") == "王老师"
        assert "产品总监" in l1.get("role", [])

    def test_distill_handles_partial_llm_response(self, sample_messages):
        """LLM 只返回部分字段时不应崩溃"""
        client = MagicMock()
        client.config.model = "mock"
        client.call_json.return_value = {"name": "张导师"}  # 只有 name 字段

        from mentor_skill.distiller.layers.l1_identity import L1Identity
        layer = L1Identity(client)
        persona = Persona(persona_name="test")
        result = layer.distill(persona, sample_messages)
        assert result.get_layer_data(1)["name"] == "张导师"


class TestDistillationEngine:
    def test_run_completes_all_layers(self, sample_messages, mock_llm_client, tmp_path):
        """完整运行 7 层，验证每层都写入了 Persona"""
        # 为每层设置不同的 mock 返回
        mock_llm_client.call_json.side_effect = _mock_layer_responses()

        engine = DistillationEngine(mock_llm_client, checkpoint_dir=tmp_path)
        persona = Persona(persona_name="test")
        result = engine.run(persona, sample_messages)

        # 所有层应当完成
        assert result.is_complete(), f"未完成的层: {result.missing_layers()}"

    def test_checkpoint_saved_after_each_layer(self, sample_messages, mock_llm_client, tmp_path):
        """每层蒸馏后应保存断点文件"""
        mock_llm_client.call_json.side_effect = _mock_layer_responses()

        engine = DistillationEngine(mock_llm_client, checkpoint_dir=tmp_path)
        persona = Persona(persona_name="test")

        # 模拟在 L3 后崩溃：只跑前 3 层
        engine.layer_instances = engine.layer_instances[:3]
        engine.run(persona, sample_messages)

        ckpt_file = tmp_path / CHECKPOINT_FILENAME
        assert ckpt_file.exists(), "断点文件未生成"
        with open(ckpt_file) as f:
            data = json.load(f)
        assert "3" in data.get("layers", {})

    def test_resume_skips_completed_layers(self, sample_messages, mock_llm_client, tmp_path):
        """--resume 时已完成的层不应重新执行"""
        # 先保存一个有 L1 的断点
        ckpt_persona = Persona(persona_name="test")
        ckpt_persona.set_layer(1, Layer1Identity(name="王老师", role=["导师"]))
        ckpt_data = ckpt_persona.model_dump()
        ckpt_data["layers"] = {str(k): v for k, v in ckpt_data["layers"].items()}
        ckpt_file = tmp_path / CHECKPOINT_FILENAME
        with open(ckpt_file, "w") as f:
            json.dump(ckpt_data, f, ensure_ascii=False, indent=2)

        # 设置 mock，L1 不应被调用
        responses = _mock_layer_responses()
        mock_llm_client.call_json.side_effect = responses[1:]  # 跳过 L1 的 mock

        engine = DistillationEngine(mock_llm_client, checkpoint_dir=tmp_path)
        persona = Persona(persona_name="test")
        result = engine.run(persona, sample_messages, resume=True)

        # L1 的 call_json 不应该被调用（已跳过）
        # L1 的数据来自 checkpoint
        assert result.get_layer_data(1)["name"] == "王老师"

    def test_checkpoint_deleted_after_completion(self, sample_messages, mock_llm_client, tmp_path):
        """蒸馏全部完成后断点文件应被删除"""
        mock_llm_client.call_json.side_effect = _mock_layer_responses()

        engine = DistillationEngine(mock_llm_client, checkpoint_dir=tmp_path)
        persona = Persona(persona_name="test")
        engine.run(persona, sample_messages)

        ckpt_file = tmp_path / CHECKPOINT_FILENAME
        assert not ckpt_file.exists(), "蒸馏完成后断点文件未被清除"

    def test_no_checkpoint_dir_runs_fine(self, sample_messages, mock_llm_client):
        """不设置 checkpoint_dir 时应正常运行（不保存断点）"""
        mock_llm_client.call_json.side_effect = _mock_layer_responses()
        engine = DistillationEngine(mock_llm_client, checkpoint_dir=None)
        persona = Persona(persona_name="test")
        result = engine.run(persona, sample_messages)
        assert result.is_complete()


# ── helpers ──────────────────────────────────────────────────────────

def _mock_layer_responses() -> list[dict]:
    """为 7 个层提供独立的 mock LLM 返回"""
    return [
        # L1
        {"name": "王老师", "role": ["产品总监"], "background": "10年经验", "personality": "直接",
         "catchphrases": ["你再想想"], "red_lines": []},
        # L2
        {"domains": ["用户增长"], "expertise_level": {}, "knowledge_boundary": [],
         "preferred_tools": ["飞书"], "key_insights": ["数据说话"]},
        # L3
        {"problem_solving": "第一性原理", "decision_framework": "数据验证", "question_style": "反问式",
         "feedback_pattern": "先问后答", "common_patterns": [], "bias": []},
        # L4
        {"tone": "直接", "formality": "mixed", "structure": "问题→拆解→方向",
         "rhetoric": [], "emoji_usage": "sparse", "response_length": "adaptive",
         "typical_response_examples": []},
        # L5
        {"empathy_style": "快速切换", "encouragement_style": "具体夸奖", "frustration_signs": ["沉默"],
         "praise_style": "行为夸奖", "emotional_boundary": []},
        # L6
        {"mentoring_style": "引导式", "teaching_rhythm": "先问后给",
         "autonomy_grant": "给方向不给答案", "typical_scenarios": {},
         "growth_expectation": "3月独立拆解", "boundary_work_mentoring": ""},
        # L7
        {"active_projects": [], "open_commitments": [], "feedback_history": [],
         "apprentice_profile": {}, "next_check_ins": []},
    ]
