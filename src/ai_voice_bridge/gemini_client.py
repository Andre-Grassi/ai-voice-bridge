"""Cliente WebSocket para Gemini Live API."""

import base64
import json
import logging
from typing import AsyncIterator

from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from ai_voice_bridge.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Cliente WebSocket para Gemini Live API (streaming bidirecional)."""

    def __init__(self) -> None:
        self._ws = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Retorna True se conectado ao Gemini."""
        return self._is_connected and self._ws is not None

    async def connect(self, system_prompt: str) -> None:
        """Estabelece conexão WebSocket com Gemini Live."""
        uri = (
            f"wss://generativelanguage.googleapis.com/ws/"
            f"google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
            f"?key={settings.google_api_key}"
        )

        logger.info("[gemini] Conectando...")
        self._ws = await ws_connect(uri, max_size=None)

        await self._send_setup(system_prompt)

        # Aguarda confirmação de setup
        response = await self._ws.recv()
        data = json.loads(response)

        if "setupComplete" in data:
            self._is_connected = True
            logger.info("[gemini] Conexão estabelecida, setup completo")
        else:
            raise RuntimeError(f"[gemini] Setup falhou: {data}")

    async def _send_setup(self, system_prompt: str) -> None:
        """Envia configuração inicial para Gemini."""
        setup_msg = {
            "setup": {
                "model": f"models/{settings.gemini_model}",
                "generationConfig": {
                    "responseModalities": ["AUDIO", "TEXT"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {"voiceName": settings.gemini_voice}
                        }
                    },
                },
                "systemInstruction": {"parts": [{"text": system_prompt}]},
            }
        }
        await self._ws.send(json.dumps(setup_msg))
        logger.debug("[gemini] Setup enviado")

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """Envia chunk de áudio PCM para Gemini."""
        if not self.is_connected:
            return

        msg = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": f"audio/pcm;rate={settings.input_sample_rate}",
                        "data": base64.b64encode(pcm_chunk).decode(),
                    }
                ]
            }
        }

        try:
            await self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.warning("[gemini] Erro ao enviar áudio: %s", e)
            self._is_connected = False

    async def receive_messages(self) -> AsyncIterator[dict]:
        """Gera mensagens recebidas do Gemini."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
                try:
                    yield json.loads(msg)
                except json.JSONDecodeError:
                    continue
        except ConnectionClosed as e:
            logger.info("[gemini] Conexão fechada (code=%s)", e.code)
            self._is_connected = False
        except Exception as e:
            logger.error("[gemini] Erro ao receber: %s", e)
            self._is_connected = False

    async def close(self) -> None:
        """Fecha a conexão WebSocket."""
        self._is_connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
            logger.info("[gemini] Conexão fechada")
