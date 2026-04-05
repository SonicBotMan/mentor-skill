"""
MarkdownCollector — 采集 Markdown/Text 文件中的内容

适用场景：
  - 导师写的技术文档、设计文档
  - 导师的笔记、博客
  - 任何 .md / .txt 格式的文件
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from mentor_skill.models.raw_message import RawMessage
from .base import BaseCollector

console = Console()


class MarkdownCollector(BaseCollector):
    """
    Markdown/Text 文件采集器

    会把每个文件作为一条 RawMessage，sender 根据文件 YAML frontmatter 推断。
    如果有多个文件，每个文件独立返回一条消息。
    """

    SOURCE_NAME = "markdown"

    def collect(
        self,
        input_path: str | Path,
        mentor_name: str = "",
        recursive: bool = True,
        **kwargs,
    ) -> list[RawMessage]:
        """
        采集指定路径下的 Markdown/Text 文件。

        Args:
            input_path: 文件路径或目录路径
            mentor_name: 导师名称（用于标记 is_mentor=True）
            recursive: 是否递归搜索子目录

        Returns:
            RawMessage 列表（每个文件一条）
        """
        path = Path(input_path)
        if not path.exists():
            console.print(f"[red]路径不存在：{path}[/red]")
            return []

        files: list[Path] = []
        if path.is_file():
            files = [path]
        elif path.is_dir():
            for ext in ("*.md", "*.txt", "*.markdown"):
                files.extend(path.glob(f"**/{ext}" if recursive else ext))
            files = sorted(set(files))

        messages = []
        for f in files:
            msg = self._parse_file(f, mentor_name)
            if msg:
                messages.append(msg)
                console.print(f"  [green]✓[/green] {f.name} ({msg.word_count} 字)")

        console.print(f"[bold]Markdown 采集完成：共 {len(messages)} 个文件[/bold]")
        return messages

    def _parse_file(self, path: Path, mentor_name: str) -> RawMessage | None:
        """解析单个文件"""
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                raw = path.read_text(encoding="gbk")
            except Exception:
                console.print(f"  [yellow]⚠ 无法读取文件：{path.name}[/yellow]")
                return None

        if not raw.strip():
            return None

        # 解析 YAML frontmatter
        metadata: dict = {"filename": path.name, "path": str(path)}
        content = raw

        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if frontmatter_match:
            try:
                import yaml
                fm = yaml.safe_load(frontmatter_match.group(1)) or {}
                if isinstance(fm, dict):
                    metadata.update(fm)
            except Exception:
                pass
            content = raw[frontmatter_match.end():]

        content = content.strip()
        if not content:
            return None

        # 推断时间戳
        timestamp = datetime.now(timezone.utc)
        for key in ("date", "created", "updated", "timestamp"):
            if key in metadata:
                try:
                    val = metadata[key]
                    if isinstance(val, datetime):
                        timestamp = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
                    elif isinstance(val, str):
                        from dateutil.parser import parse as parse_date
                        timestamp = parse_date(val)
                    break
                except Exception:
                    pass

        # 推断 sender
        sender = metadata.get("author", metadata.get("sender", mentor_name or "导师"))

        # 推断是否为导师
        is_mentor = True  # Markdown 文件默认认为是导师写的
        if mentor_name and sender and mentor_name not in sender and sender not in mentor_name:
            is_mentor = False

        return RawMessage(
            source=self.SOURCE_NAME,
            timestamp=timestamp,
            sender=sender,
            content=content,
            is_mentor=is_mentor,
            context={"filename": path.name},
            metadata=metadata,
        )

    def validate_input(self, input_path: str | Path, **kwargs) -> bool:
        path = Path(input_path)
        if not path.exists():
            console.print(f"[red]路径不存在：{path}[/red]")
            return False
        if path.is_file() and path.suffix.lower() not in (".md", ".txt", ".markdown"):
            console.print(f"[yellow]文件格式不支持（需要 .md/.txt）：{path}[/yellow]")
            return False
        return True
