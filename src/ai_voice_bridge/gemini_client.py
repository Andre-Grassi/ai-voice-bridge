"""Cliente para Gemini Live API usando o SDK oficial google-genai."""

import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from ai_voice_bridge.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Cliente para Gemini Live API (streaming bidirecional de áudio)."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.google_api_key)
        self._session = None
        self._context_manager = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Retorna True se conectado ao Gemini."""
        return self._is_connected and self._session is not None

    async def connect(self, system_prompt: str) -> None:
        """Estabelece conexão com Gemini Live API."""
        logger.info("[gemini] Conectando via SDK...")

        # Configuração simplificada baseada na documentação oficial
        config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_prompt,
        }

        # Live API retorna um async context manager
        self._context_manager = self._client.aio.live.connect(
            model=settings.gemini_model,
            config=config,
        )
        # Entra no context manager manualmente
        self._session = await self._context_manager.__aenter__()
        self._is_connected = True
        logger.info("[gemini] Conexão estabelecida via SDK")

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Envia chunk de áudio PCM para Gemini."""
        if not self.is_connected or self._session is None:
            return

        try:
            await self._session.send_realtime_input(
                audio={
                    "data": pcm_chunk,
                    "mime_type": "audio/pcm",
                }
            )
        except Exception as e:
            logger.warning("[gemini] Erro ao enviar áudio: %s", e)
            self._is_connected = False

    async def receive_messages(self) -> AsyncIterator[dict]:
        """Gera mensagens recebidas do Gemini."""
        if not self._session:
            return

        try:
            turn = self._session.receive()
            async for response in turn:
                # Converte a resposta do SDK para dict no formato esperado
                yield self._convert_response(response)
        except Exception as e:
            logger.error("[gemini] Erro ao receber: %s", e)
            self._is_connected = False

    def _convert_response(self, response) -> dict:
        """Converte resposta do SDK para o formato dict esperado pelo bridge."""
        result = {}

        if hasattr(response, "server_content") and response.server_content:
            server_content = {
                "turnComplete": getattr(response.server_content, "turn_complete", False)
            }

            if (
                hasattr(response.server_content, "model_turn")
                and response.server_content.model_turn
            ):
                parts = []
                for part in response.server_content.model_turn.parts:
                    if hasattr(part, "text") and part.text:
                        parts.append({"text": part.text})
                    elif hasattr(part, "inline_data") and part.inline_data:
                        # Áudio binário
                        parts.append(
                            {
                                "inlineData": {
                                    "mimeType": getattr(
                                        part.inline_data, "mime_type", "audio/pcm"
                                    ),
                                    "data": part.inline_data.data,  # já é bytes
                                }
                            }
                        )
                if parts:
                    server_content["modelTurn"] = {"parts": parts}

            result["serverContent"] = server_content

        return result

    async def close(self) -> None:
        """Fecha a conexão."""
        self._is_connected = False
        if self._context_manager and self._session:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception:
                pass
        self._session = None
        self._context_manager = None
        logger.info("[gemini] Conexão fechada")
