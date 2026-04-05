"""
WechatCollector — 采集微信聊天记录

目前支持处理 WeChatMsg (https://github.com/LC044/WeChatMsg)
导出的 CSV 格式聊天记录。
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from mentor_skill.models.raw_message import RawMessage
from .base import BaseCollector

console = Console()


class WechatCollector(BaseCollector):
    """
    微信采集器 (CSV 解析版)
    """

    SOURCE_NAME = "wechat"

    def collect(
        self,
        input_file: str | Path,
        mentor_name: str,
        apprentice_name: str = "",
        **kwargs,
    ) -> list[RawMessage]:
        """
        解析导出的 CSV 聊天记录

        Args:
            input_file: CSV 文件路径
            mentor_name: 导师在微信中的昵称/备注
            apprentice_name: 学徒在微信中的昵称（可选，用于辅助判断）
        """
        path = Path(input_file)
        if not path.exists():
            console.print(f"[red]文件不存在：{path}[/red]")
            return []

        messages = []
        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                # 检查必要的列（WeChatMsg 的列名通常包含：Sender, Content, Time）
                # 注意：不同工具导出的列名可能不同，这里做一些模糊匹配

                for row in reader:
                    # 尝试匹配发送者、内容和时间
                    sender = self._get_val(row, ["Sender", "发送者", "昵称", "Name"])
                    content = self._get_val(row, ["Content", "内容", "消息内容", "Message"])
                    time_str = self._get_val(row, ["Time", "时间", "发送时间", "DateTime"])

                    if not sender or not content:
                        continue

                    # 过滤掉非文本内容（简单判断）
                    if content.startswith("[") and content.endswith("]") and len(content) < 20:
                        if any(tag in content for tag in ["图片", "表情", "语音", "文件", "视频", "位置", "红包"]):
                            continue

                    try:
                        # 尝试多种时间格式
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                            try:
                                timestamp = datetime.strptime(time_str, fmt).replace(tzinfo=timezone.utc)
                                break
                            except Exception:
                                continue
                        else:
                            timestamp = datetime.now(timezone.utc)
                    except Exception:
                        timestamp = datetime.now(timezone.utc)

                    is_mentor = mentor_name in sender or sender in mentor_name

                    messages.append(RawMessage(
                        source=self.SOURCE_NAME,
                        timestamp=timestamp,
                        sender=sender,
                        content=content,
                        is_mentor=is_mentor,
                        metadata=row
                    ))
        except Exception as e:
            console.print(f"[red]解析微信 CSV 失败：{e}[/red]")
            return []

        console.print(f"[bold]微信采集完成：共 {len(messages)} 条消息[/bold]")
        return messages

    def _get_val(self, row: dict, keys: list[str]) -> str:
        for k in keys:
            if k in row:
                return row[k]
            # 忽略大小写的匹配
            for rk in row.keys():
                if k.lower() == rk.lower():
                    return row[rk]
        return ""

    def validate_input(self, input_file: str | Path, **kwargs) -> bool:
        path = Path(input_file)
        if not path.exists() or path.suffix.lower() != ".csv":
            console.print(f"[red]请输入有效的微信导出 CSV 文件：{path}[/red]")
            return False
        return True
