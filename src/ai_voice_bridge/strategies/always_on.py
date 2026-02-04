"""Estratégia Always-On: conexão persistente com auto-reconexão."""

import asyncio
import logging
from typing import AsyncIterator

from ai_voice_bridge.config import settings
from ai_voice_bridge.gemini_client import GeminiClient
from ai_voice_bridge.strategies.base import SessionStrategy

logger = logging.getLogger(__name__)


class AlwaysOnStrategy(SessionStrategy):
    """Estratégia 'Always-On': conexão persistente com auto-reconexão."""

    def __init__(self, gemini: GeminiClient) -> None:
        super().__init__(gemini)
        self._reconnect_task: asyncio.Task | None = None
        self._should_run = True

    async def initialize(self) -> None:
        """Conecta imediatamente e inicia monitor de reconexão."""
        await self._connect()
        self._reconnect_task = asyncio.create_task(self._reconnect_monitor())
        logger.info("[always-on] Estratégia inicializada com conexão ativa")

    async def _connect(self) -> None:
        """Cria nova conexão com Gemini."""
        await self._gemini.connect(settings.system_prompt)
        logger.info("[always-on] Conexão estabelecida")

    async def _reconnect_monitor(self) -> None:
        """Monitor que reconecta automaticamente em caso de queda."""
        while self._should_run:
            try:
                await asyncio.sleep(1)
                if not self._gemini.is_connected:
                    logger.warning("[always-on] Conexão perdida, reconectando...")
                    try:
                        await self._connect()
                    except Exception as e:
                        logger.error("[always-on] Falha na reconexão: %s", e)
                        await asyncio.sleep(5)  # Backoff
            except asyncio.CancelledError:
                break

    async def on_start_talking(self) -> None:
        """Conexão já ativa, nenhuma ação necessária."""
        pass

    async def on_stop_talking(self) -> None:
        """Mantém conexão ativa."""
        pass

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Envia áudio para Gemini se conectado."""
        if self._gemini.is_connected:
            await self._gemini.send_audio(pcm_chunk)

    async def receive_responses(self) -> AsyncIterator[dict]:
        """Recebe respostas do Gemini continuamente."""
        while self._should_run:
            if self._gemini.is_connected:
                try:
                    async for msg in self._gemini.receive_messages():
                        yield msg
                except Exception as e:
                    logger.warning("[always-on] Erro no receive: %s", e)
            await asyncio.sleep(0.1)

    async def shutdown(self) -> None:
        """Encerra a estratégia e para o monitor."""
        self._should_run = False
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        await self._gemini.close()
