"""
RawMessage — 所有采集器的统一输出格式

设计决策：用 dataclass（而非 Pydantic）是因为采集层是"脏数据"入口，
宽松的 dataclass 避免校验失败阻塞采集流程。
进入蒸馏层后再用 Pydantic 严格校验。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawMessage:
    """单条原始消息"""

    source: str              # "markdown" / "pdf" / "wechat" / "feishu" / "dingtalk"
    timestamp: datetime      # 消息时间
    sender: str              # 发送者名称
    content: str             # 纯文本内容
    is_mentor: bool = False  # 是否为导师发送（采集时或分析时标记）
    context: dict = field(default_factory=dict)       # 群名、话题等上下文
    metadata: dict = field(default_factory=dict)      # 原始元数据（保留）
    attachments: list[dict] = field(default_factory=list)  # 文件附件信息

    def __post_init__(self):
        # 确保 content 是字符串
        if not isinstance(self.content, str):
            self.content = str(self.content)
        self.content = self.content.strip()

    @property
    def word_count(self) -> int:
        """字符数（中文按字算）"""
        return len(self.content)

    @property
    def is_high_value(self) -> bool:
        """简单判断是否为高价值消息（详细判定在 analyzers/quality.py）"""
        return self.word_count > 50

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender,
            "content": self.content,
            "is_mentor": self.is_mentor,
            "context": self.context,
            "metadata": self.metadata,
        }
