"""Tool implementations and argument validation. Gemma selects; Python validates and executes."""
from __future__ import annotations

import re
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from voice_io import VoiceIO

ROOT = Path(__file__).resolve().parent.parent
MAX_TIMER_SECONDS = 86400
# Allowlist: webbrowser.get() can launch arbitrary executables for unknown names.
ALLOWED_BROWSERS = {"default", "chrome", "firefox", "safari", "edge"}
DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")

CAPABILITIES = (
    "I can set timers, open websites, start your daily routine, "
    "tell the time, and ask you questions when I'm unsure."
)
FALLBACK = (
    "Sorry, I can't do that. Try asking me to set a timer, "
    "open a website, start your day, or tell the time."
)
ROUTINE_PLACEHOLDER = (
    "Starting your day. Add SKILLS/start_my_day.py to customise this routine."
)

Args = dict[str, Any]
Tool = Callable[[Args, VoiceIO], str]


# ---------- validation ----------

def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("duration_seconds must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    raise ValueError("duration_seconds must be an integer.")


def _validate_timer(args: Args) -> Args:
    seconds = _to_int(args.get("duration_seconds"))
    if not 1 <= seconds <= MAX_TIMER_SECONDS:
        raise ValueError(f"duration_seconds must be between 1 and {MAX_TIMER_SECONDS}.")
    label = args.get("label") or ""
    if not isinstance(label, str):
        raise ValueError("label must be a string.")
    return {"duration_seconds": seconds, "label": label.strip()[:80]}


def _validate_website(args: Args) -> Args:
    domain = args.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain is required.")
    domain = re.sub(r"^https?://", "", domain.strip().lower()).rstrip("/")
    if "." not in domain:
        domain += ".com"
    if not DOMAIN_RE.match(domain):
        raise ValueError("domain must be a plain lowercase domain like youtube.com.")
    browser = args.get("browser") or "default"
    if not isinstance(browser, str) or browser.lower() not in ALLOWED_BROWSERS:
        raise ValueError(f"browser must be one of {sorted(ALLOWED_BROWSERS)}.")
    return {"domain": domain, "browser": browser.lower()}


def _validate_question(args: Args) -> Args:
    question = args.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required.")
    return {"question": question.strip()[:200]}


def _no_args(_: Args) -> Args:
    return {}


VALIDATORS: dict[str, Callable[[Args], Args]] = {
    "set_timer": _validate_timer,
    "open_website": _validate_website,
    "start_daily_routine": _no_args,
    "get_time": _no_args,
    "list_capabilities": _no_args,
    "ask_user": _validate_question,
    "unknown_request": _no_args,
}


def validate_arguments(action: str, args: Args) -> Args:
    """Return cleaned arguments or raise ValueError."""
    return VALIDATORS[action](args)


# ---------- tools ----------

def set_timer(args: Args, voice: VoiceIO) -> str:
    seconds = args["duration_seconds"]
    label = args["label"] or "your timer"

    def _ring() -> None:
        time.sleep(seconds)
        voice.speak(f"Timer finished: {label}.")

    threading.Thread(target=_ring, daemon=True).start()
    return "Timer set."


def open_website(args: Args, voice: VoiceIO) -> str:
    domain = args["domain"]
    url = f"https://{domain}"
    name = None if args["browser"] == "default" else args["browser"]
    try:
        opened = webbrowser.get(name).open(url)
    except webbrowser.Error:
        opened = webbrowser.open(url)  # requested browser missing: use the default
    if not opened:
        raise RuntimeError("Could not open a browser.")
    return f"Opening {domain}."


def start_daily_routine(args: Args, voice: VoiceIO) -> str:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from SKILLS.start_my_day import start_my_day
    except ImportError:
        return ROUTINE_PLACEHOLDER
    result = start_my_day()
    report = getattr(result, "report", None) or getattr(start_my_day, "report", None)
    if callable(report):
        report = report()
    if report is None and isinstance(result, str):
        report = result
    return str(report) if report else "Your day has been started."


def get_time(args: Args, voice: VoiceIO) -> str:
    return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}."


def list_capabilities(args: Args, voice: VoiceIO) -> str:
    return CAPABILITIES


def ask_user(args: Args, voice: VoiceIO) -> str:
    """Speak the question, listen once; returns '' if no reply was heard."""
    voice.speak(args["question"])
    return voice.listen(timeout=8, phrase_limit=10) or ""


def unknown_request(args: Args, voice: VoiceIO) -> str:
    return FALLBACK


TOOLS: dict[str, Tool] = {
    "set_timer": set_timer,
    "open_website": open_website,
    "start_daily_routine": start_daily_routine,
    "get_time": get_time,
    "list_capabilities": list_capabilities,
    "ask_user": ask_user,
    "unknown_request": unknown_request,
}
ACTIONS = tuple(TOOLS)
# Tools whose real output (not the model's guess) should be spoken.
SPEAKS_RESULT = {"get_time", "list_capabilities", "start_daily_routine", "unknown_request"}


def execute(action: str, args: Args, voice: VoiceIO) -> str:
    return TOOLS[action](args, voice)
