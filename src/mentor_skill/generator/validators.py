"""
Validators — Persona 验证器
"""
from __future__ import annotations

from mentor_skill.models.persona import Persona


class PersonaValidator:
    """在生成文件前进行最终检查"""

    def validate(self, persona: Persona) -> bool:
        # 1. 检查是否至少有 L1Identity
        if 1 not in persona.layers:
            return False

        # 2. 检查基本字段
        l1 = persona.get_layer_data(1)
        if not l1.get("name"):
            return False

        # v0.1: 允许部分层缺失，但给出警告
        missing = persona.missing_layers()
        if missing:
            from rich.console import Console
            console = Console()
            console.print(f"[yellow]⚠ 警告：部分层 ({missing}) 尚未蒸馏。[/yellow]")

        return True
