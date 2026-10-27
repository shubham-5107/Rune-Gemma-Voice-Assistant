---
name: buddy-gemma-agent
description: Offline desktop voice agent that uses Gemma 3 (via Ollama) to turn spoken commands into validated tool calls - timers, opening websites, a daily routine, and the time. Use when you need a wake-word voice assistant powered by a local open-weight model instead of a cloud LLM.
license: MIT
compatibility: Python 3.10+, Ollama, microphone
---

# Buddy - offline Gemma voice agent

## Usage
1. `pip install -r requirements.txt`
2. `ollama pull gemma3:4b` (Ollama must be running)
3. `python scripts/main.py` from the project root
4. Say "Buddy, <command>". Input without the word "buddy" is ignored.

## Supported commands
- `set_timer` - duration 1-86400 s, optional label
- `open_website` - plain domain; `.com` appended if no dot
- `start_daily_routine` - calls `SKILLS/start_my_day.py` if present, else a placeholder
- `get_time`, `list_capabilities`
- `ask_user` - one clarifying question per request
- `unknown_request` - polite fallback (also used by the model to signal "all steps done")

## Safety rules
- Gemma only returns JSON; Python validates every action and argument before running anything.
- No shell execution, file deletion, or credential access. Only the listed tools exist.
- Browsers are allowlisted; domains are regex-checked; max 4 agent steps per request.
- Invalid model output is retried once, then falls back to `unknown_request`.
- Every interaction is logged to `logs/agent_log.jsonl`.

## Example requests
- "Buddy, set a 10 minute timer for pasta"
- "Buddy, open youtube"
- "Buddy, start my day and set a 25-minute focus timer"
- "Buddy, what time is it?"
