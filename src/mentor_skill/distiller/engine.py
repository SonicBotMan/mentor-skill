"""
DistillationEngine — 蒸馏引擎

按顺序执行 L1 到 L7 的蒸馏，支持断点保存与恢复。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from mentor_skill.llm.base import LLMClient
from mentor_skill.models.persona import Persona, LAYER_CLASSES
from .layers.l1_identity import L1Identity
from .layers.l2_knowledge import L2Knowledge
from .layers.l3_thinking import L3Thinking
from .layers.l4_communication import L4Communication
from .layers.l5_emotion import L5Emotion
from .layers.l6_mentorship import L6Mentorship
from .layers.l7_apprentice_memory import L7ApprenticeMemory

console = Console()

CHECKPOINT_FILENAME = "checkpoint.json"


class DistillationEngine:
    """按顺序驱动七层蒸馏逻辑，支持断点恢复"""

    def __init__(self, llm: LLMClient, checkpoint_dir: Optional[Path] = None):
        self.llm = llm
        self.checkpoint_dir = checkpoint_dir
        self.layer_instances = [
            L1Identity(llm),
            L2Knowledge(llm),
            L3Thinking(llm),
            L4Communication(llm),
            L5Emotion(llm),
            L6Mentorship(llm),
            L7ApprenticeMemory(llm),
        ]

    # ── checkpoint 工具 ──────────────────────────────────────────────

    def _checkpoint_path(self) -> Optional[Path]:
        if self.checkpoint_dir:
            return self.checkpoint_dir / CHECKPOINT_FILENAME
        return None

    def _save_checkpoint(self, persona: Persona) -> None:
        path = self._checkpoint_path()
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        data = persona.model_dump()
        if "layers" in data:
            data["layers"] = {str(k): v for k, v in data["layers"].items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"  [dim]💾 断点已保存：{path}[/dim]")

    def load_checkpoint(self) -> Optional[Persona]:
        """尝试加载断点，如不存在返回 None"""
        path = self._checkpoint_path()
        if not path or not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if "layers" in data:
            raw_layers = data["layers"]
            parsed: dict[int, Any] = {}
            for k, v in raw_layers.items():
                layer_id = int(k)
                cls = LAYER_CLASSES.get(layer_id)
                parsed[layer_id] = cls(**v) if cls and v else v
            data["layers"] = parsed
        persona = Persona(**data)
        completed = sorted(persona.layers.keys())
        console.print(
            Panel(
                f"[green]发现断点文件：{path}[/green]\n"
                f"已完成层：{completed}\n"
                f"将从第 [bold]{max(completed) + 1}[/bold] 层继续",
                title="🔄 断点恢复",
                border_style="yellow",
            )
        )
        return persona

    # ── 成本预估 ─────────────────────────────────────────────────────

    def _print_cost_estimate(self, data: List[Any], pending_count: int) -> None:
        """在蒸馏前打印 token 用量和费用预估（粗略估算）"""
        # 按每个汉字 ~1.5 token 估算输入语料 token 数
        total_chars = sum(len(getattr(m, "content", str(m))) for m in data)
        input_tokens_per_layer = int(total_chars * 1.5)
        # 每层系统 prompt + 输出约 2000 token
        output_tokens_per_layer = 2000
        total_input = input_tokens_per_layer * pending_count
        total_output = output_tokens_per_layer * pending_count
        total_tokens = total_input + total_output

        # 简单价格表（单位：元/1000 token，输入/输出）
        model = self.llm.config.model.lower()
        PRICE_TABLE: dict[str, tuple[float, float]] = {
            "glm-4-flash": (0.0, 0.0),           # 免费
            "glm-4": (0.1, 0.1),
            "deepseek-chat": (0.001, 0.002),
            "qwen-turbo": (0.003, 0.006),
            "gpt-4o-mini": (0.11, 0.44),
            "gpt-4o": (1.75, 5.25),
            "claude-3-haiku": (0.17, 0.85),
        }
        price_in, price_out = next(
            (v for k, v in PRICE_TABLE.items() if k in model),
            (0.05, 0.15),  # 默认估算
        )
        est_cost = (total_input / 1000 * price_in) + (total_output / 1000 * price_out)

        if price_in == 0 and price_out == 0:
            cost_str = "[green]免费（当前模型）[/green]"
        elif est_cost < 0.01:
            cost_str = "[green]< ¥0.01[/green]"
        else:
            cost_str = f"[yellow]约 ¥{est_cost:.2f}[/yellow]"

        console.print(
            f"[dim]预估用量：{total_tokens:,} tokens（输入 {total_input:,} + 输出 {total_output:,}）  |  预估费用：{cost_str}[/dim]\n"
        )

    # ── 主流程 ──────────────────────────────────────────────────────

    def run(
        self,
        persona: Persona,
        data: List[Any],
        interactive: bool = False,
        resume: bool = False,
    ) -> Persona:
        """
        全自动化流程

        Args:
            persona: 初始 Persona 对象（resume=True 时会被 checkpoint 覆盖）
            data: RawMessage 或 DialogPair 列表
            interactive: 是否开启逐层确认模式
            resume: 是否从断点继续（需要 checkpoint_dir 已设置）
        """
        # 尝试断点恢复
        if resume:
            ckpt = self.load_checkpoint()
            if ckpt:
                persona = ckpt
            else:
                console.print("[yellow]未找到断点文件，从头开始蒸馏。[/yellow]")

        already_done = set(persona.layers.keys())
        pending_layers = [layer for layer in self.layer_instances if layer.LAYER_ID not in already_done]

        if not pending_layers:
            console.print("[bold green]所有层均已蒸馏，无需重新运行。[/bold green]")
            return persona

        skip_note = f"  [dim](已跳过层 {sorted(already_done)})[/dim]" if already_done else ""
        console.print(
            f"[bold blue]🚀 开始对 [white]{persona.persona_name}[/white] 的蒸馏流程...[/bold blue]{skip_note}"
        )
        console.print(f"[dim]模型：{self.llm.config.model}  |  待蒸馏层数：{len(pending_layers)}/7[/dim]")

        # Token 成本预估
        self._print_cost_estimate(data, len(pending_layers))

        total_layers = len(pending_layers)
        layer_times: list[float] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=20),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TextColumn("[dim]预计剩余[/dim]"),
            TimeRemainingColumn(),
            transient=False,
        ) as progress:
            main_task = progress.add_task(
                description="[bold]蒸馏进度[/bold]",
                total=total_layers,
            )

            for layer in pending_layers:
                layer_desc = f"[cyan]L{layer.LAYER_ID}[/cyan] {layer.LAYER_NAME}"
                progress.update(main_task, description=f"{layer_desc}...")

                t0 = time.time()
                persona = layer.distill(persona, data, interactive=interactive)
                elapsed = time.time() - t0
                layer_times.append(elapsed)

                persona.distilled_by = self.llm.config.model

                progress.update(
                    main_task,
                    advance=1,
                    description=f"[green]✅ L{layer.LAYER_ID} {layer.LAYER_NAME}[/green] [dim]({elapsed:.1f}s)[/dim]",
                )

                # 每层完成后保存断点
                self._save_checkpoint(persona)

                if interactive:
                    persona = self._interactive_confirm(layer.LAYER_ID, layer.LAYER_NAME, persona, data)

        total_elapsed = sum(layer_times)
        avg_per_layer = total_elapsed / len(layer_times) if layer_times else 0
        console.print(
            f"\n[bold green]✨ 导师 Persona 蒸馏成功！[/bold green]  "
            f"[dim]用时 {total_elapsed:.1f}s，平均每层 {avg_per_layer:.1f}s[/dim]"
        )

        # 只在全部 7 层完成时清除断点，部分完成时保留供 --resume 使用
        if persona.is_complete():
            ckpt_path = self._checkpoint_path()
            if ckpt_path and ckpt_path.exists():
                ckpt_path.unlink()
                console.print("[dim]断点文件已清除。[/dim]")

        return persona

    def _interactive_confirm(
        self,
        layer_id: int,
        layer_name: str,
        persona: Persona,
        data: List[Any],
    ) -> Persona:
        """交互式逐层确认，返回（可能已修改的）Persona"""
        import yaml

        while True:
            layer_data = persona.get_layer_data(layer_id)
            console.print(
                Panel(
                    yaml.dump(layer_data, allow_unicode=True, default_flow_style=False),
                    title=f"[bold]L{layer_id} {layer_name} 蒸馏结果[/bold]",
                    border_style="blue",
                )
            )
            action = console.input(
                "[bold]操作：[/bold]"
                "[[green]y[/green]] 确认继续  "
                "[[yellow]e[/yellow]] 手动编辑字段  "
                "[[red]r[/red]] 重新蒸馏 > "
            ).strip().lower()

            if action in ("y", ""):
                break

            elif action == "e":
                field_name = console.input("输入要修改的字段名：").strip()
                new_value_str = console.input(f"输入 {field_name} 的新值（JSON 格式）：").strip()
                try:
                    import json as _json
                    new_value = _json.loads(new_value_str)
                    layer_obj = persona.get_layer(layer_id)
                    if layer_obj and hasattr(layer_obj, field_name):
                        setattr(layer_obj, field_name, new_value)
                        console.print(f"[green]✅ 已更新 {field_name}[/green]")
                        self._save_checkpoint(persona)
                    else:
                        console.print(f"[red]字段 {field_name} 不存在[/red]")
                except Exception as ex:
                    console.print(f"[red]解析失败：{ex}[/red]")

            elif action == "r":
                console.print(f"[yellow]重新蒸馏 L{layer_id}...[/yellow]")
                for inst in self.layer_instances:
                    if inst.LAYER_ID == layer_id:
                        persona = inst.distill(persona, data, interactive=False)
                        self._save_checkpoint(persona)
                        break
                # 重蒸馏后再次展示结果

        return persona
