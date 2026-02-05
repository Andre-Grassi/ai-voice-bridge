"""Estratégia On-Demand: conecta/desconecta por interação."""

import logging
from typing import AsyncIterator

from ai_voice_bridge.config import settings
from ai_voice_bridge.gemini_client import GeminiClient
from ai_voice_bridge.strategies.base import SessionStrategy

logger = logging.getLogger(__name__)


class OnDemandStrategy(SessionStrategy):
    """Estratégia 'Walkie-Talkie': conecta/desconecta por interação.

    Mantém histórico local e injeta no system_instruction a cada reconexão.
    """

    def __init__(self, gemini: GeminiClient) -> None:
        super().__init__(gemini)
        self._history: list[dict[str, str]] = []
        self._is_active = False

    async def initialize(self) -> None:
        """Inicializa a estratégia (aguarda start_talking)."""
        logger.info("[on-demand] Estratégia inicializada (aguardando start_talking)")

    async def on_start_talking(self) -> None:
        """Conecta ao Gemini com histórico injetado."""
        if self._is_active:
            return

        logger.info("[on-demand] Iniciando sessão Gemini...")
        try:
            await self._gemini.connect(self._build_context_prompt())
            self._is_active = True
            logger.info("[on-demand] Sessão ativa, pronta para áudio")
        except Exception as e:
            logger.error("[on-demand] Erro ao conectar ao Gemini: %s", e)
            self._is_active = False
            raise

    async def on_stop_talking(self) -> None:
        """Encerra a sessão Gemini."""
        if not self._is_active:
            return

        logger.info("[on-demand] Encerrando sessão...")
        await self._gemini.close()
        self._is_active = False

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Envia áudio para Gemini se sessão estiver ativa."""
        if self._is_active:
            await self._gemini.send_audio(pcm_chunk)

    async def receive_responses(self) -> AsyncIterator[dict]:
        """Recebe respostas do Gemini e salva texto no histórico."""
        if not self._is_active:
            return

        async for msg in self._gemini.receive_messages():
            # Salva texto no histórico
            if text := self._extract_text(msg):
                self._history.append({"role": "assistant", "content": text})
            yield msg

    async def shutdown(self) -> None:
        """Encerra a estratégia."""
        await self._gemini.close()

    def add_to_history(self, role: str, text: str) -> None:
        """Adiciona ao histórico de conversa."""
        if text.strip():
            self._history.append({"role": role, "content": text})

    def _build_context_prompt(self) -> str:
        """Constrói prompt com histórico para injeção no system_instruction."""
        base = settings.system_prompt

        if not self._history:
            return base

        # Limita histórico
        recent = self._history[-settings.max_history_messages :]

        history_text = "\n\n--- Previous Conversation ---\n"
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "--- End History ---\n\n"

        return f"{base}\n{history_text}Continue the conversation naturally."

    def _extract_text(self, msg: dict) -> str | None:
        """Extrai texto da resposta Gemini."""
        try:
            parts = msg.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
            for part in parts:
                if text := part.get("text"):
                    return text
        except Exception:
            pass
        return None
