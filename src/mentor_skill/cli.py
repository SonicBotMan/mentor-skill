"""
mentor-skill CLI — 终端交互入口

使用 Typer 构建，支持 Rich 渲染。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mentor_skill.config import get_config, save_config
from mentor_skill.models.persona import Persona

app = typer.Typer(
    name="mentor",
    help="导师.SKILL (mentor-skill) — 把你的导师蒸馏成 AI Skill。",
    add_completion=False,
)
console = Console()

# 保存内置 list 类型的引用；CLI 命令实现为 list_personas + @app.command("list")，
# 避免 def list 遮蔽 builtins.list（isinstance、Typer 子命令解析均会受影响）。
_list_type = list


@app.command()
def init(
    name: str = typer.Option(..., help="导师名称 (如: wang-laoshi)"),
    template: str = typer.Option("product", help="模板类型: product, tech, academic"),
):
    """初始化一个新的导师蒸馏项目"""
    console.print(f"[bold green]✨ 正在初始化项目：{name} (模板: {template})[/bold green]")

    # 创建目录结构
    cfg = get_config()
    persona_dir = Path(cfg.project.persona_dir) / name
    data_dir = Path(cfg.project.data_dir) / name

    persona_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # 写一个初始 YAML
    initial_persona = Persona(persona_name=name)
    from mentor_skill.generator.persona_files import PersonaFileGenerator
    PersonaFileGenerator().save(initial_persona, persona_dir)

    console.print("  [blue]目录设计：[/blue]")
    console.print(f"  - 原始数据目录: [cyan]{data_dir}[/cyan]")
    console.print(f"  - Persona 存储目录: [cyan]{persona_dir}[/cyan]")
    console.print("\n[bold yellow]下一步：[/bold yellow] 请使用 `mentor collect` 采集导师的数据。")


@app.command()
def collect(
    source: str = typer.Option(..., help="数据源类型: markdown, pdf, wechat, feishu, dingtalk"),
    input: str = typer.Option(None, "--input", "-i", help="文件或目录路径"),
    persona: str = typer.Option(..., help="目标导师 ID (对应 init 时起的名称)"),
    name: str = typer.Option(None, help="导师在平台上的真实姓名 (搜索用)"),
):
    """从不同平台采集导师数据"""
    from mentor_skill.collectors import (
        MarkdownCollector, PDFCollector, WechatCollector, FeishuCollector, DingtalkCollector
    )

    cfg = get_config()
    target_data_dir = Path(cfg.project.data_dir) / persona
    target_data_dir.mkdir(parents=True, exist_ok=True)

    collector_map = {
        "markdown": MarkdownCollector,
        "pdf": PDFCollector,
        "wechat": WechatCollector,
        "feishu": FeishuCollector,
        "dingtalk": DingtalkCollector,
    }

    if source not in collector_map:
        console.print(f"[red]错误：不支持的数据源 {source}[/red]")
        raise typer.Exit(1)

    collector = collector_map[source](cfg.model_dump())

    # 执行采集
    if source in ("markdown", "pdf", "wechat"):
        if not input:
            console.print("[red]错误：本地采集源必须指定 --input[/red]")
            raise typer.Exit(1)
        messages = collector.collect(input_path=input if source != "wechat" else None, input_file=input if source == "wechat" else None, mentor_name=name or persona)
    else:
        # 飞书、钉钉 API 模式
        messages = collector.collect(mentor_name=name or persona)

    # 保存结果
    if messages:
        output_file = target_data_dir / f"{source}_raw.json"
        import json
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in messages], f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]✅ 成功采集 {len(messages)} 条原始记录，已存至 {output_file}[/bold green]")
    else:
        console.print("[yellow]⚠ 采集结束，但未发现有效数据。[/yellow]")


@app.command()
def analyze(
    persona: str = typer.Option(..., help="目标导师 ID"),
    stats: bool = typer.Option(True, help="显示统计报表"),
):
    """分析已采集数据的内容质量"""
    from mentor_skill.analyzers import DataCleaner, StatsAnalyzer, QualityAssessor
    import json

    cfg = get_config()
    data_path = Path(cfg.project.data_dir) / persona

    # 加载所有 raw 文件
    all_raw_msgs = []
    from mentor_skill.models.raw_message import RawMessage
    from datetime import datetime

    for f in data_path.glob("*_raw.json"):
        with open(f, encoding="utf-8") as jf:
            data_list = json.load(jf)
            for d in data_list:
                d['timestamp'] = datetime.fromisoformat(d['timestamp'])
                all_raw_msgs.append(RawMessage(**d))

    if not all_raw_msgs:
        console.print("[red]错误：未发现采集数据，请先运行 mentor collect[/red]")
        raise typer.Exit(1)

    # 清洗
    cleaner = DataCleaner()
    cleaned = cleaner.clean(all_raw_msgs)

    # 统计
    analyzer = StatsAnalyzer()
    stats_info = analyzer.analyze(cleaned)

    # 质量评估
    assessor = QualityAssessor()
    score = assessor.assess(stats_info)

    # 渲染报表
    if stats:
        # 评分颜色
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"

        table = Table(title=f"[bold]📊 {persona} 数据质量报告[/bold]", show_lines=False)
        table.add_column("维度", style="cyan", width=20)
        table.add_column("数值", style="magenta", width=16)
        table.add_column("说明", style="dim")
        table.add_row("总消息数（清洗后）", str(stats_info.total_messages), "过滤噪声、重复和非文本后")
        table.add_row("导师消息数", str(stats_info.mentor_messages), "仅统计 is_mentor=True")
        table.add_row("高价值消息数", str(stats_info.high_value_count), f"≥{assessor.HIGH_VALUE_MIN_LEN}字 的深度消息")
        table.add_row("高价值比例", f"{stats_info.high_value_ratio:.1%}", "高价值 / 导师消息")
        table.add_row("平均消息长度", f"{stats_info.avg_length:.0f} 字", "导师消息平均字数")
        table.add_row(
            "质量总分",
            f"[{score_color}][bold]{score}[/bold][/{score_color}] / 100",
            assessor.get_recommendation(score),
        )
        console.print(table)

        # 达标提示
        if score < 60:
            console.print("\n[red]⚠ 数据量不足，蒸馏效果可能较差。建议至少采集 100 条高价值消息。[/red]")
        elif score < 80:
            console.print("\n[yellow]⚡ 数据质量中等，可以继续蒸馏，但建议补充更多深度对话。[/yellow]")
        else:
            console.print("\n[green]✅ 数据质量优秀，可以开始蒸馏。[/green]")

        # Top-5 高价值消息预览
        high_value_msgs = sorted(
            [m for m in cleaned if m.is_high_value and m.is_mentor],
            key=lambda m: len(m.content),
            reverse=True,
        )[:5]

        if high_value_msgs:
            console.print("\n[bold]Top-5 高价值消息预览（按长度排序）：[/bold]")
            from rich.panel import Panel as _Panel
            for i, msg in enumerate(high_value_msgs, 1):
                preview = msg.content[:300].replace("\n", " ")
                if len(msg.content) > 300:
                    preview += "…"
                console.print(_Panel(
                    preview,
                    title=f"[dim]#{i}  {len(msg.content)} 字  [{msg.source}]  {msg.timestamp.strftime('%Y-%m-%d')}[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                ))


@app.command()
def distill(
    persona: str = typer.Option(..., help="目标导师 ID"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="开启交互模式（逐层确认）"),
    resume: bool = typer.Option(False, "--resume", help="从上次断点继续蒸馏"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只展示蒸馏计划和 token 预估，不执行"),
):
    """执行 7 层深度蒸馏 (核心引擎)"""
    from mentor_skill.llm import LLMClient
    from mentor_skill.distiller import DistillationEngine
    from mentor_skill.analyzers import DialogExtractor
    import json
    from mentor_skill.models.raw_message import RawMessage
    from datetime import datetime

    cfg = get_config()
    if not dry_run and not cfg.llm.api_key:
        console.print("[red]错误：未检测到 LLM API Key，请先配置。[/red]")
        console.print("[yellow]提示：使用 `mentor config --set llm.api_key YOUR_KEY` 设置智谱/DeepSeek等[/yellow]")
        raise typer.Exit(1)

    # 1. 加载并准备数据
    data_path = Path(cfg.project.data_dir) / persona
    all_msgs: list[RawMessage] = []
    for f in data_path.glob("*_raw.json"):
        with open(f, encoding="utf-8") as jf:
            for d in json.load(jf):
                d["timestamp"] = datetime.fromisoformat(d["timestamp"])
                all_msgs.append(RawMessage(**d))

    if not all_msgs and not resume:
        console.print("[red]错误：未发现采集数据，请先运行 mentor collect[/red]")
        raise typer.Exit(1)

    # 提取 Q&A
    extractor = DialogExtractor()
    pairs = extractor.extract(all_msgs, mentor_name=persona)
    distill_data = pairs + [m for m in all_msgs if m.is_high_value]

    # dry-run：只打印计划，不执行蒸馏
    if dry_run:
        from rich.panel import Panel as _Panel

        total_chars = sum(len(getattr(m, "content", str(m))) for m in distill_data)
        input_tokens = int(total_chars * 1.5)
        output_tokens = 2000 * 7
        total_tokens = input_tokens + output_tokens

        model = cfg.llm.model if cfg.llm.api_key else "(未配置)"
        console.print(_Panel(
            f"[bold]蒸馏对象：[/bold]{persona}\n"
            f"[bold]输入数据：[/bold]{len(all_msgs)} 条原始消息  →  {len(distill_data)} 条蒸馏素材\n"
            f"[bold]LLM 模型：[/bold]{model}\n"
            f"[bold]待执行层：[/bold]L1 → L2 → L3 → L4 → L5 → L6 → L7（7 层）\n"
            f"[bold]预估 Token：[/bold]{total_tokens:,}（输入 {input_tokens:,} + 输出 {output_tokens:,}）\n"
            f"[bold]预估耗时：[/bold]5 ~ 20 分钟（取决于 LLM 响应速度）",
            title="[cyan]🔍 dry-run 蒸馏计划[/cyan]",
            border_style="cyan",
        ))
        console.print("\n[dim]去掉 --dry-run 参数，即可正式执行蒸馏。[/dim]")
        return

    # 2. 运行引擎（checkpoint 存放在 persona_dir 下）
    checkpoint_dir = Path(cfg.project.persona_dir) / persona
    client = LLMClient.from_app_config()
    engine = DistillationEngine(client, checkpoint_dir=checkpoint_dir)

    p_obj = Persona(persona_name=persona)
    final_persona = engine.run(p_obj, distill_data, interactive=interactive, resume=resume)

    # 3. 保存最终 Persona
    from mentor_skill.generator.persona_files import PersonaFileGenerator
    PersonaFileGenerator().save(final_persona, checkpoint_dir)
    console.print(
        f"\n[bold green]✅ 蒸馏完成！[/bold green]  下一步：[cyan]mentor generate --persona {persona}[/cyan]"
    )


# 支持的输出格式
FORMAT_CHOICES = ["generic", "cursor", "claude", "openclaw", "all"]


@app.command()
def generate(
    persona: str = typer.Option(..., help="目标导师 ID"),
    format: str = typer.Option(
        "all",
        "--format", "-f",
        help=f"输出格式：{' | '.join(FORMAT_CHOICES)}（all = 同时生成所有格式）",
    ),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="自定义输出目录"),
):
    """生成导师 Skill 文件（支持多平台格式）"""
    import json
    from rich.table import Table
    from mentor_skill.models.persona import Persona
    from mentor_skill.generator import (
        SkillMDGenerator, CursorRuleGenerator, ClaudeSkillGenerator,
        OpenClawSkillGenerator, PersonaValidator,
    )

    if format not in FORMAT_CHOICES:
        console.print(f"[red]不支持的格式 [{format}]，可选：{FORMAT_CHOICES}[/red]")
        raise typer.Exit(1)

    cfg = get_config()
    p_dir = Path(cfg.project.persona_dir) / persona
    p_file = p_dir / "persona.json"

    if not p_file.exists():
        console.print("[red]错误：未找到蒸馏后的 Persona 数据，请先运行 mentor distill[/red]")
        raise typer.Exit(1)

    with open(p_file, encoding="utf-8") as f:
        p_data = json.load(f)
        if "layers" in p_data:
            p_data["layers"] = {int(k): v for k, v in p_data["layers"].items()}
        p_obj = Persona(**p_data)

    if not PersonaValidator().validate(p_obj):
        console.print("[red]错误：Persona 数据校验失败。[/red]")
        raise typer.Exit(1)

    out_dir = Path(output_dir) if output_dir else p_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 格式 → (生成器, 文件名) 映射
    generators: dict[str, tuple] = {
        "generic": (SkillMDGenerator(),    f"{persona}.SKILL.md"),
        "cursor":  (CursorRuleGenerator(), f"{persona}.mdc"),
        "claude":  (ClaudeSkillGenerator(), f"{persona}.claude.SKILL.md"),
        "openclaw":(OpenClawSkillGenerator(), f"{persona}.openclaw.skill.md"),
    }

    targets = list(generators.items()) if format == "all" else [(format, generators[format])]

    table = Table(title=f"[bold]📦 {persona} Skill 生成结果[/bold]")
    table.add_column("格式", style="cyan", width=10)
    table.add_column("文件", style="white")
    table.add_column("状态", style="green")

    for fmt_name, (gen, filename) in targets:
        out_path = out_dir / filename
        try:
            gen.generate(p_obj, out_path)
            table.add_row(fmt_name, str(out_path.absolute()), "✅ 成功")
        except Exception as e:
            table.add_row(fmt_name, filename, f"[red]❌ 失败：{e}[/red]")

    console.print(table)
    console.print("\n[dim]提示：Cursor 格式（.mdc）可放入项目的 .cursor/rules/ 目录直接生效[/dim]")


@app.command()
def test(
    persona: str = typer.Option(..., help="目标导师 ID"),
    ask: Optional[str] = typer.Option(None, "--ask", "-q", help="单次提问（非交互模式）"),
    skill_file: Optional[str] = typer.Option(None, "--skill-file", help="手动指定 .SKILL.md 路径"),
    rounds: int = typer.Option(10, help="交互模式最大对话轮数"),
):
    """与蒸馏后的导师 Persona 对话，验证 Skill 效果"""
    cfg = get_config()

    if not cfg.llm.api_key:
        console.print("[red]错误：未检测到 LLM API Key，请先运行 mentor config --set llm.api_key YOUR_KEY[/red]")
        raise typer.Exit(1)

    # 定位 .SKILL.md
    if skill_file:
        skill_path = Path(skill_file)
    else:
        skill_path = Path(cfg.project.persona_dir) / persona / f"{persona}.SKILL.md"

    if not skill_path.exists():
        console.print(f"[red]错误：未找到 {skill_path}，请先运行 mentor generate --persona {persona}[/red]")
        raise typer.Exit(1)

    system_prompt = skill_path.read_text(encoding="utf-8")

    # 构建对话历史
    history: list[dict] = []

    def _chat(user_input: str) -> str:
        """单次对话（带历史）"""
        import litellm

        history.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": system_prompt}] + history

        kwargs: dict = {
            "model": cfg.llm.model,
            "messages": messages,
            "temperature": cfg.llm.temperature,
            "max_tokens": cfg.llm.max_tokens,
            "timeout": cfg.llm.timeout,
        }
        if cfg.llm.api_base:
            kwargs["api_base"] = cfg.llm.api_base
        if cfg.llm.api_key:
            kwargs["api_key"] = cfg.llm.api_key

        response = litellm.completion(**kwargs)
        reply = response.choices[0].message.content or ""
        history.append({"role": "assistant", "content": reply})
        return reply

    # 打印标题
    console.rule(f"[bold blue]🧑‍🏫 与导师 [{persona}] 对话中[/bold blue]")
    console.print(f"[dim]Skill 文件：{skill_path}[/dim]")
    console.print(f"[dim]模型：{cfg.llm.model}  |  输入 [bold]/quit[/bold] 或 Ctrl+C 退出[/dim]\n")

    # 单次模式
    if ask:
        console.print(f"[bold cyan]你：[/bold cyan]{ask}")
        with console.status("[bold green]导师思考中...[/bold green]"):
            reply = _chat(ask)
        console.print(f"\n[bold yellow]{persona}：[/bold yellow]{reply}\n")
        return

    # 交互多轮模式
    round_count = 0
    while round_count < rounds:
        try:
            user_input = typer.prompt(f"[第{round_count + 1}轮] 你")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]对话结束。[/dim]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("/quit", "/exit", "exit", "quit"):
            console.print("[dim]对话结束。[/dim]")
            break

        with console.status("[bold green]导师思考中...[/bold green]"):
            try:
                reply = _chat(user_input)
            except Exception as e:
                console.print(f"[red]调用失败：{e}[/red]")
                break

        console.print(f"\n[bold yellow]{persona}：[/bold yellow]{reply}\n")
        round_count += 1

    # 打印对话摘要
    if history:
        console.rule("[dim]对话结束[/dim]")
        console.print(f"[dim]共 {len(history) // 2} 轮对话。[/dim]")


@app.command()
def config(
    set: Optional[str] = typer.Option(None, "--set", help="设置配置项 (格式: key1.key2=value)"),
    preset: Optional[str] = typer.Option(None, "--preset", help="快速配置 LLM 预设: zhipu/deepseek/qwen/minimax/openai"),
    show: bool = typer.Option(True, help="显示当前配置"),
):
    """查看或修改全局配置（支持 --preset 一键配置 LLM）"""
    from mentor_skill.config import LLM_PRESETS
    import yaml

    cfg = get_config()

    # --preset 一键配置 LLM
    if preset:
        preset_lower = preset.lower()
        if preset_lower not in LLM_PRESETS:
            console.print(f"[red]未知预设 [{preset}]，可用预设：{', '.join(LLM_PRESETS.keys())}[/red]")
            raise typer.Exit(1)
        p = LLM_PRESETS[preset_lower]
        cfg.llm.model = p["default_model"]
        if p["api_base"]:
            cfg.llm.api_base = p["api_base"]
        else:
            cfg.llm.api_base = None
        save_config(cfg)
        console.print(f"[bold green]✅ 已应用 [{p['display_name']}] 预设[/bold green]")
        console.print(f"  模型：[cyan]{cfg.llm.model}[/cyan]")
        if cfg.llm.api_base:
            console.print(f"  API Base：[cyan]{cfg.llm.api_base}[/cyan]")
        console.print("\n[yellow]别忘了设置 API Key：[/yellow]  [cyan]mentor config --set llm.api_key YOUR_KEY[/cyan]")

    # --set 设置单个配置项
    if set:
        if "=" not in set:
            console.print("[red]格式错误，应为 key.subkey=value[/red]")
            raise typer.Exit(1)
        key, val = set.split("=", 1)
        keys = key.split(".")
        if len(keys) == 2:
            section = getattr(cfg, keys[0], None)
            if section and hasattr(section, keys[1]):
                orig_attr = getattr(section, keys[1])
                if isinstance(orig_attr, int): val = int(val)
                elif isinstance(orig_attr, float): val = float(val)
                setattr(section, keys[1], val)
                save_config(cfg)
                console.print(f"[green]已更新 {key} = {val}[/green]")
            else:
                console.print(f"[red]配置项不存在：{key}[/red]")
        else:
            console.print("[red]只支持两层配置项（如 llm.api_key）[/red]")

    if show and not set and not preset:
        console.print("[bold blue]当前配置：[/bold blue]")
        console.print(yaml.dump(cfg.model_dump(), allow_unicode=True, default_flow_style=False))
        console.print("[dim]使用 --set 修改配置项，或 --preset 一键配置 LLM[/dim]")


@app.command("list", help="列出所有已创建的导师 Persona")
def list_personas(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细层信息"),
):
    """列出所有已创建的导师 Persona（实现函数名为 list_personas，避免遮蔽内置 list 导致 Typer 解析异常）"""
    import json as _json
    from rich.panel import Panel

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)

    if not persona_root.exists():
        console.print("[yellow]暂无任何 Persona，请先运行 mentor init[/yellow]")
        return

    dirs = [d for d in sorted(persona_root.iterdir()) if d.is_dir()]
    if not dirs:
        console.print("[yellow]暂无任何 Persona，请先运行 mentor init[/yellow]")
        return

    table = Table(title="[bold]🧑‍🏫 已有导师 Persona[/bold]", show_lines=True)
    table.add_column("ID", style="cyan", width=20)
    table.add_column("导师姓名", style="white", width=12)
    table.add_column("完成层数", justify="center", width=10)
    table.add_column("蒸馏模型", style="dim", width=16)
    table.add_column("文件", style="dim")

    for d in dirs:
        p_file = d / "persona.json"
        ck_file = d / "checkpoint.json"
        skill_file = next(d.glob("*.SKILL.md"), None)

        if not p_file.exists() and not ck_file.exists():
            table.add_row(d.name, "-", "-", "-", "（未蒸馏）")
            continue

        src = p_file if p_file.exists() else ck_file
        try:
            with open(src, encoding="utf-8") as f:
                data = _json.load(f)
            layers_done = len(data.get("layers", {}))
            model = data.get("distilled_by", "-") or "-"
            l1 = data.get("layers", {}).get("1", {})
            mentor_name = l1.get("name", d.name) if isinstance(l1, dict) else d.name

            files_info = []
            if p_file.exists():    files_info.append("persona.json ✓")
            if ck_file.exists():   files_info.append("checkpoint.json ⏸")
            if skill_file:         files_info.append(f"{skill_file.name} ✓")

            layer_display = f"{layers_done}/7" + (" ✅" if layers_done == 7 else " ⏳")
            table.add_row(d.name, mentor_name, layer_display, model[:16], " | ".join(files_info))

        except Exception as e:
            table.add_row(d.name, "-", "读取失败", "-", str(e)[:30])

    console.print(table)

    if verbose:
        for d in dirs:
            p_file = d / "persona.json"
            if not p_file.exists():
                continue
            try:
                with open(p_file, encoding="utf-8") as f:
                    data = _json.load(f)
                l1 = data.get("layers", {}).get("1", {})
                if isinstance(l1, dict):
                    console.print(Panel(
                        f"[bold]姓名：[/bold]{l1.get('name', '-')}\n"
                        f"[bold]背景：[/bold]{l1.get('background', '-')}\n"
                        f"[bold]口头禅：[/bold]{', '.join(l1.get('catchphrases', []))}\n"
                        f"[bold]缺失层：[/bold]{[i for i in range(1,8) if str(i) not in data.get('layers', {})]}",
                        title=f"[cyan]{d.name}[/cyan] 详情",
                        expand=False,
                    ))
            except Exception:
                pass


@app.command()
def demo(
    ask: Optional[str] = typer.Option(None, "--ask", "-q", help="单次提问（非交互）"),
    full: bool = typer.Option(False, "--full", help="演示完整 pipeline（init→collect→distill→generate）"),
):
    """使用内置 Sample Persona 演示 Skill 效果（无需真实数据）"""
    import tempfile
    import json as _json

    from rich.panel import Panel

    # __file__ = src/mentor_skill/cli.py → .parent×3 = project root
    DEMO_PERSONA_DIR = Path(__file__).parent.parent.parent / "evals" / "personas" / "sample_mentor"
    # 备用路径：相对于安装包
    if not DEMO_PERSONA_DIR.exists():
        DEMO_PERSONA_DIR = Path(__file__).parent.parent / "_demo_persona"

    if not DEMO_PERSONA_DIR.exists():
        console.print("[red]找不到内置 demo Persona，请确认 evals/personas/sample_mentor/ 存在[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        "[bold cyan]导师.SKILL Demo 模式[/bold cyan]\n\n"
        "使用内置的「王老师」Sample Persona 演示蒸馏效果。\n"
        "王老师：10年互联网产品经验，直接务实，擅长用反问引导思考。\n\n"
        "[dim]想用自己的真实数据？运行 mentor init --name 你的导师名[/dim]",
        border_style="blue",
    ))

    if full:
        _demo_full_pipeline()
        return

    # 读取 sample persona
    p_file = DEMO_PERSONA_DIR / "persona.json"
    with open(p_file, encoding="utf-8") as f:
        data = _json.load(f)
    if "layers" in data:
        data["layers"] = {int(k): v for k, v in data["layers"].items()}
    from mentor_skill.models.persona import Persona, LAYER_CLASSES
    for k, v in data["layers"].items():
        cls = LAYER_CLASSES.get(k)
        if cls and isinstance(v, dict):
            data["layers"][k] = cls(**v)
    p_obj = Persona(**data)

    # 生成临时 SKILL.md 用于对话
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "wang-laoshi.SKILL.md"
        from mentor_skill.generator.skill_md import SkillMDGenerator
        SkillMDGenerator().generate(p_obj, skill_path)

        cfg = get_config()
        if not cfg.llm.api_key:
            # 无 API Key 时展示生成的 SKILL.md 内容作为 demo
            console.print("\n[yellow]⚠ 未配置 LLM API Key，展示 SKILL.md 内容作为示例：[/yellow]\n")
            console.print(Panel(
                skill_path.read_text(encoding="utf-8")[:3000],
                title="[bold]wang-laoshi.SKILL.md（前 3000 字）[/bold]",
                border_style="green",
            ))
            console.print(
                "\n[dim]配置 LLM 后可与王老师实时对话：[/dim]\n"
                "[cyan]  mentor config --set llm.api_key YOUR_KEY\n"
                "  mentor demo --ask '老师，帮我看看这个方案'[/cyan]"
            )
            return

        # 有 API Key，直接调起对话
        console.print("[bold green]✅ 正在连接王老师...[/bold green]\n")

        # 复用 test 命令的对话逻辑
        # 直接调 test 的核心逻辑，而不是走 CLI runner
        _run_demo_chat(p_obj, skill_path, ask)


def _run_demo_chat(persona: Persona, skill_path: Path, ask: Optional[str]) -> None:
    """Demo 对话的核心逻辑（复用 test 命令实现）"""
    import litellm
    from mentor_skill.config import get_config

    cfg = get_config()
    system_prompt = skill_path.read_text(encoding="utf-8")
    history: list[dict] = []

    def _chat(user_input: str) -> str:
        history.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": system_prompt}] + history
        kwargs: dict = {
            "model": cfg.llm.model,
            "messages": messages,
            "temperature": cfg.llm.temperature,
            "max_tokens": cfg.llm.max_tokens,
            "timeout": cfg.llm.timeout,
        }
        if cfg.llm.api_base:
            kwargs["api_base"] = cfg.llm.api_base
        if cfg.llm.api_key:
            kwargs["api_key"] = cfg.llm.api_key
        resp = litellm.completion(**kwargs)
        reply = resp.choices[0].message.content or ""
        history.append({"role": "assistant", "content": reply})
        return reply

    mentor_name = persona.mentor_name
    console.rule(f"[bold blue]🧑‍🏫 与导师 [{mentor_name}] 对话（Demo）[/bold blue]")
    console.print(f"[dim]模型：{cfg.llm.model}  |  输入 /quit 退出[/dim]\n")

    if ask:
        console.print(f"[bold cyan]你：[/bold cyan]{ask}")
        with console.status("[bold green]王老师思考中...[/bold green]"):
            reply = _chat(ask)
        console.print(f"\n[bold yellow]{mentor_name}：[/bold yellow]{reply}\n")
        return

    round_count = 0
    while round_count < 20:
        try:
            user_input = typer.prompt(f"[第{round_count+1}轮] 你")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Demo 结束。[/dim]")
            break
        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("/quit", "/exit", "exit", "quit"):
            console.print("[dim]Demo 结束。[/dim]")
            break
        with console.status("[bold green]王老师思考中...[/bold green]"):
            try:
                reply = _chat(user_input)
            except Exception as e:
                console.print(f"[red]调用失败：{e}[/red]")
                break
        console.print(f"\n[bold yellow]{mentor_name}：[/bold yellow]{reply}\n")
        round_count += 1


def _demo_full_pipeline() -> None:
    """展示完整 pipeline 的 dry-run 演示（不调用真实 LLM）"""
    from rich.panel import Panel
    import time

    steps = [
        ("mentor init --name wang-laoshi --template product",
         "初始化项目目录结构"),
        ("mentor collect --source markdown --input ./mentor-docs/ --persona wang-laoshi",
         "从 Markdown 文件采集导师语料"),
        ("mentor collect --source feishu --name '王老师' --persona wang-laoshi",
         "从飞书采集对话记录"),
        ("mentor analyze --persona wang-laoshi --stats",
         "分析数据质量，确认采集够用"),
        ("mentor distill --persona wang-laoshi",
         "执行 7 层深度蒸馏（需要 LLM API Key）"),
        ("mentor generate --persona wang-laoshi --format all",
         "生成 4 种平台格式的 Skill 文件"),
        ("mentor test --persona wang-laoshi",
         "与蒸馏后的导师 Persona 对话验证效果"),
    ]

    console.print(Panel(
        "[bold]完整使用流程演示[/bold]（dry-run，不执行真实命令）",
        border_style="cyan",
    ))

    for i, (cmd, desc) in enumerate(steps, 1):
        time.sleep(0.3)
        console.print(f"\n[dim]Step {i}[/dim]  [cyan]{cmd}[/cyan]")
        console.print(f"        [dim]→ {desc}[/dim]")

    console.print(Panel(
        "完整流程约需 10-30 分钟（取决于数据量和 LLM 速度）。\n\n"
        "准备好后，从第一步开始：\n"
        "[cyan]mentor init --name 你的导师名 --template product[/cyan]",
        title="下一步",
        border_style="green",
    ))


@app.command()
def compare(
    persona_a: str = typer.Option(..., "--persona-a", "-a", help="第一个 Persona ID"),
    persona_b: str = typer.Option(..., "--persona-b", "-b", help="第二个 Persona ID"),
):
    """对比两个 Persona 的差异（逐层展示关键字段变化）"""
    import json as _json
    from rich.panel import Panel

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)

    def _load_persona_data(persona_id: str) -> dict:
        p_file = persona_root / persona_id / "persona.json"
        ck_file = persona_root / persona_id / "checkpoint.json"
        src = p_file if p_file.exists() else ck_file
        if not src.exists():
            console.print(f"[red]错误：未找到 Persona [{persona_id}]，请先运行蒸馏。[/red]")
            raise typer.Exit(1)
        with open(src, encoding="utf-8") as f:
            return _json.load(f)

    data_a = _load_persona_data(persona_a)
    data_b = _load_persona_data(persona_b)

    layers_a = data_a.get("layers", {})
    layers_b = data_b.get("layers", {})

    # 对比元数据
    console.rule(f"[bold blue]Persona 对比：{persona_a}  vs  {persona_b}[/bold blue]")
    meta_table = Table(show_header=True, header_style="bold cyan", box=None)
    meta_table.add_column("字段", width=16)
    meta_table.add_column(persona_a, width=28)
    meta_table.add_column(persona_b, width=28)
    meta_table.add_row("完成层数", f"{len(layers_a)}/7", f"{len(layers_b)}/7")
    meta_table.add_row("蒸馏模型", data_a.get("distilled_by", "-"), data_b.get("distilled_by", "-"))
    console.print(meta_table)
    console.print()

    LAYER_LABELS = {
        "1": ("L1 基础身份", ["name", "role", "personality", "catchphrases"]),
        "2": ("L2 知识专业", ["domains", "key_insights", "expertise_depth"]),
        "3": ("L3 思维框架", ["problem_solving", "decision_framework", "question_style"]),
        "4": ("L4 沟通风格", ["tone", "structure", "emoji_usage"]),
        "5": ("L5 情感表达", ["empathy_style", "praise_style", "frustration_signals"]),
        "6": ("L6 指导关系", ["mentoring_style", "autonomy_grant", "feedback_cadence"]),
        "7": ("L7 学徒记忆", ["active_projects", "feedback_history", "growth_notes"]),
    }

    for layer_id, (label, fields) in LAYER_LABELS.items():
        la = layers_a.get(layer_id, {})
        lb = layers_b.get(layer_id, {})

        if not la and not lb:
            continue

        changed = False
        rows = []
        for field in fields:
            va = la.get(field, "(未蒸馏)")
            vb = lb.get(field, "(未蒸馏)")
            if isinstance(va, _list_type):
                va = ", ".join(str(x) for x in va) if va else "(空)"
            if isinstance(vb, _list_type):
                vb = ", ".join(str(x) for x in vb) if vb else "(空)"
            va_str = str(va)[:60] if va else "-"
            vb_str = str(vb)[:60] if vb else "-"
            is_diff = va_str != vb_str
            if is_diff:
                changed = True
            rows.append((field, va_str, vb_str, is_diff))

        panel_style = "yellow" if changed else "dim"
        diff_mark = " [yellow]△[/yellow]" if changed else " [green]≡[/green]"

        layer_table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        layer_table.add_column("字段", style="dim", width=22)
        layer_table.add_column(persona_a, width=32)
        layer_table.add_column(persona_b, width=32)

        for field, va_str, vb_str, is_diff in rows:
            if is_diff:
                layer_table.add_row(
                    f"[bold]{field}[/bold]",
                    f"[yellow]{va_str}[/yellow]",
                    f"[green]{vb_str}[/green]",
                )
            else:
                layer_table.add_row(field, f"[dim]{va_str}[/dim]", f"[dim]{vb_str}[/dim]")

        console.print(Panel(layer_table, title=f"{label}{diff_mark}", border_style=panel_style))

    console.print("\n[dim]△ = 存在差异    ≡ = 两者相同[/dim]")


@app.command()
def update(
    persona: str = typer.Option(..., help="目标导师 ID"),
    source: str = typer.Option(..., help="新数据来源: markdown / pdf / wechat / feishu / dingtalk"),
    input: Optional[str] = typer.Option(None, "--input", "-i", help="本地文件/目录路径"),
    layers: str = typer.Option("all", "--layers", help="重新蒸馏的层编号，逗号分隔（如 3,4,7）或 all"),
    interactive: bool = typer.Option(False, "--interactive", help="逐层交互确认"),
):
    """增量更新 Persona：补充新数据后只重新蒸馏指定层（无需全量重蒸馏）"""
    import json as _json

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)
    data_dir = Path(cfg.project.data_dir) / persona

    persona_file = persona_root / persona / "persona.json"
    if not persona_file.exists():
        console.print(f"[red]错误：未找到 Persona [{persona}]，请先运行完整蒸馏。[/red]")
        raise typer.Exit(1)

    # 加载已有 Persona
    from mentor_skill.generator.persona_files import PersonaFileGenerator
    existing_persona = PersonaFileGenerator().load(persona_root / persona)
    console.print(f"[bold blue]📂 已加载 Persona [{persona}]（{len(existing_persona.layers)}/7 层已蒸馏）[/bold blue]")

    # Step 1: 采集新数据
    console.print(f"\n[bold]Step 1：采集新数据（来源：{source}）[/bold]")
    new_messages = []

    if source in ("markdown", "pdf"):
        if not input:
            console.print("[red]错误：--source markdown/pdf 需要提供 --input 路径[/red]")
            raise typer.Exit(1)
        if source == "markdown":
            from mentor_skill.collectors.markdown import MarkdownCollector
            new_messages = MarkdownCollector().collect(input_path=input, mentor_name=persona)
        else:
            from mentor_skill.collectors.pdf import PDFCollector
            new_messages = PDFCollector().collect(input_path=input, mentor_name=persona)
    elif source == "wechat":
        if not input:
            console.print("[red]错误：--source wechat 需要提供 --input CSV 路径[/red]")
            raise typer.Exit(1)
        from mentor_skill.collectors.wechat import WechatCollector
        new_messages = WechatCollector().collect(input_file=input, mentor_name=persona)
    elif source == "feishu":
        from mentor_skill.collectors.feishu import FeishuCollector
        new_messages = FeishuCollector().collect(mentor_name=persona)
    elif source == "dingtalk":
        from mentor_skill.collectors.dingtalk import DingtalkCollector
        new_messages = DingtalkCollector().collect(mentor_name=persona)
    else:
        console.print(f"[red]不支持的数据源：{source}[/red]")
        raise typer.Exit(1)

    if not new_messages:
        console.print("[yellow]⚠ 未采集到新数据，退出。[/yellow]")
        raise typer.Exit(0)

    console.print(f"  [green]✓ 采集到 {len(new_messages)} 条新消息[/green]")

    # 保存新数据（追加到现有数据目录）
    data_dir.mkdir(parents=True, exist_ok=True)
    new_data_file = data_dir / f"update_{source}.json"
    with open(new_data_file, "w", encoding="utf-8") as f:
        _json.dump(
            [{"content": m.content, "sender": m.sender, "timestamp": m.timestamp.isoformat(),
              "is_mentor": m.is_mentor, "source": m.source} for m in new_messages],
            f, ensure_ascii=False, indent=2,
        )
    console.print(f"  [dim]新数据已保存：{new_data_file}[/dim]")

    # Step 2: 确定需要重新蒸馏的层
    if layers == "all":
        layer_ids = list(range(1, 8))
    else:
        try:
            layer_ids = [int(x.strip()) for x in layers.split(",") if x.strip()]
        except ValueError:
            console.print("[red]--layers 格式错误，应为逗号分隔数字（如 3,4,7）或 all[/red]")
            raise typer.Exit(1)

    console.print(f"\n[bold]Step 2：重新蒸馏层 {layer_ids}[/bold]")

    if not cfg.llm.api_key:
        console.print("[red]错误：未配置 LLM API Key，请先运行 mentor config --set llm.api_key YOUR_KEY[/red]")
        raise typer.Exit(1)

    # 重置指定层，允许重新蒸馏
    from mentor_skill.distiller.engine import DistillationEngine
    checkpoint_dir = persona_root / persona

    # 清除需要重蒸馏的层（这样 engine 会重新处理它们）
    for lid in layer_ids:
        existing_persona.layers.pop(str(lid), None)

    PersonaFileGenerator().save(existing_persona, persona_root / persona, filename="checkpoint.json")
    console.print(f"  [dim]已重置层 {layer_ids}，启动增量蒸馏...[/dim]")

    # 加载所有数据（新 + 旧）
    all_messages = []
    for data_file in sorted(data_dir.glob("*.json")):
        try:
            with open(data_file, encoding="utf-8") as f:
                records = _json.load(f)
            from mentor_skill.models.raw_message import RawMessage
            from datetime import datetime, timezone
            for r in records:
                ts_str = r.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                except Exception:
                    ts = datetime.now(timezone.utc)
                all_messages.append(RawMessage(
                    source=r.get("source", source),
                    timestamp=ts,
                    sender=r.get("sender", ""),
                    content=r.get("content", ""),
                    is_mentor=r.get("is_mentor", False),
                ))
        except Exception:
            continue

    if not all_messages:
        all_messages = new_messages

    engine = DistillationEngine(checkpoint_dir=checkpoint_dir, interactive=interactive)
    updated_persona = engine.run(
        persona=existing_persona,
        data=all_messages,
        resume=True,
    )

    PersonaFileGenerator().save(updated_persona, persona_root / persona)
    if (persona_root / persona / "checkpoint.json").exists():
        (persona_root / persona / "checkpoint.json").unlink()

    console.print(f"\n[bold green]✅ Persona [{persona}] 增量更新完成（{len(updated_persona.layers)}/7 层）[/bold green]")
    console.print(f"[dim]运行 mentor generate --persona {persona} --format all 重新生成 Skill 文件[/dim]")


@app.command()
def doctor(
    check_llm: bool = typer.Option(False, "--check-llm", help="实际发送测试请求验证 LLM 连通性（需要 API Key）"),
):
    """诊断配置、数据和环境问题，给出修复建议"""
    from rich.panel import Panel as _Panel
    import json as _json

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)
    data_root = Path(cfg.project.data_dir)

    checks: list[tuple[str, bool, str]] = []  # (名称, 通过, 建议)

    # ── 1. 配置检查 ──────────────────────────────────────────────────
    checks.append((
        "配置文件",
        True,
        "OK（使用默认配置或已有 config.yaml）",
    ))

    api_key_set = bool(cfg.llm.api_key)
    checks.append((
        "LLM API Key",
        api_key_set,
        "已设置" if api_key_set else
        "未设置 → 运行：mentor config --preset zhipu  然后 mentor config --set llm.api_key YOUR_KEY",
    ))

    checks.append((
        "LLM 模型",
        bool(cfg.llm.model),
        f"{cfg.llm.model}" if cfg.llm.model else "未设置 → 运行：mentor config --preset zhipu",
    ))

    api_base_ok = cfg.llm.api_base or cfg.llm.model in ("gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku-20240307")
    checks.append((
        "LLM API Base",
        bool(api_base_ok),
        f"{cfg.llm.api_base}" if cfg.llm.api_base else
        "(未设置，OpenAI/Anthropic 官方模型无需 api_base)" if api_base_ok else
        "未设置 → 运行：mentor config --preset zhipu（会自动设置 api_base）",
    ))

    # ── 2. 数据目录检查 ──────────────────────────────────────────────
    data_root = data_root.resolve()
    data_exists = data_root.exists()
    checks.append((
        "数据目录",
        data_exists,
        str(data_root) if data_exists else
        f"不存在 → 运行：mentor init --name 你的导师名  或  mkdir -p {data_root}",
    ))

    if data_exists:
        raw_files = list(data_root.glob("**/*_raw.json"))
        checks.append((
            "原始数据",
            bool(raw_files),
            f"找到 {len(raw_files)} 个 *_raw.json 文件" if raw_files else
            "无数据文件 → 运行：mentor collect --source markdown --input 你的文档目录 --persona 导师名",
        ))

    # ── 3. Persona 目录检查 ──────────────────────────────────────────
    persona_exists = persona_root.exists()
    checks.append((
        "Persona 目录",
        persona_exists,
        str(persona_root) if persona_exists else
        "不存在 → 运行：mentor init --name 你的导师名",
    ))

    if persona_exists:
        persona_dirs = [d for d in persona_root.iterdir() if d.is_dir()] if persona_root.exists() else []
        checks.append((
            "已有 Persona",
            bool(persona_dirs),
            f"找到 {len(persona_dirs)} 个 Persona（{', '.join(d.name for d in persona_dirs[:3])}）" if persona_dirs else
            "暂无 Persona → 运行：mentor init --name 你的导师名",
        ))

        complete_personas = []
        for d in persona_dirs:
            p_file = d / "persona.json"
            if p_file.exists():
                try:
                    data_p = _json.loads(p_file.read_text(encoding="utf-8"))
                    if len(data_p.get("layers", {})) == 7:
                        complete_personas.append(d.name)
                except Exception:
                    pass
        checks.append((
            "已完成蒸馏 Persona",
            bool(complete_personas),
            f"7层蒸馏完成：{', '.join(complete_personas)}" if complete_personas else
            "暂无完成 7 层蒸馏的 Persona → 运行：mentor distill --persona 导师名",
        ))

    # ── 4. 依赖检查 ──────────────────────────────────────────────────
    try:
        import litellm  # noqa: F401
        checks.append(("litellm 依赖", True, "已安装"))
    except ImportError:
        checks.append(("litellm 依赖", False, "未安装 → 运行：pip install litellm"))

    try:
        import playwright  # noqa: F401
        checks.append(("playwright 依赖", True, "已安装（钉钉采集可用）"))
    except ImportError:
        checks.append(("playwright 依赖", True, "未安装（只影响钉钉消息采集，其他功能正常）"))

    # ── 5. LLM 连通性测试（可选）────────────────────────────────────
    if check_llm:
        if not cfg.llm.api_key:
            checks.append(("LLM 连通性", False, "跳过（未设置 API Key）"))
        else:
            with console.status("[bold green]测试 LLM 连通性...[/bold green]"):
                try:
                    import litellm
                    test_kwargs: dict = {
                        "model": cfg.llm.model,
                        "messages": [{"role": "user", "content": "Hi, reply with just 'OK'"}],
                        "max_tokens": 10,
                        "timeout": 15,
                    }
                    if cfg.llm.api_base:
                        test_kwargs["api_base"] = cfg.llm.api_base
                    if cfg.llm.api_key:
                        test_kwargs["api_key"] = cfg.llm.api_key
                    resp = litellm.completion(**test_kwargs)
                    reply = resp.choices[0].message.content or ""
                    checks.append(("LLM 连通性", True, f"成功（响应：'{reply.strip()[:30]}'）"))
                except Exception as e:
                    checks.append(("LLM 连通性", False, f"连接失败：{str(e)[:80]}  →  检查 api_key / api_base / 网络"))

    # ── 渲染结果 ─────────────────────────────────────────────────────
    console.rule("[bold blue]🩺 mentor doctor 诊断报告[/bold blue]")
    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    for name, ok, msg in checks:
        icon = "[bold green]✅[/bold green]" if ok else "[bold red]❌[/bold red]"
        style = "dim" if ok else "white"
        console.print(f"  {icon}  [cyan]{name:<18}[/cyan]  [{style}]{msg}[/{style}]")

    console.print()
    if passed == total:
        console.print(_Panel(
            "所有检查通过！\n\n"
            "如果是首次使用，下一步：\n"
            "  1. mentor init --name 你的导师名\n"
            "  2. mentor collect --source markdown --input ./docs/ --persona 导师名\n"
            "  3. mentor distill --persona 导师名",
            title="[bold green]✅ 环境就绪[/bold green]",
            border_style="green",
        ))
    else:
        failed = [(n, m) for n, ok, m in checks if not ok]
        fix_list = "\n".join(f"  • {n}：{m}" for n, m in failed[:3])
        console.print(_Panel(
            f"发现 {total - passed} 个问题，建议先修复以下项：\n\n{fix_list}",
            title=f"[bold yellow]⚠ {total - passed}/{total} 项需要修复[/bold yellow]",
            border_style="yellow",
        ))


@app.command("export")
def export_persona(
    persona: str = typer.Option(..., help="要导出的 Persona ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径（默认 ./<persona>.mentor.zip）"),
):
    """将 Persona 打包成 .mentor.zip，便于迁移和分享"""
    import zipfile

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)
    persona_dir = persona_root / persona

    if not persona_dir.exists():
        console.print(f"[red]错误：未找到 Persona [{persona}]，请先运行蒸馏。[/red]")
        raise typer.Exit(1)

    output_path = Path(output) if output else Path(f"{persona}.mentor.zip")

    exported_files = []
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(persona_dir.iterdir()):
            if f.is_file():
                arcname = f"persona/{persona}/{f.name}"
                zf.write(f, arcname)
                exported_files.append(f.name)

    size_kb = output_path.stat().st_size / 1024
    console.print(f"[bold green]✅ 已导出 Persona [{persona}] → {output_path}[/bold green]")
    console.print(f"[dim]包含文件：{', '.join(exported_files)}  |  大小：{size_kb:.1f} KB[/dim]")
    console.print("\n[dim]分享给他人后，对方可运行：[/dim]")
    console.print(f"  [cyan]mentor import --file {output_path.name}[/cyan]")


@app.command("import")
def import_persona(
    file: str = typer.Argument(..., help=".mentor.zip 文件路径"),
    overwrite: bool = typer.Option(False, "--overwrite", help="如果 Persona 已存在，强制覆盖"),
):
    """从 .mentor.zip 文件导入 Persona"""
    import zipfile

    zip_path = Path(file)
    if not zip_path.exists():
        console.print(f"[red]错误：文件不存在：{zip_path}[/red]")
        raise typer.Exit(1)
    if not zipfile.is_zipfile(zip_path):
        console.print(f"[red]错误：{zip_path} 不是有效的 zip 文件[/red]")
        raise typer.Exit(1)

    cfg = get_config()
    persona_root = Path(cfg.project.persona_dir)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        # 从 zip 内路径提取 persona id
        persona_ids = {n.split("/")[1] for n in names if n.startswith("persona/") and n.count("/") >= 2}
        if not persona_ids:
            console.print("[red]错误：zip 文件格式不正确，未找到 persona/ 目录。[/red]")
            raise typer.Exit(1)

        for persona_id in sorted(persona_ids):
            target_dir = persona_root / persona_id
            if target_dir.exists() and not overwrite:
                console.print(f"[yellow]⚠ Persona [{persona_id}] 已存在，使用 --overwrite 强制覆盖。[/yellow]")
                continue

            target_dir.mkdir(parents=True, exist_ok=True)
            imported = []
            for member in names:
                prefix = f"persona/{persona_id}/"
                if member.startswith(prefix) and not member.endswith("/"):
                    filename = member[len(prefix):]
                    data = zf.read(member)
                    (target_dir / filename).write_bytes(data)
                    imported.append(filename)

            console.print(f"[bold green]✅ 已导入 Persona [{persona_id}][/bold green]")
            console.print(f"  [dim]路径[/dim] [cyan]{target_dir}[/cyan]")
            console.print(f"[dim]文件：{', '.join(imported)}[/dim]")

    console.print("\n[dim]运行 mentor list 查看所有已导入的 Persona[/dim]")


@app.callback(invoke_without_command=True)
def version_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", is_eager=True, help="显示版本号"),
):
    """导师.SKILL (mentor-skill) — 把你的导师蒸馏成 AI Skill。"""
    if version:
        from mentor_skill import __version__
        console.print(f"mentor-skill v[bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
