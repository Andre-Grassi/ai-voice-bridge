"""Coordenador principal do AI Voice Bridge."""

import asyncio
import base64
import logging

from ai_voice_bridge.config import settings, ConnectionMode
from ai_voice_bridge.websocket_server import WebSocketServer
from ai_voice_bridge.gemini_client import GeminiClient
from ai_voice_bridge.strategies.base import SessionStrategy
from ai_voice_bridge.strategies.on_demand import OnDemandStrategy
from ai_voice_bridge.strategies.always_on import AlwaysOnStrategy

logger = logging.getLogger(__name__)


class VoiceBridge:
    """Coordenador principal do AI Voice Bridge."""

    def __init__(self) -> None:
        self._ws = WebSocketServer()
        self._gemini = GeminiClient()
        self._strategy = self._create_strategy()
        self._response_task: asyncio.Task | None = None

    def _create_strategy(self) -> SessionStrategy:
        """Cria estratégia baseada na configuração."""
        if settings.connection_mode == ConnectionMode.ON_DEMAND:
            logger.info("[bridge] Usando estratégia On-Demand")
            return OnDemandStrategy(self._gemini)
        else:
            logger.info("[bridge] Usando estratégia Always-On")
            return AlwaysOnStrategy(self._gemini)

    async def run(self) -> None:
        """Inicia o bridge."""
        logger.info("[bridge] Iniciando AI Voice Bridge...")

        # Inicia servidor WebSocket
        await self._ws.start(
            on_start_talking=self._handle_start,
            on_stop_talking=self._handle_stop,
            on_audio_chunk=self._handle_audio,
        )

        # Inicializa estratégia
        await self._strategy.initialize()
        await self._ws.send_ready()

        # Inicia processamento de respostas
        self._response_task = asyncio.create_task(self._process_responses())

        logger.info("[bridge] AI Voice Bridge pronto!")

    async def _handle_start(self) -> None:
        """Handler para start_talking."""
        logger.debug("[bridge] start_talking recebido")
        await self._strategy.on_start_talking()

    async def _handle_stop(self) -> None:
        """Handler para stop_talking."""
        logger.debug("[bridge] stop_talking recebido")
        await self._strategy.on_stop_talking()

    async def _handle_audio(self, chunk: bytes) -> None:
        """Handler para áudio recebido do cliente."""
        await self._strategy.send_audio(chunk)

    async def _process_responses(self) -> None:
        """Processa respostas do Gemini e envia para clientes."""
        try:
            async for msg in self._strategy.receive_responses():
                # Processa áudio
                if audio_data := self._extract_audio(msg):
                    await self._ws.send_speaking(True)
                    await self._ws.send_audio(audio_data)

                # Processa texto (legendas)
                if text := self._extract_text(msg):
                    await self._ws.send_subtitle(text)

                # Detecta fim de turno
                if self._is_turn_complete(msg):
                    await self._ws.send_speaking(False)
                    await self._ws.send_turn_complete()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[bridge] Erro no processamento: %s", e)
            await self._ws.send_error(str(e))

    def _extract_audio(self, msg: dict) -> bytes | None:
        """Extrai áudio PCM da resposta Gemini."""
        try:
            parts = msg.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
            for part in parts:
                if inline := part.get("inlineData"):
                    mime = inline.get("mimeType", "")
                    if "audio" in mime:
                        return base64.b64decode(inline["data"])
        except Exception:
            pass
        return None

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

    def _is_turn_complete(self, msg: dict) -> bool:
        """Verifica se o turno foi concluído."""
        return msg.get("serverContent", {}).get("turnComplete", False)

    async def shutdown(self) -> None:
        """Encerra o bridge."""
        logger.info("[bridge] Encerrando...")
        if self._response_task:
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass
        await self._strategy.shutdown()
        await self._ws.stop()
        logger.info("[bridge] AI Voice Bridge encerrado")
