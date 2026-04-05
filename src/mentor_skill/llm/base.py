"""
LLM 调用抽象层 — litellm 封装

支持：智谱 GLM / DeepSeek / Qwen / MiniMax / OpenAI / Anthropic / Ollama 等所有 OpenAI 兼容 API
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class LLMConfig:
    model: str = "glm-4-flash"
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 120


class LLMClient:
    """统一的 LLM 调用客户端（基于 litellm）"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._check_litellm()

    def _check_litellm(self):
        try:
            import litellm  # noqa: F401
        except ImportError:
            console.print("[red]错误：请先安装 litellm：pip install litellm[/red]")
            raise

    def call(
        self,
        prompt: str,
        system: str | None = None,
        response_format: str = "json",
        max_retries: int = 3,
    ) -> str:
        """
        调用 LLM。

        Args:
            prompt: 用户消息内容
            system: 系统提示词（可选）
            response_format: "json" 要求输出 JSON，"text" 自由输出
            max_retries: 最大重试次数

        Returns:
            LLM 返回的文本内容
        """
        import litellm

        # 构建消息列表
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "timeout": self.config.timeout,
        }

        # api_base 和 api_key
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key

        # JSON 模式（部分模型不支持，故做降级处理）
        if response_format == "json":
            # 对支持的模型启用 JSON mode，否则在 prompt 中强调
            supported_json_mode = not self._is_third_party_model()
            if supported_json_mode:
                kwargs["response_format"] = {"type": "json_object"}

        # 带重试的调用
        last_err = None
        for attempt in range(max_retries):
            try:
                response = litellm.completion(**kwargs)
                content = response.choices[0].message.content
                return content or ""
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    console.print(f"[yellow]LLM 调用失败（{e}），{wait}s 后重试...[/yellow]")
                    time.sleep(wait)

        raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次）：{last_err}") from last_err

    def _is_third_party_model(self) -> bool:
        """判断是否为第三方（非 OpenAI）模型，以决定是否启用 JSON mode"""
        model = self.config.model.lower()
        third_party_prefixes = ("glm-", "deepseek-", "qwen-", "abab", "moonshot", "yi-")
        return any(model.startswith(p) for p in third_party_prefixes)

    def call_json(
        self,
        prompt: str,
        system: str | None = None,
        max_retries: int = 3,
    ) -> dict:
        """调用 LLM 并解析 JSON 响应"""
        # 对第三方模型在 prompt 末尾追加 JSON 强调
        if self._is_third_party_model():
            prompt = prompt + "\n\n请严格输出 JSON 格式，不要输出任何其他内容。"

        raw = self.call(prompt, system=system, response_format="json", max_retries=max_retries)

        # 尝试解析 JSON
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 尝试从代码块中提取 JSON
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            # 最后尝试找第一个 { } 块
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"LLM 返回内容无法解析为 JSON：\n{raw[:500]}")

    @classmethod
    def from_app_config(cls) -> "LLMClient":
        """从全局配置创建 LLMClient"""
        from mentor_skill.config import get_config
        cfg = get_config()
        llm_cfg = LLMConfig(
            model=cfg.llm.model,
            api_base=cfg.llm.api_base or None,
            api_key=cfg.llm.api_key or None,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            timeout=cfg.llm.timeout,
        )
        return cls(llm_cfg)
