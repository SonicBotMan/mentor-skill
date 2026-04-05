"""
DataCleaner — 数据清洗管道

负责去重、过滤系统消息、规范化。
"""
from __future__ import annotations

import re
from typing import List

from mentor_skill.models.raw_message import RawMessage


class DataCleaner:
    """清洗管道：去重 → 过滤 → 规范化"""

    def __init__(self, min_length: int = 2):
        self.min_length = min_length
        # 系统消息特征
        self.system_patterns = [
            r"撤回了一条消息",
            r"离开了群聊",
            r"加入了群聊",
            r"通过扫描二维码加入",
            r"打了个招呼",
            r"拍了拍",
            r"修改了群名称",
            r"开启了入群验证",
        ]

    def clean(self, messages: List[RawMessage]) -> List[RawMessage]:
        """执行全套清洗流水线"""
        if not messages:
            return []

        cleaned = messages

        # 1. 过滤系统消息（微信/飞书/钉钉场景常用）
        cleaned = self._filter_system_messages(cleaned)

        # 2. 过滤长度过短的消息
        cleaned = [m for m in cleaned if len(m.content) >= self.min_length]

        # 3. 规范化空格和换行
        cleaned = self._normalize_content(cleaned)

        # 4. 去重 (通过内容和时间戳哈希)
        cleaned = self._deduplicate(cleaned)

        return cleaned

    def _filter_system_messages(self, messages: List[RawMessage]) -> List[RawMessage]:
        result = []
        for m in messages:
            is_system = False
            for p in self.system_patterns:
                if re.search(p, m.content):
                    is_system = True
                    break
            if not is_system:
                result.append(m)
        return result

    def _normalize_content(self, messages: List[RawMessage]) -> List[RawMessage]:
        for m in messages:
            # 连续换行转单换行
            m.content = re.sub(r"\n+", "\n", m.content)
            # 两端去空格
            m.content = m.content.strip()
        return messages

    def _deduplicate(self, messages: List[RawMessage]) -> List[RawMessage]:
        seen = set()
        result = []
        for m in messages:
            # 简单哈希：时间戳 + 内容的哈希
            h = hash((m.timestamp.isoformat(), m.content))
            if h not in seen:
                seen.add(h)
                result.append(m)
        return result
