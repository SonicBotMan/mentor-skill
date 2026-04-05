"""
FeishuCollector — 飞书自动化采集器

支持采集：
  1. 共同群聊中的历史消息（需要机器人权限）
  2. 私聊消息（需要 user_access_token）
  3. 文档和 Wiki 内容
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from rich.console import Console

from mentor_skill.models.raw_message import RawMessage
from .base import BaseCollector

console = Console()


class FeishuCollector(BaseCollector):
    """飞书采集器 (API 模式)"""

    SOURCE_NAME = "feishu"
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.app_id = self.config.get("app_id")
        self.app_secret = self.config.get("app_secret")
        self._token_cache = {}

    def get_tenant_token(self) -> str:
        now = time.time()
        if self._token_cache.get("token") and self._token_cache.get("expire", 0) > now + 60:
            return self._token_cache["token"]

        resp = requests.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取飞书 token 失败：{data}")

        token = data["tenant_access_token"]
        self._token_cache["token"] = token
        self._token_cache["expire"] = now + data.get("expire", 7200)
        return token

    def api_get(self, path: str, params: dict, use_user_token: bool = False) -> dict:
        if use_user_token and self.config.get("user_access_token"):
            token = self.config["user_access_token"]
        else:
            token = self.get_tenant_token()
        resp = requests.get(
            f"{self.BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return resp.json()

    def collect(
        self,
        mentor_name: str,
        msg_limit: int = 500,
        doc_limit: int = 20,
        **kwargs,
    ) -> list[RawMessage]:
        """
        全量采集飞书聊天和文档

        Args:
            mentor_name: 导师姓名（用于搜索用户）
            msg_limit: 消息条数上限
            doc_limit: 文档篇数上限
        """
        if not self.app_id or not self.app_secret:
            console.print("[red]请在配置中提供飞书 App ID 和 App Secret[/red]")
            return []

        # 1. 查找用户
        user = self._find_user(mentor_name)
        if not user:
            return []

        user_open_id = user.get("open_id") or user.get("user_id")
        console.print(f"  [green]✓[/green] 找到飞书用户：{user.get('name')} ({user_open_id})")

        messages: list[RawMessage] = []

        # 2. 采集私聊
        if self.config.get("user_access_token") and self.config.get("p2p_chat_id"):
            console.print("  [blue]📱 采集私聊消息...[/blue]")
            p2p_msgs = self._fetch_p2p_messages(self.config["p2p_chat_id"], user_open_id, msg_limit)
            messages.extend(p2p_msgs)
            console.print(f"    获取 {len(p2p_msgs)} 条私聊消息")

        # 3. 采集群聊
        remaining = msg_limit - len(messages)
        if remaining > 0:
            console.print("  [blue]👥 采集群聊消息...[/blue]")
            group_msgs = self._fetch_group_messages(user_open_id, remaining)
            messages.extend(group_msgs)
            console.print(f"    获取 {len(group_msgs)} 条群聊消息")

        # 4. 采集文档（文档会作为一条超级大的长消息存入）
        if doc_limit > 0:
            console.print("  [blue]📄 采集文档...[/blue]")
            doc_raw_list = self._collect_docs(user_open_id, mentor_name, doc_limit)
            messages.extend(doc_raw_list)

        return messages

    def _find_user(self, name: str) -> Optional[dict]:
        """多策略用户查找：名称模糊匹配 → 全员搜索 → 手动输入"""
        # 策略 1：遍历根部门及子部门
        user = self._search_in_department("0", name, max_depth=3)
        if user:
            return user

        # 策略 2：使用飞书用户搜索 API（如果有 user_access_token）
        if self.config.get("user_access_token"):
            resp = self.api_get(
                "/search/v1/user",
                {"query": name, "page_size": 10},
                use_user_token=True,
            )
            if resp.get("code") == 0:
                items = resp.get("data", {}).get("results", [])
                for item in items:
                    u = item.get("user", {})
                    if name in u.get("name", ""):
                        return u

        # 策略 3：提示用户手动输入 open_id
        console.print(f"[yellow]⚠ 未能自动找到用户 [{name}]。[/yellow]")
        console.print("[dim]你可以在飞书管理后台查看用户的 open_id[/dim]")
        try:
            manual_id = console.input(
                f"[bold]请手动输入 {name} 的 open_id（直接回车跳过）：[/bold]"
            ).strip()
        except EOFError:
            manual_id = ""
        if manual_id:
            return {"open_id": manual_id, "name": name}

        console.print(f"[red]无法找到用户 {name}，跳过飞书采集。[/red]")
        return None

    def _search_in_department(self, dept_id: str, name: str, max_depth: int = 2, _depth: int = 0) -> Optional[dict]:
        """递归遍历部门查找用户"""
        data = self.api_get(
            "/contact/v3/users/find_by_department",
            {"department_id": dept_id, "page_size": 100},
        )
        if data.get("code") == 0:
            for u in data.get("data", {}).get("items", []):
                if name in u.get("name", ""):
                    return u

        # 递归子部门
        if _depth < max_depth:
            dept_data = self.api_get(
                "/contact/v3/departments/children",
                {"department_id": dept_id, "page_size": 50},
            )
            if dept_data.get("code") == 0:
                for dept in dept_data.get("data", {}).get("items", []):
                    child_id = dept.get("department_id") or dept.get("open_department_id")
                    if child_id:
                        found = self._search_in_department(child_id, name, max_depth, _depth + 1)
                        if found:
                            return found
        return None

    def _fetch_p2p_messages(self, chat_id: str, user_open_id: str, limit: int) -> list[RawMessage]:
        msgs = []
        page_token = None
        while len(msgs) < limit:
            params = {"container_id_type": "chat", "container_id": chat_id, "page_size": 50, "sort_type": "ByCreateTimeDesc"}
            if page_token: params["page_token"] = page_token

            data = self.api_get("/im/v1/messages", params, use_user_token=True)
            if data.get("code") != 0: break

            items = data.get("data", {}).get("items", [])
            if not items: break

            for item in items:
                sender_id = item.get("sender", {}).get("id") or item.get("sender", {}).get("open_id")
                content_text = self._parse_content(item.get("body", {}).get("content", ""))
                if not content_text: continue

                ts = datetime.fromtimestamp(int(item.get("create_time", 0)) / 1000, tz=timezone.utc)
                msgs.append(RawMessage(
                    source=self.SOURCE_NAME,
                    timestamp=ts,
                    sender="王老师" if sender_id == user_open_id else "学徒", # 简单推断
                    content=content_text,
                    is_mentor=(sender_id == user_open_id),
                    context={"chat_type": "p2p", "chat_id": chat_id}
                ))

            if not data.get("data", {}).get("has_more"): break
            page_token = data.get("data", {}).get("page_token")
        return msgs

    def _fetch_group_messages(self, user_open_id: str, limit: int) -> list[RawMessage]:
        # 找到机器人和用户共同所在的群（简化处理，只采集第一个找到的群）
        data = self.api_get("/im/v1/chats", {"page_size": 100})
        if data.get("code") != 0: return []

        all_msgs = []
        for chat in data.get("data", {}).get("items", []):
            chat_id = chat.get("chat_id")
            # 简单检查用户是否在该群（可以通过获取群成员 API）
            # 此处省略耗时的成员检查，直接拉取该群是否有该用户的消息
            msgs = []
            page_token = None
            while len(msgs) < 100 and (len(all_msgs) + len(msgs)) < limit:
                params = {"container_id_type": "chat", "container_id": chat_id, "page_size": 50}
                if page_token: params["page_token"] = page_token
                data_msg = self.api_get("/im/v1/messages", params)
                if data_msg.get("code") != 0: break
                items = data_msg.get("data", {}).get("items", [])
                if not items: break
                for item in items:
                    sender_id = item.get("sender", {}).get("id") or item.get("sender", {}).get("open_id")
                    if sender_id != user_open_id: continue
                    content_text = self._parse_content(item.get("body", {}).get("content", ""))
                    if not content_text: continue
                    ts = datetime.fromtimestamp(int(item.get("create_time", 0)) / 1000, tz=timezone.utc)
                    msgs.append(RawMessage(
                        source=self.SOURCE_NAME,
                        timestamp=ts,
                        sender="王老师",
                        content=content_text,
                        is_mentor=True,
                        context={"chat_type": "group", "chat_id": chat_id, "chat_name": chat.get("name")}
                    ))
                if not data_msg.get("data", {}).get("has_more"): break
                page_token = data_msg.get("data", {}).get("page_token")
            all_msgs.extend(msgs)
            if len(all_msgs) >= limit: break
        return all_msgs

    def _parse_content(self, raw_content: str) -> str:
        try:
            obj = json.loads(raw_content)
            if "text" in obj: return obj["text"]
            # 富文本处理
            if "content" in obj:
                text_parts = []
                for line in obj["content"]:
                    for seg in line:
                        if seg.get("tag") in ("text", "a"):
                            text_parts.append(seg.get("text", ""))
                return " ".join(text_parts)
            return str(obj)
        except Exception:
            return raw_content

    def _collect_docs(self, user_open_id: str, name: str, limit: int) -> list[RawMessage]:
        """采集用户创建/编辑的飞书文档正文"""
        token = self.get_tenant_token()

        # 搜索该用户相关的文档
        resp = requests.post(
            f"{self.BASE_URL}/suite/docs-api/search/object",
            json={
                "search_key": name,
                "count": limit,
                "offset": 0,
                "owner_ids": [user_open_id],
                "obj_types": ["doc", "docx", "wiki"],
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        ).json()

        msgs: list[RawMessage] = []
        objects = resp.get("data", {}).get("objects", [])

        for obj in objects[:limit]:
            obj_type = obj.get("obj_type", "doc")
            obj_token = obj.get("obj_token", "")
            title = obj.get("title", "Untitled")
            url = obj.get("url", "")

            content = self._fetch_doc_content(obj_type, obj_token, title, token)

            msgs.append(RawMessage(
                source=self.SOURCE_NAME,
                timestamp=datetime.now(timezone.utc),
                sender=name,
                content=content,
                is_mentor=True,
                context={"type": "doc", "obj_type": obj_type, "title": title, "url": url},
            ))
            console.print(f"    [dim]📄 已采集文档：{title}（{len(content)} 字）[/dim]")

        return msgs

    def _fetch_doc_content(self, obj_type: str, obj_token: str, title: str, token: str) -> str:
        """拉取文档正文（docx v1 API）"""
        if not obj_token:
            return f"文档标题：{title}\n（无法获取正文：缺少 token）"

        try:
            if obj_type == "docx":
                resp = requests.get(
                    f"{self.BASE_URL}/docx/v1/documents/{obj_token}/raw_content",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=20,
                ).json()
                if resp.get("code") == 0:
                    return f"# {title}\n\n{resp['data'].get('content', '')}"

            elif obj_type == "doc":
                resp = requests.get(
                    f"{self.BASE_URL}/doc/v2/{obj_token}/content",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=20,
                ).json()
                if resp.get("code") == 0:
                    raw = resp.get("data", {}).get("content", "{}")
                    return self._parse_doc_content(title, raw)

            elif obj_type == "wiki":
                # Wiki 需要先拿 node token，再按 docx 处理
                node_resp = requests.get(
                    f"{self.BASE_URL}/wiki/v2/spaces/get_node",
                    params={"token": obj_token},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                ).json()
                if node_resp.get("code") == 0:
                    node = node_resp.get("data", {}).get("node", {})
                    obj_token2 = node.get("obj_token", "")
                    obj_type2 = node.get("obj_type", "docx")
                    if obj_token2:
                        return self._fetch_doc_content(obj_type2, obj_token2, title, token)

        except Exception as e:
            console.print(f"    [yellow]⚠ 文档 [{title}] 正文获取失败：{e}[/yellow]")

        return f"# {title}\n（正文获取失败，仅保留标题）"

    def _parse_doc_content(self, title: str, raw_json: str) -> str:
        """解析旧版飞书 doc JSON 格式，提取纯文本"""
        try:
            doc = json.loads(raw_json)
            texts: list[str] = [f"# {title}"]
            body = doc.get("body", {})
            for block in body.get("blocks", []):
                for elem in block.get("elements", []):
                    text_run = elem.get("textRun", {})
                    if text_run.get("content"):
                        texts.append(text_run["content"])
            return "\n".join(texts)
        except Exception:
            return f"# {title}\n{raw_json[:2000]}"

    def validate_input(self, **kwargs) -> bool:
        return bool(self.app_id and self.app_secret)
