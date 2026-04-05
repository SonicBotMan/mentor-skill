"""采集器包"""
from .base import BaseCollector
from .markdown import MarkdownCollector
from .pdf import PDFCollector
from .wechat import WechatCollector
from .feishu import FeishuCollector
from .dingtalk import DingtalkCollector

__all__ = [
    "BaseCollector",
    "MarkdownCollector",
    "PDFCollector",
    "WechatCollector",
    "FeishuCollector",
    "DingtalkCollector",
]
