"""
配置管理 — 加载和验证 config.yaml

支持多种 LLM 服务商（智谱/DeepSeek/Qwen/MiniMax/OpenAI）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# ── LLM 预设 ─────────────────────────────────────────────────────────────────
LLM_PRESETS: dict[str, dict] = {
    "zhipu": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-4-flash",
        "display_name": "智谱 GLM",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "display_name": "DeepSeek",
    },
    "qwen": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
        "display_name": "Qwen（阿里百炼）",
    },
    "minimax": {
        "api_base": "https://api.minimax.chat/v1",
        "default_model": "abab6.5s-chat",
        "display_name": "MiniMax",
    },
    "openai": {
        "api_base": None,
        "default_model": "gpt-4o-mini",
        "display_name": "OpenAI",
    },
}


class LLMSettings(BaseModel):
    model: str = "glm-4-flash"
    api_key: str = ""
    api_base: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 120

    def get_provider_name(self) -> str:
        """根据 api_base 推断服务商名称"""
        if not self.api_base:
            return "openai"
        for name, preset in LLM_PRESETS.items():
            if preset["api_base"] and preset["api_base"] in self.api_base:
                return name
        return "custom"


class FeishuSettings(BaseModel):
    app_id: str = ""
    app_secret: str = ""
    user_access_token: str = ""
    p2p_chat_id: str = ""


class DingtalkSettings(BaseModel):
    app_key: str = ""
    app_secret: str = ""
    chrome_profile: str | None = None


class CollectSettings(BaseModel):
    msg_limit: int = 1000
    doc_limit: int = 30


class AnalyzeSettings(BaseModel):
    min_message_length: int = 10
    high_value_min_length: int = 50
    context_window: int = 5
    gap_minutes: int = 30


class ProjectSettings(BaseModel):
    name: str = "my-mentor"
    template: str = "product"
    data_dir: str = ".mentor/data"
    output_dir: str = ".mentor/output"
    persona_dir: str = ".mentor/personas"


class AppConfig(BaseModel):
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    feishu: FeishuSettings = Field(default_factory=FeishuSettings)
    dingtalk: DingtalkSettings = Field(default_factory=DingtalkSettings)
    collect: CollectSettings = Field(default_factory=CollectSettings)
    analyze: AnalyzeSettings = Field(default_factory=AnalyzeSettings)


# ── 全局配置单例 ──────────────────────────────────────────────────────────────
_config: AppConfig | None = None
_config_path: Path | None = None

# per-persona 配置存储目录
PERSONA_CONFIG_DIR = Path.home() / ".mentor-skill" / "personas"
GLOBAL_CONFIG_DIR = Path.home() / ".mentor-skill"


def load_config(config_path: Path | None = None) -> AppConfig:
    """加载配置文件，优先级：参数路径 > 当前目录 config.yaml > 默认值"""
    global _config, _config_path

    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.extend([
        Path("config.yaml"),
        Path("config.yml"),
        GLOBAL_CONFIG_DIR / "config.yaml",
    ])

    raw: dict[str, Any] = {}
    for path in search_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            _config_path = path
            break

    _config = AppConfig(**raw)
    return _config


def get_config() -> AppConfig:
    """获取当前配置（懒加载）"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def save_config(cfg: AppConfig, path: Path | None = None) -> None:
    """保存配置到文件"""
    target = path or _config_path or Path("config.yaml")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        yaml.dump(cfg.model_dump(), f, allow_unicode=True, default_flow_style=False)


# ── Persona 配置（单个导师的 config）────────────────────────────────────────
def get_persona_dir(persona_name: str) -> Path:
    """获取 persona 存储目录"""
    cfg = get_config()
    base = Path(cfg.project.persona_dir)
    return base / persona_name


def load_feishu_config() -> dict:
    """从全局配置目录加载飞书配置（兼容 colleague-skill 格式）"""
    path = GLOBAL_CONFIG_DIR / "feishu_config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_feishu_config(config: dict) -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "feishu_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False)
    )


def load_dingtalk_config() -> dict:
    path = GLOBAL_CONFIG_DIR / "dingtalk_config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_dingtalk_config(config: dict) -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "dingtalk_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False)
    )
