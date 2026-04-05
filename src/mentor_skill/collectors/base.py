"""
BaseCollector — 所有采集器的抽象基类
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from mentor_skill.models.raw_message import RawMessage


class BaseCollector(ABC):
    """所有采集器的抽象基类"""

    SOURCE_NAME: str = "unknown"  # 子类覆盖，如 "markdown", "feishu"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def collect(self, **kwargs) -> list[RawMessage]:
        """
        采集数据，返回 RawMessage 列表。

        子类必须实现。每条消息应正确设置：
          - source: 数据源名称
          - timestamp: 消息时间
          - sender: 发送者姓名
          - content: 纯文本内容
          - is_mentor: 是否为导师发送（如能判断）
        """
        ...

    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """校验输入参数是否合法"""
        ...

    def _make_source_tag(self) -> str:
        return self.SOURCE_NAME
