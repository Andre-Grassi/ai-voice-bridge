"""Configuração centralizada via variáveis de ambiente."""

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConnectionMode(str, Enum):
    """Modo de conexão com Gemini: On-Demand ou Always-On."""

    ON_DEMAND = "ON_DEMAND"
    ALWAYS_ON = "ALWAYS_ON"


class Settings(BaseSettings):
    """Configuração do AI Voice Bridge via variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API
    google_api_key: str
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_voice: str = "Aoede"
    system_prompt: str = "You are a helpful AI assistant in a VR environment."

    # Session Strategy
    connection_mode: ConnectionMode = ConnectionMode.ON_DEMAND

    # Audio Settings (PCM 16-bit, Mono)
    input_sample_rate: int = 16000  # Cliente → Gemini
    output_sample_rate: int = 24000  # Gemini → Cliente

    # WebSocket Server
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765

    # History (On-Demand mode)
    max_history_messages: int = 20

    # Debug
    debug_play_audio_locally: bool = False


settings = Settings()
