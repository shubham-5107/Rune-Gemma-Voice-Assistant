"""Buddy: offline Gemma-powered desktop voice agent. Run: python scripts/main.py"""
from __future__ import annotations

import re
import sys

from gemma_client import FALLBACK_DECISION, AgentDecision, GemmaClient, SYSTEM_PROMPT
from logger import log_interaction
from tools import SPEAKS_RESULT, execute
from voice_io import VoiceIO

WAKE_WORD = "buddy"
MAX_STEPS = 4


def clean_command(heard: str) -> str | None:
    """None if the wake word is absent; otherwise the text with the wake word removed."""
    if not re.search(rf"\b{WAKE_WORD}\b", heard, flags=re.I):
        return None
    return re.sub(rf"\b{WAKE_WORD}\b[\s,.:!?-]*", "", heard, count=1, flags=re.I).strip()


def handle_request(query: str, client: GemmaClient, voice: VoiceIO) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    asked = False
    for step in range(MAX_STEPS):
        try:
            decision, raw, status = client.decide(messages)
        except Exception as err:  # Ollama not running, model missing, etc.
            log_interaction(query, "", "model_error", None, error=str(err))
            voice.speak("I can't reach my language model. Is Ollama running?")
            return

        if decision.action == "ask_user" and asked:  # one clarifying question per request
            decision = AgentDecision(**vars(FALLBACK_DECISION))
        elif decision.action == "unknown_request" and step > 0:
            # Convention: after a tool ran, unknown_request means "nothing left to do".
            log_interaction(query, raw, status, None, result="request complete")
            return
        asked = asked or decision.action == "ask_user"
        messages.append({"role": "assistant", "content": raw})

        try:
            result = execute(decision.action, decision.arguments, voice)
        except Exception as err:
            log_interaction(query, raw, status, decision.action, error=str(err))
            voice.speak("Sorry, something went wrong with that.")
            return
        log_interaction(query, raw, status, decision.action, result=result)

        if decision.action == "ask_user":  # the tool already spoke the question
            if not result:
                voice.speak("I didn't catch a reply.")
                return
            result = f"user replied: {result}"
        elif decision.action in SPEAKS_RESULT:
            voice.speak(result)
        else:
            voice.speak(decision.spoken_reply or result)

        if decision.action == "unknown_request":
            return
        messages.append({"role": "user", "content": f"TOOL_RESULT {decision.action}: {result}"})


def main() -> None:
    voice = VoiceIO()
    client = GemmaClient()
    voice.speak("Buddy is ready.")
    print(f"Say '{WAKE_WORD}' followed by a command. Press Ctrl+C to quit.")
    try:
        while True:
            print("Listening...", end="\r", flush=True)
            heard = voice.listen()
            if not heard:
                continue
            print(f"You: {heard}")
            command = clean_command(heard)
            if command is None:
                continue
            if not command:  # wake word alone
                voice.speak("Yes?")
                command = voice.listen()
                if not command:
                    continue
            handle_request(command, client, voice)
    except KeyboardInterrupt:
        print("\nBye.")
    except (OSError, AttributeError) as err:  # no microphone / PyAudio missing
        print(f"Microphone error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
