from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.settings import Settings
from app.schemas.telegram import TelegramTopicCreateResult


class TelegramGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _post(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.settings.telegram_dry_run:
            return {"ok": True, "result": {"message_id": 1, "message_thread_id": 1001, "name": payload.get("name", "topic")}}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.settings.telegram_bot_api_url}/{method}", json=payload)
            response.raise_for_status()
            return response.json()

    async def send_business_message(
        self,
        *,
        business_connection_id: str,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        return await self._post(
            "sendMessage",
            {
                "business_connection_id": business_connection_id,
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
        )

    async def send_bot_message(
        self,
        *,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
        message_thread_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        return await self._post("sendMessage", payload)

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> Dict[str, Any]:
        return await self._post(
            "answerCallbackQuery",
            {"callback_query_id": callback_query_id, "text": text},
        )

    async def create_forum_topic(self, chat_id: int, title: str) -> TelegramTopicCreateResult:
        response = await self._post("createForumTopic", {"chat_id": chat_id, "name": title})
        result = response.get("result", {})
        thread_id = result.get("message_thread_id", 1001)
        topic_id = result.get("icon_custom_emoji_id")
        return TelegramTopicCreateResult(topic_id=topic_id, message_thread_id=thread_id, title=title)

    async def send_topic_message(self, chat_id: int, thread_id: int, text: str) -> Dict[str, Any]:
        return await self.send_bot_message(chat_id=chat_id, message_thread_id=thread_id, text=text)

    async def send_admin_entrypoint(self, chat_id: int) -> Dict[str, Any]:
        return await self.send_bot_message(
            chat_id=chat_id,
            text=(
                '<b><tg-emoji emoji-id="5870982283724328568">⚙</tg-emoji> '
                "Открыть панель администратора</b>\n\n"
                "Панель доступна только сотрудникам салона."
            ),
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "Открыть панель",
                            "web_app": {"url": self.settings.admin_web_url},
                            "icon_custom_emoji_id": "5870982283724328568",
                        }
                    ]
                ]
            },
        )

    async def send_staff_alert(self, text: str) -> Dict[str, Any]:
        return await self.send_bot_message(
            chat_id=self.settings.staff_group_chat_id,
            text=f'<tg-emoji emoji-id="6039486778597970865">🔔</tg-emoji> {text}',
        )

