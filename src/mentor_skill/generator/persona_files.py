"""
PersonaFileGenerator — Persona 序列化与存储
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from rich.console import Console

from mentor_skill.models.persona import Persona

console = Console()


class PersonaFileGenerator:
    """负责将 Persona 对象持久化为 YAML/JSON"""

    def save(self, persona: Persona, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 保存为完整 YAML (人类友好)
        yaml_path = output_dir / "persona.yaml"
        # 直接 dump model 会丢失一些元数据，这里用 model_dump
        data = persona.model_dump()

        # 将枚举或 int key 转为 string 以适配 YAML
        if "layers" in data:
            data["layers"] = {str(k): v for k, v in data["layers"].items()}

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        # 2. 保存为 JSON (机器友好)
        json_path = output_dir / "persona.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        console.print(f"  [green]✓[/green] Persona 已保存至 {yaml_path}")
        return yaml_path
