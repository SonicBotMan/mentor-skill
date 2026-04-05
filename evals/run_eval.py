"""
evals/run_eval.py — Skill 质量评估主脚本

用法：
  python evals/run_eval.py --persona sample-mentor --test-cases evals/test_cases/product_qa.json

评估流程：
  1. 加载 Persona → 生成 SKILL.md 系统提示词
  2. 逐条测试用例：发送用户输入 → 获取 AI 回复
  3. 用 LLM-as-judge 对每条回复打分
  4. 汇总并输出评估报告
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# 将项目 src 加入 path，支持直接运行（不安装包的场景）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mentor_skill.config import get_config
from mentor_skill.llm.base import LLMClient, LLMConfig
from mentor_skill.models.persona import Persona, LAYER_CLASSES
from evals.metrics import (
    MetricResult,
    JUDGE_SYSTEM_PROMPT,
    build_judge_prompt,
    aggregate_results,
)

app = typer.Typer()
console = Console()


def _load_persona(persona_name: str) -> Persona:
    cfg = get_config()
    p_file = Path(cfg.project.persona_dir) / persona_name / "persona.json"

    # fallback：从 evals/personas/ 加载样本 Persona
    if not p_file.exists():
        p_file = Path(__file__).parent / "personas" / persona_name / "persona.json"

    if not p_file.exists():
        console.print(f"[red]找不到 Persona 文件：{p_file}[/red]")
        raise typer.Exit(1)

    with open(p_file, encoding="utf-8") as f:
        data = json.load(f)
    if "layers" in data:
        raw = data["layers"]
        parsed = {}
        for k, v in raw.items():
            layer_id = int(k)
            cls = LAYER_CLASSES.get(layer_id)
            parsed[layer_id] = cls(**v) if cls and v else v
        data["layers"] = parsed
    return Persona(**data)


def _build_system_prompt(persona: Persona) -> str:
    """从 Persona 构建系统提示词（简化版，用于推理）"""
    from mentor_skill.generator.skill_md import SkillMDGenerator
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as f:
        tmp_path = Path(f.name)

    SkillMDGenerator().generate(persona, tmp_path)
    content = tmp_path.read_text(encoding="utf-8")
    tmp_path.unlink(missing_ok=True)
    return content


def _persona_summary(persona: Persona) -> str:
    """生成给 judge 用的 Persona 摘要"""
    l1 = persona.get_layer_data(1)
    l6 = persona.get_layer_data(6)
    return (
        f"导师：{persona.mentor_name}，{l1.get('background', '')}。"
        f"性格：{l1.get('personality', '')}。"
        f"口头禅：{', '.join(l1.get('catchphrases', []))}。"
        f"带人风格：{l6.get('mentoring_style', '')}。"
    )


@app.command()
def run(
    persona: str = typer.Option("sample-mentor", "--persona", "-p", help="导师 ID"),
    test_cases: str = typer.Option(
        str(Path(__file__).parent / "test_cases" / "product_qa.json"),
        "--test-cases", "-t",
        help="测试用例 JSON 文件路径（可用 product_qa / tech_qa / academic_qa）",
    ),
    output: str = typer.Option("", "--output", "-o", help="评估报告输出路径（留空则只打印）"),
    model: str = typer.Option("", "--model", help="指定评估模型（留空则使用配置中的模型）"),
    skip_cases: str = typer.Option("", "--skip", help="跳过的 case ID（逗号分隔）"),
):
    """运行 Skill 质量评估"""

    # 1. 加载 Persona & 测试用例
    console.rule("[bold blue]🔬 mentor-skill Eval Runner[/bold blue]")
    p_obj = _load_persona(persona)
    console.print(f"✅ 加载 Persona：[cyan]{p_obj.mentor_name}[/cyan]（{len(p_obj.layers)} 层）")

    with open(test_cases, encoding="utf-8") as f:
        tc_data = json.load(f)
    cases = tc_data.get("cases", [])
    skip_set = set(s.strip() for s in skip_cases.split(",") if s.strip())
    cases = [c for c in cases if c["id"] not in skip_set]
    console.print(f"✅ 加载测试用例：[cyan]{len(cases)}[/cyan] 条（来自 {tc_data.get('description', '')}）\n")

    # 2. 构建 LLM 客户端
    cfg = get_config()
    if not cfg.llm.api_key:
        console.print("[red]错误：请先配置 LLM API Key[/red]")
        raise typer.Exit(1)

    llm_cfg = LLMConfig(
        model=model or cfg.llm.model,
        api_base=cfg.llm.api_base or None,
        api_key=cfg.llm.api_key,
        temperature=0.3,
        max_tokens=1024,
        timeout=60,
    )
    client = LLMClient(llm_cfg)
    system_prompt = _build_system_prompt(p_obj)
    persona_summary = _persona_summary(p_obj)

    # 3. 逐条运行 & 评分
    results: list[MetricResult] = []

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=False) as progress:
        for case in cases:
            cid = case["id"]
            task = progress.add_task(f"[cyan]{cid}[/cyan] {case.get('scenario', '')[:30]}...", total=None)

            # 3a. 获取 AI 回复
            try:
                ai_reply = client.call(
                    prompt=case["user_input"],
                    system=system_prompt,
                    response_format="text",
                )
            except Exception as e:
                console.print(f"[red]Case {cid} 调用失败：{e}[/red]")
                results.append(MetricResult(cid, 0, 0, 0, reasoning=f"调用失败：{e}"))
                continue

            # 3b. LLM-as-judge 评分
            judge_prompt = build_judge_prompt(persona_summary, case, ai_reply)
            try:
                score_data = client.call_json(judge_prompt, system=JUDGE_SYSTEM_PROMPT)
                result = MetricResult(
                    case_id=cid,
                    score_style=float(score_data.get("score_style", 0)),
                    score_behavior=float(score_data.get("score_behavior", 0)),
                    score_followup=float(score_data.get("score_followup", 0)),
                    reasoning=score_data.get("reasoning", ""),
                    raw_response=ai_reply,
                )
            except Exception as e:
                console.print(f"[yellow]Case {cid} 评分失败：{e}，设为 0 分[/yellow]")
                result = MetricResult(cid, 0, 0, 0, reasoning=f"评分失败：{e}", raw_response=ai_reply)

            results.append(result)
            progress.update(task, description=f"[green]✅ {cid}[/green] 总分 {result.total:.1f}")
            time.sleep(0.5)  # 避免频控

    # 4. 汇总报告
    summary = aggregate_results(results)
    _print_report(summary, p_obj.mentor_name, results)

    # 5. 保存报告
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        console.print(f"\n[dim]报告已保存至：{out_path}[/dim]")


def _print_report(summary: dict, mentor_name: str, results: list[MetricResult]) -> None:
    avg = summary.get("avg_total_score", 0)
    grade = summary.get("grade", "")

    console.print()
    console.print(
        Panel(
            f"[bold]导师：{mentor_name}[/bold]\n"
            f"测试用例：{summary['total_cases']} 条\n\n"
            f"[bold cyan]综合得分：{avg:.2f} / 10[/bold cyan]  [bold]{grade}[/bold]\n\n"
            f"风格一致性：{summary['avg_style_consistency']:.2f}\n"
            f"行为合规性：{summary['avg_behavior_compliance']:.2f}\n"
            f"追问/记忆层：{summary['avg_proactive_followup']:.2f}",
            title="📊 Eval Report",
            border_style="blue",
        )
    )

    # 逐条表格
    table = Table(title="逐条评分明细")
    table.add_column("Case ID", style="cyan", width=8)
    table.add_column("场景", width=20)
    table.add_column("风格", justify="right")
    table.add_column("行为", justify="right")
    table.add_column("追问", justify="right")
    table.add_column("总分", justify="right", style="bold")
    table.add_column("评判理由", width=40)

    for r in results:
        table.add_row(
            r.case_id,
            "",
            f"{r.score_style:.1f}",
            f"{r.score_behavior:.1f}",
            f"{r.score_followup:.1f}",
            f"{r.total:.2f}",
            r.reasoning[:60] + ("..." if len(r.reasoning) > 60 else ""),
        )

    console.print(table)

    # AI 回复详情
    console.print("\n[bold]AI 回复详情：[/bold]")
    for r in results:
        if r.raw_response:
            console.print(Panel(r.raw_response, title=f"[cyan]{r.case_id}[/cyan]", expand=False))


if __name__ == "__main__":
    app()
