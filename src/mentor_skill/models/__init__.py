"""数据模型包"""
from .raw_message import RawMessage
from .persona import (
    Layer1Identity,
    Layer2Knowledge,
    Layer3Thinking,
    Layer4Communication,
    Layer5Emotion,
    Layer6Mentorship,
    Layer7ApprenticeMemory,
    Persona,
)

__all__ = [
    "RawMessage",
    "Layer1Identity",
    "Layer2Knowledge",
    "Layer3Thinking",
    "Layer4Communication",
    "Layer5Emotion",
    "Layer6Mentorship",
    "Layer7ApprenticeMemory",
    "Persona",
]
