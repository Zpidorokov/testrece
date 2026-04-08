from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx

from app.core.enums import AirouterDecision
from app.core.settings import Settings
from app.schemas.telegram import AIRouterOutput, AIRouterReply


class OpenRouterAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_reply(self, *, prompt: str, fallback: AIRouterReply) -> AIRouterReply:
        if self.settings.openrouter_dry_run or not self.settings.openrouter_api_key:
            return fallback

        payload: Dict[str, Any] = {
            "model": self.settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON with keys: split, messages.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.45,
            "max_tokens": 450,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return AIRouterReply(**parsed)

    async def generate(self, *, prompt: str, fallback: AIRouterOutput) -> AIRouterOutput:
        if self.settings.openrouter_dry_run or not self.settings.openrouter_api_key:
            return fallback

        payload: Dict[str, Any] = {
            "model": self.settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON with keys: decision, intent, risk_level, "
                        "should_escalate, reply, extracted_entities, next_action."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.25,
            "max_tokens": 450,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if "reply" not in parsed:
            parsed["reply"] = {"split": False, "messages": []}
        return AIRouterOutput(**parsed)


def build_fallback_output(intent: str, risk_level: str, should_escalate: bool, messages: List[str], next_action: str) -> AIRouterOutput:
    return AIRouterOutput(
        decision=AirouterDecision.ESCALATE.value if should_escalate else AirouterDecision.REPLY.value,
        intent=intent,
        risk_level=risk_level,
        should_escalate=should_escalate,
        reply=AIRouterReply(split=len(messages) > 1, messages=messages),
        extracted_entities={},
        next_action=next_action,
    )
