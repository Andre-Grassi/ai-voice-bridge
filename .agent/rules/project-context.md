---
trigger: always_on
---

# Project Context: AI Voice Bridge

## 1. Project Overview
I am developing a "Voice Gateway" microservice in Python. The goal of this system is to act as a low-latency, agnostic bridge between a client interface (initially an Unreal Engine 5 VR game) and Google's Multimodal "Gemini Live" API.

**Deployment Model:** The gateway runs on a **remote server** (cloud VM, container, etc.). Unreal Engine connects via WebSocket, sends user speech audio, and receives AI-generated speech audio back.

## 2. Architectural Philosophy
The system follows **Pragmatic Minimal Architecture** - a simplified approach that prioritizes:
* **Simplicity:** Fewer files, less abstraction overhead.
* **Flexibility:** Configurable behavior via environment variables.
* **Testability:** Dependencies injected for easy mocking.
* **Stateless Server:** No local audio hardware dependencies. All audio I/O is via network.

> **Note:** This is a simplified architecture optimized for rapid development. Can evolve to full Hexagonal Architecture if needed in the future.

## 3. Tech Stack
* **Language:** Python 3.14 (focus on `asyncio`).
* **AI Provider:** Google Gemini Live API (via WebSocket `wss://`).
* **Client Communication:** WebSocket server (via `websockets` library) for bidirectional audio + control.
* **Audio I/O:** Network-based only. Client (Unreal) handles microphone/speaker access.
* **Audio Format:** PCM 16-bit, 16kHz input / 24kHz output, Mono.

## 4. Configurable Session Strategies
The service must support two distinct operating modes, selectable via an environment variable (`CONNECTION_MODE`):

### Mode A: "On-Demand" (Walkie-Talkie Style)
* **Behavior:** Connection to Gemini is **only established** when client sends `start_talking` and **closed** on `stop_talking`.
* **Context Injection:** Maintains **local conversation history (RAM)**. On every reconnection, injects accumulated text history into `system_instruction`.

### Mode B: "Always-On" (Continuous Style)
* **Behavior:** Connection to Gemini is established on startup and stays open indefinitely.
* **Auto-Reconnection:** If connection drops (15-min limit, timeout), reconnects immediately and transparently.

## 5. Data Flow (Pipeline)

```
┌─────────────────┐     WebSocket      ┌─────────────────┐     WebSocket      ┌─────────────────┐
│  Unreal Engine  │◄─────────────────►│  Voice Gateway  │◄─────────────────►│  Gemini Live    │
│     (Client)    │   audio + events   │    (Server)     │   audio + events   │      API        │
└─────────────────┘                    └─────────────────┘                    └─────────────────┘
```

1. **Unreal → Gateway:** Sends `start_talking`, `stop_talking`, and PCM audio chunks.
2. **Gateway → Gemini:** Forwards audio to Gemini Live API.
3. **Gemini → Gateway:** Receives AI audio and text responses.
4. **Gateway → Unreal:** Sends `speaking` events, `subtitle` text, and PCM audio chunks.

## 6. WebSocket Protocol (Gateway ↔ Unreal Engine)

### Messages FROM Unreal (Client → Gateway)
```json
{"type": "start_talking"}
{"type": "stop_talking"}
{"type": "audio", "data": "<base64 PCM 16kHz>"}
```

### Messages TO Unreal (Gateway → Client)
```json
{"type": "connected"}
{"type": "ready"}
{"type": "speaking", "value": true}
{"type": "speaking", "value": false}
{"type": "subtitle", "text": "Hello, how can I help you?"}
{"type": "audio", "data": "<base64 PCM 24kHz>"}
{"type": "turn_complete"}
{"type": "error", "message": "..."}
```

## 7. File Structure (PyPI-Ready, Pragmatic Minimal)

The project uses the **src layout** with a **flat package structure** for simplicity.

```
ai-voice-bridge/                        # Repository root
├── src/
│   └── ai_voice_bridge/                # Python package (importable)
│       ├── __init__.py                 # Package version and exports
│       ├── __main__.py                 # python -m ai_voice_bridge
│       ├── cli.py                      # CLI entry point
│       ├── config.py                   # Pydantic settings
│       ├── bridge.py                   # Main coordinator (VoiceBridge)
│       ├── gemini_client.py            # Gemini Live WebSocket client
│       ├── websocket_server.py         # Client-facing WebSocket server
│       └── strategies/
│           ├── __init__.py
│           ├── base.py                 # SessionStrategy ABC
│           ├── on_demand.py
│           └── always_on.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── ...
├── Dockerfile
├── .env.example
├── pyproject.toml
├── README.md
└── LICENSE
```

### Import Examples
```python
from ai_voice_bridge import VoiceBridge
from ai_voice_bridge.strategies import OnDemandStrategy
from ai_voice_bridge.gemini_client import GeminiClient
```

### Run Commands
```bash
# Development
pip install -e .
python -m ai_voice_bridge

# CLI (after install)
ai-voice-bridge

# Docker  
docker run -p 8765:8765 ai-voice-bridge
```

## 8. Code Generation Instructions
* **Pattern:** Use the **Strategy Pattern** for session modes (On-Demand vs Always-On).
* **Config:** Use a `.env` file to select the mode (`CONNECTION_MODE=ON_DEMAND`).
* **Memory:** Append text transcripts to a local list for "Context Injection" in On-Demand mode.
* **Async:** Ensure non-blocking I/O with `asyncio`.
* **No Hardware Dependencies:** Do not use PyAudio or any local audio libraries.
* **Binary WebSocket Frames:** Use binary frames for audio to reduce overhead (optional optimization).
* **No Abstract Ports:** Use concrete classes directly; avoid over-abstraction.
* Stick to modern Python conventions.