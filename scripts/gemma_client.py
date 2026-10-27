"""Gemma (via Ollama) client: prompt, strict JSON parsing, validation, one retry."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import ollama

from tools import ACTIONS, validate_arguments

MODEL = "gemma3:4b"
TEMPERATURE = 0.2
MAX_REPLY_WORDS = 25

SYSTEM_PROMPT = """You are Buddy, an offline desktop voice agent running locally on the user's computer.
Pick exactly ONE tool for the user's request.

Reply with ONLY one JSON object. No markdown, no code fences, no extra text:
{"action": "<tool name>", "arguments": {...}, "spoken_reply": "<short natural response>"}

Allowed tools and argument schemas (use no others):
- set_timer: {"duration_seconds": integer 1-86400, "label": string (optional)}
- open_website: {"domain": "lowercase domain, no protocol, no spaces, e.g. youtube.com", "browser": "default" (optional)}
- start_daily_routine: {}
- get_time: {}
- list_capabilities: {}
- ask_user: {"question": "short clarifying question"}
- unknown_request: {}

Rules:
- Convert durations to seconds (25 minutes = 1500).
- If the command is ambiguous or missing a required detail, use ask_user.
- If no tool fits, use unknown_request.
- Never invent tools. Never perform destructive actions (deleting files, shell commands, passwords, credentials); use unknown_request instead.
- spoken_reply must be under 25 words.
- Messages starting with "TOOL_RESULT" report a finished step. If more steps of the ORIGINAL request remain, return the next tool. If everything is done, return unknown_request with empty arguments and spoken_reply "".
- Do not repeat a tool that already succeeded unless asked."""


@dataclass
class AgentDecision:
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    spoken_reply: str = ""


FALLBACK_DECISION = AgentDecision("unknown_request", {}, "")


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("Output is not valid JSON.")
        data = json.loads(cleaned[start : end + 1])  # JSONDecodeError is a ValueError
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")
    return data


def parse_decision(text: str) -> AgentDecision:
    """Parse and validate model output; raises ValueError describing the problem."""
    data = _extract_json(text)
    action = data.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action!r}. Allowed: {', '.join(ACTIONS)}.")
    args = data.get("arguments", {})
    if not isinstance(args, dict):
        raise ValueError("'arguments' must be an object.")
    reply = data.get("spoken_reply", "")
    if not isinstance(reply, str):
        raise ValueError("'spoken_reply' must be a string.")
    reply = " ".join(reply.split()[:MAX_REPLY_WORDS])
    return AgentDecision(action, validate_arguments(action, args), reply)


class GemmaClient:
    def __init__(self, model: str = MODEL) -> None:
        self.model = model

    def _chat(self, messages: list[dict[str, str]]) -> str:
        response = ollama.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": TEMPERATURE},
        )
        return response["message"]["content"]

    def decide(self, messages: list[dict[str, str]]) -> tuple[AgentDecision, str, str]:
        """Return (decision, raw_output, validation_status). Retries once on invalid output."""
        raw = self._chat(messages)
        try:
            return parse_decision(raw), raw, "ok"
        except ValueError as err:
            feedback = (
                f"Invalid output: {err} Reply again with ONLY the valid JSON object "
                "in the required format."
            )
        retry = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": feedback},
        ]
        raw = self._chat(retry)
        try:
            return parse_decision(raw), raw, "retry_ok"
        except ValueError as err:
            return FALLBACK_DECISION, raw, f"invalid: {err}"
