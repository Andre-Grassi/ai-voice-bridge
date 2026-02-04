"""AI Voice Bridge - Modular Realtime Voice Bridge for Gemini Live API."""

__version__ = "0.1.0"

from ai_voice_bridge.bridge import VoiceBridge
from ai_voice_bridge.config import settings

__all__ = ["VoiceBridge", "settings", "__version__"]
