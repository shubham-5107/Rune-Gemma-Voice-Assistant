"""Speech input (speech_recognition) and output (pyttsx3)."""
from __future__ import annotations

import threading

import pyttsx3
import speech_recognition as sr


class VoiceIO:
    def __init__(self, rate: int = 170) -> None:
        self._engine = pyttsx3.init()  # initialised once, reused for every response
        self._engine.setProperty("rate", rate)
        self._speak_lock = threading.Lock()  # timer threads and main thread share the engine
        self._recognizer = sr.Recognizer()
        self._calibrated = False

    def speak(self, text: str) -> None:
        if not text:
            return
        print(f"Buddy: {text}")
        with self._speak_lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def listen(self, timeout: float = 6, phrase_limit: float = 10) -> str | None:
        """Listen once. Returns recognised text, or None on silence/failure."""
        with sr.Microphone() as source:
            if not self._calibrated:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self._calibrated = True
            try:
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
            except sr.WaitTimeoutError:
                return None
        try:
            return self._recognizer.recognize_google(audio, language="en-in").strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as err:
            print(f"[speech recognition unavailable: {err}]")
            return None
