"""
DingtalkCollector — 钉钉自动化采集器

由于钉钉 API 不提供历史消息拉取接口，
消息记录部分自动使用 Playwright 浏览器方案采集。
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from rich.console import Console

from mentor_skill.models.raw_message import RawMessage
from .base import BaseCollector

console = Console()


class DingtalkCollector(BaseCollector):
    """钉钉采集器 (API + 浏览器混用模式)"""

    SOURCE_NAME = "dingtalk"
    API_BASE = "https://api.dingtalk.com"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.app_key = self.config.get("app_key")
        self.app_secret = self.config.get("app_secret")
        self._token_cache = {}

    def get_access_token(self) -> str:
        now = time.time()
        if self._token_cache.get("token") and self._token_cache.get("expire", 0) > now + 60:
            return self._token_cache["token"]

        resp = requests.post(
            f"{self.API_BASE}/v1.0/oauth2/accessToken",
            json={"appKey": self.app_key, "appSecret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if "accessToken" not in data:
            raise ValueError(f"获取钉钉 token 失败：{data}")

        token = data["accessToken"]
        self._token_cache["token"] = token
        self._token_cache["expire"] = now + data.get("expireIn", 7200)
        return token

    def api_get(self, path: str, params: dict) -> dict:
        token = self.get_access_token()
        resp = requests.get(
            f"{self.API_BASE}{path}",
            params=params,
            headers={"x-acs-dingtalk-access-token": token},
            timeout=15,
        )
        return resp.json()

    def api_post(self, path: str, body: dict) -> dict:
        token = self.get_access_token()
        resp = requests.post(
            f"{self.API_BASE}{path}",
            json=body,
            headers={"x-acs-dingtalk-access-token": token},
            timeout=15,
        )
        return resp.json()

    def collect(
        self,
        mentor_name: str,
        msg_limit: int = 500,
        doc_limit: int = 20,
        headless: bool = False,
        **kwargs,
    ) -> list[RawMessage]:
        """
        采集钉钉聊天记录和文档

        Args:
            mentor_name: 导师姓名
            msg_limit: 消息条数上限
            doc_limit: 文档篇数上限
            headless: 是否使用无头模式（如果未登录建议设为 False）
        """
        if not self.app_key or not self.app_secret:
            console.print("[red]请在配置中提供钉钉 AppKey 和 AppSecret[/red]")
            return []

        # 1. 搜索用户（API）
        user = self._find_user(mentor_name)
        if not user:
            return []

        user_id = user.get("userId")
        console.print(f"  [green]✓[/green] 找到钉钉用户：{user.get('name')} ({user_id})")

        messages: list[RawMessage] = []

        # 2. 采集文档 (API)
        if doc_limit > 0:
            console.print("  [blue]📄 采集钉钉文档 (API)...[/blue]")
            doc_list = self._collect_docs_api(user_id, mentor_name, doc_limit)
            messages.extend(doc_list)

        # 3. 采集聊天记录 (浏览器自动化)
        if msg_limit > 0:
            console.print("  [blue]📨 采集消息记录 (浏览器方案)...[/blue]")
            browser_msgs = self._collect_messages_browser(mentor_name, msg_limit, headless)
            messages.extend(browser_msgs)
            console.print(f"    获取 {len(browser_msgs)} 条聊天记录")

        return messages

    def _find_user(self, name: str) -> Optional[dict]:
        data = self.api_post("/v1.0/contact/users/search", {"searchText": name, "offset": 0, "size": 10})
        users = data.get("list", []) or data.get("result", {}).get("list", [])
        if not users:
            console.print(f"[yellow]未能找到钉钉用户 {name}[/yellow]")
            return None
        return users[0]

    def _collect_docs_api(self, user_id: str, name: str, limit: int) -> list[RawMessage]:
        """采集钉钉文档/知识库内容"""
        # 钉钉文档搜索 API (v1.0)
        data = self.api_post(
            "/v1.0/doc/search",
            {"keyword": name, "size": limit, "offset": 0},
        )
        docs = (
            data.get("docList", [])
            or data.get("result", {}).get("docList", [])
            or data.get("data", {}).get("list", [])
        )

        msgs: list[RawMessage] = []
        for item in docs:
            title = item.get("title", "Untitled")
            doc_key = item.get("docKey") or item.get("spaceId", "")
            share_url = item.get("shareUrl", "")

            content = self._fetch_doc_content(doc_key, title)

            msgs.append(RawMessage(
                source=self.SOURCE_NAME,
                timestamp=datetime.now(timezone.utc),
                sender=name,
                content=content,
                is_mentor=True,
                context={"type": "doc", "title": title, "url": share_url},
            ))
            console.print(f"    [dim]📄 已采集文档：{title}（{len(content)} 字）[/dim]")

        return msgs

    def _fetch_doc_content(self, doc_key: str, title: str) -> str:
        """拉取钉钉文档正文（知识库 API）"""
        if not doc_key:
            return f"# {title}\n（无法获取正文：缺少 doc_key）"

        try:
            # 钉钉知识库文档内容 API
            data = self.api_get(
                f"/v1.0/doc/workspaces/docs/{doc_key}/content",
                params={},
            )
            if data.get("success") or data.get("result"):
                raw_content = data.get("result", {}).get("content") or data.get("content", "")
                return f"# {title}\n\n{self._parse_doc_content(raw_content)}"

            # 备用：钉钉文档旧版 API
            data2 = self.api_post(
                "/v1.0/doc/getContentByDocKey",
                {"docKey": doc_key},
            )
            if data2.get("result"):
                return f"# {title}\n\n{data2['result'].get('content', '')}"

        except Exception as e:
            console.print(f"    [yellow]⚠ 文档 [{title}] 正文获取失败：{e}[/yellow]")

        return f"# {title}\n（正文获取失败，仅保留标题）"

    def _parse_doc_content(self, raw: str) -> str:
        """解析钉钉文档内容（可能是 HTML 或纯文本）"""
        if not raw:
            return ""
        # 简单去除 HTML 标签
        import re
        text = re.sub(r"<[^>]+>", "", raw)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _collect_messages_browser(self, name: str, limit: int, headless: bool) -> list[RawMessage]:
        """浏览器自动化采集钉钉聊天记录"""
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            console.print("[red]请安装 playwright：pip install playwright && playwright install chromium[/red]")
            return []

        msgs: list[RawMessage] = []

        with sync_playwright() as p:
            launch_kwargs: dict = {"headless": headless}

            # 尝试复用本地 Chrome profile（保持登录状态）
            chrome_profile = self.config.get("chrome_profile")
            if chrome_profile:
                launch_kwargs["args"] = [f"--user-data-dir={chrome_profile}"]

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                console.print("  [blue]正在打开钉钉网页版...[/blue]")
                page.goto("https://im.dingtalk.com", timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)

                # 检查登录状态
                if "login" in page.url.lower() or page.query_selector(".login-container"):
                    if headless:
                        console.print("[yellow]未登录，无头模式下无法完成钉钉认证，跳过消息采集。[/yellow]")
                        console.print("[dim]建议：先运行 mentor collect --source dingtalk --name 姓名 (非无头模式) 完成登录[/dim]")
                        browser.close()
                        return []
                    else:
                        console.print("[yellow]请在浏览器中扫码登录，然后按 Enter 继续...[/yellow]")
                        input()

                # 搜索联系人
                console.print(f"  [blue]搜索联系人：{name}...[/blue]")
                search_btn = page.query_selector('[data-testid="search-btn"], .search-btn, .topbar-search')
                if search_btn:
                    search_btn.click()
                    page.keyboard.type(name)
                    page.wait_for_timeout(2000)

                    # 找到第一个匹配的联系人
                    result_item = page.query_selector('.search-result-item, .contact-item')
                    if result_item:
                        result_item.click()
                        page.wait_for_timeout(2000)
                    else:
                        console.print(f"[yellow]未找到联系人 {name} 的搜索结果[/yellow]")
                        browser.close()
                        return []
                else:
                    console.print("[yellow]未找到搜索入口，跳过消息采集[/yellow]")
                    browser.close()
                    return []

                # 滚动加载消息历史
                msgs = self._extract_messages_from_page(page, name, limit)
                console.print(f"    提取到 {len(msgs)} 条消息")

            except PWTimeout:
                console.print("[yellow]钉钉页面加载超时，跳过消息采集[/yellow]")
            except Exception as e:
                console.print(f"[yellow]浏览器采集出错：{e}[/yellow]")
            finally:
                browser.close()

        return msgs

    def _extract_messages_from_page(self, page: Any, mentor_name: str, limit: int) -> list[RawMessage]:
        """从已打开的聊天页面提取消息"""
        msgs: list[RawMessage] = []
        last_count = 0
        scroll_attempts = 0
        max_scroll = 20

        while len(msgs) < limit and scroll_attempts < max_scroll:
            # 滚动到顶部加载更早的消息
            page.evaluate("document.querySelector('.message-list, .chat-content')?.scrollTop = 0")
            page.wait_for_timeout(1500)

            # 提取消息 DOM
            message_elements = page.query_selector_all(
                '.message-item, .chat-message-item, [class*="message-item"]'
            )

            for elem in message_elements:
                try:
                    # 判断发送者
                    sender_elem = elem.query_selector('.sender-name, .nick-name, [class*="sender"]')
                    sender = sender_elem.inner_text().strip() if sender_elem else ""

                    # 消息内容
                    content_elem = elem.query_selector('.message-content, .text-content, [class*="content"]')
                    content = content_elem.inner_text().strip() if content_elem else ""

                    if not content or len(content) < 2:
                        continue

                    is_mentor = mentor_name in sender if sender else False

                    msgs.append(RawMessage(
                        source=self.SOURCE_NAME,
                        timestamp=datetime.now(timezone.utc),
                        sender=sender or ("王老师" if is_mentor else "学徒"),
                        content=content,
                        is_mentor=is_mentor,
                        context={"type": "im"},
                    ))

                except Exception:
                    continue

            # 去重（按内容）
            seen = set()
            unique_msgs = []
            for m in msgs:
                if m.content not in seen:
                    seen.add(m.content)
                    unique_msgs.append(m)
            msgs = unique_msgs

            if len(msgs) == last_count:
                break  # 没有新消息，停止滚动
            last_count = len(msgs)
            scroll_attempts += 1

        return msgs[:limit]

    def validate_input(self, **kwargs) -> bool:
        return bool(self.app_key and self.app_secret)
