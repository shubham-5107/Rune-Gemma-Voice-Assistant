# Rune - Gemma Voice Agent

Rune is a desktop voice assistant that replaces keyword matching with a local Gemma 3 model running through Ollama. After the wake word "buddy", Gemma picks a tool, extracts its arguments, and returns strict JSON; Python validates the JSON and executes only whitelisted tools (timers, websites, daily routine, time), speaking replies with pyttsx3 and logging every interaction.

## Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- A working microphone and speakers
- PyAudio build requirements (Windows: wheel installs directly; macOS: `brew install portaudio`; Linux: `sudo apt install portaudio19-dev espeak`)

## Install
```bash
cd buddy-gemma-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ollama setup
```bash
ollama pull gemma3:4b
```

## Run
```bash
python scripts/main.py
```

## Example voice commands
1. "Buddy, set a 10 minute timer for pasta."
2. "Buddy, open youtube."
3. "Buddy, what time is it?"
4. "Buddy, start my day and set a 25-minute focus timer."
5. "Buddy, what can you do?"

## Safety notes
- No shell commands, file deletion, or credential access; only the seven listed tools exist.
- All model output is validated before execution; invalid output is retried once, then rejected.
- Speech-to-text uses `recognize_google`, which sends audio to Google's web service. The LLM itself runs fully offline; swap in an offline recognizer (e.g. Vosk) for end-to-end offline use.
- Logs are stored locally in `logs/agent_log.jsonl` and contain your spoken queries.

## Author

SHUBHAM SHARMA
GITHUB: https://github.com/shubham-5107
