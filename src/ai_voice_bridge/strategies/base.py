"""Interface abstrata para estratégias de sessão Gemini."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ai_voice_bridge.gemini_client import GeminiClient


class SessionStrategy(ABC):
    """Interface abstrata para estratégias de sessão Gemini."""

    def __init__(self, gemini: GeminiClient) -> None:
        self._gemini = gemini

    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa a estratégia."""
        ...

    @abstractmethod
    async def on_start_talking(self) -> None:
        """Chamado quando usuário começa a falar."""
        ...

    @abstractmethod
    async def on_stop_talking(self) -> None:
        """Chamado quando usuário para de falar."""
        ...

    @abstractmethod
    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Envia áudio para Gemini."""
        ...

    @abstractmethod
    async def receive_responses(self) -> AsyncIterator[dict]:
        """Recebe respostas do Gemini."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Encerra a estratégia."""
        ...

    def add_to_history(self, role: str, text: str) -> None:
        """Adiciona ao histórico (implementação opcional)."""
        pass
