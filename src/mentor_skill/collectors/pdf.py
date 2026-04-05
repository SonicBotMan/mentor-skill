"""
PDFCollector — 采集 PDF 文件内容（使用 pdfplumber）
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from mentor_skill.models.raw_message import RawMessage
from .base import BaseCollector

console = Console()


class PDFCollector(BaseCollector):
    """PDF 文件采集器"""

    SOURCE_NAME = "pdf"

    def collect(
        self,
        input_path: str | Path,
        mentor_name: str = "",
        recursive: bool = True,
        **kwargs,
    ) -> list[RawMessage]:
        try:
            import pdfplumber
        except ImportError:
            console.print("[red]请先安装 pdfplumber：pip install pdfplumber[/red]")
            return []

        path = Path(input_path)
        if not path.exists():
            console.print(f"[red]路径不存在：{path}[/red]")
            return []

        files: list[Path] = []
        if path.is_file():
            files = [path]
        elif path.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            files = sorted(path.glob(pattern))

        messages = []
        for f in files:
            msg = self._parse_pdf(f, mentor_name, pdfplumber)
            if msg:
                messages.append(msg)
                console.print(f"  [green]✓[/green] {f.name} ({msg.word_count} 字)")

        console.print(f"[bold]PDF 采集完成：共 {len(messages)} 个文件[/bold]")
        return messages

    def _parse_pdf(self, path: Path, mentor_name: str, pdfplumber) -> RawMessage | None:
        try:
            with pdfplumber.open(path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text.strip())
                    # 提取表格
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            row_text = " | ".join(str(c or "") for c in row)
                            if row_text.strip():
                                pages_text.append(row_text)

                content = "\n\n".join(pages_text).strip()
                if not content:
                    return None

                # 从 PDF 元数据获取信息
                meta = pdf.metadata or {}
                author = meta.get("Author", mentor_name or "导师")
                created_raw = meta.get("CreationDate", "")

                timestamp = datetime.now(timezone.utc)
                if created_raw:
                    try:
                        # PDF 日期格式: D:YYYYMMDDHHmmSS
                        date_str = created_raw.replace("D:", "")[:14]
                        timestamp = datetime(
                            int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]),
                            tzinfo=timezone.utc
                        )
                    except Exception:
                        pass

                return RawMessage(
                    source=self.SOURCE_NAME,
                    timestamp=timestamp,
                    sender=str(author),
                    content=content,
                    is_mentor=True,  # PDF 默认认为是导师的材料
                    context={"filename": path.name, "pages": len(pdf.pages)},
                    metadata=dict(meta),
                )
        except Exception as e:
            console.print(f"  [yellow]⚠ 解析 PDF 失败（{path.name}）：{e}[/yellow]")
            return None

    def validate_input(self, input_path: str | Path, **kwargs) -> bool:
        path = Path(input_path)
        if not path.exists():
            console.print(f"[red]路径不存在：{path}[/red]")
            return False
        return True
