# Apoorva AI
**Personal AI Assistant**

An advanced, local-first personal AI assistant built for Windows with real-time system diagnostics, high-fidelity British neural voice synthesis, hands-free wake word recognition ("Apoorva"), desktop automation, and multi-model intelligence.

---

## Capabilities

- **Refined AI Persona**: Articulate, calm British tone with natural neural voice synthesis.
- **Ultra-Low Latency Pipeline**: Universal token streaming, responsive voice endpoint detection (shaved ~1.5s of dead silence), and sentence-by-sentence pipelined speech synthesis.
- **Parallel Multi-Task Threading**: Concurrent background workers execute multiple user tasks in parallel while sharing the same thread-safe SQLite memory and task board.
- **Live Hardware Diagnostics**: Real-time telemetry monitoring for CPU load & clock frequency, RAM utilization, battery percentage & charging status, disk capacity, network info, and system uptime.
- **Hands-Free Wake Detection**: Say *"Apoorva"* or *"Hey Apoorva"* to command the assistant without pressing any keys (`/wake`).
- **Neural Speech Synthesis**: Powered by Microsoft Neural Edge-TTS (`en-GB-RyanNeural`) with local offline Piper-TTS and Windows SAPI fallback.
- **Universal Application Launcher**: Dynamically launches any installed Windows application (VS Code, Spotify, Discord, Chrome, Edge, Terminal, etc.) or system setting.
- **Hardware & Media Controls**: Control system volume (`volume_up`, `volume_down`, `mute`), media playback (`play`, `pause`, `next`, `previous`), and workstation locking.
- **Visual Intelligence**: Desktop screen capture and multi-modal image analysis (`analyze_screen`).
- **Web & YouTube Research**: DuckDuckGo search and direct YouTube playback without cumbersome prompts.
- **Shared Thread-Safe SQLite Memory**: Persistent fact retention and concurrent task coordination across sessions.


---

## Setup & Installation

```powershell
# Create and activate virtual environment
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# Playwright browser engine
playwright install chromium

# Copy configuration template
Copy-Item .env.example .env
```

### Configuration (`.env`)

Set your preferred provider: `groq`, `gemini`, `openrouter`, or local `ollama`.

```ini
APOORVA_PROVIDER=groq
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=your_key_here

# Optional: Voice Settings
APOORVA_VOICE=en-GB-RyanNeural
APOORVA_VOICE_RATE=+3%
APOORVA_VOICE_PITCH=+0Hz
```

---

## Launching Apoorva AI

```powershell
python main.py
```

### Commands in Console

| Command | Action |
| --- | --- |
| `/wake` or `/handsfree` | Toggle continuous hands-free wake word listening ("Apoorva...") |
| `/voice` | Push-to-talk single utterance capture |
| `/diag` | Full hardware telemetry readout |
| `/stop` | Immediately silence current speech |
| `/tts on` / `/tts off` | Enable or mute vocal responses |
| `/tasks` | Display active background tasks |
| `/approve ID yes\|no` | Authorize sensitive operations |
| `exit` | Power down Apoorva AI |
