import asyncio
import base64
import json
import logging

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None
    logger.warning(
        "[bridge] Biblioteca 'sounddevice' (ou PortAudio) não encontrada. Playback local desativado."
    )

from ai_voice_bridge.config import settings
from ai_voice_bridge.gemini_client import GeminiClient
from ai_voice_bridge.strategies.base import SessionStrategy
from ai_voice_bridge.strategies.on_demand import OnDemandStrategy
from ai_voice_bridge.strategies.always_on import AlwaysOnStrategy

# Sample rate do áudio de saída do Gemini
_AUDIO_SAMPLE_RATE = 24000


class VoiceBridge:
    """Coordena conexões WebSocket, estratégia e cliente Gemini."""

    def __init__(self) -> None:
        self._gemini = GeminiClient()
        self._connections: set[WebSocket] = set()
        self._strategy = self._create_strategy()
        self._response_task: asyncio.Task | None = None
        self._audio_buffer: list[bytes] = []  # Buffer para debug de áudio local

    def _create_strategy(self) -> SessionStrategy:
        """Cria estratégia baseada na configuração."""
        mode = settings.connection_mode.upper()
        if mode == "ALWAYS_ON":
            return AlwaysOnStrategy(self._gemini)
        else:
            return OnDemandStrategy(self._gemini)

    async def initialize(self) -> None:
        """Inicializa o bridge (estratégia e conexões)."""
        logger.info("[bridge] Inicializando estratégia...")
        await self._strategy.initialize()
        logger.info("[bridge] Bridge pronto.")

    async def handle_connection(self, websocket: WebSocket) -> None:
        """Gerencia uma nova conexão WebSocket (FastAPI)."""
        await websocket.accept()
        self._connections.add(websocket)
        client_addr = websocket.client
        logger.info("[bridge] Cliente conectado: %s", client_addr)

        try:
            # Envia 'connected' e 'ready'
            await websocket.send_text(json.dumps({"type": "connected"}))
            await websocket.send_text(json.dumps({"type": "ready"}))

            # Loop de mensagens
            while True:
                message = await websocket.receive()
                if "text" in message:
                    await self._process_message(message["text"])
                elif "bytes" in message:
                    await self._handle_audio(message["bytes"])

        except WebSocketDisconnect:
            logger.info("[bridge] Cliente desconectado: %s", client_addr)
        except Exception as e:
            logger.error("[bridge] Erro na conexão %s: %s", client_addr, e)
        finally:
            self._connections.discard(websocket)

    async def _process_message(self, message: str) -> None:
        """Processa mensagens de texto (JSON) do cliente."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "start_talking":
                logger.debug("[bridge] start_talking recebido")
                await self._handle_start()
            elif msg_type == "stop_talking":
                logger.debug("[bridge] stop_talking recebido")
                await self._handle_stop()

        except json.JSONDecodeError:
            logger.warning("[bridge] JSON inválido recebido")

    async def _handle_start(self) -> None:
        """Inicia sessão de fala."""
        try:
            await self._strategy.on_start_talking()

            # Reinicia task de resposta
            if self._response_task:
                self._response_task.cancel()
            self._response_task = asyncio.create_task(self._process_responses())

        except Exception as e:
            logger.error("[bridge] Erro ao iniciar: %s", e)
            await self.send_error(f"Falha ao conectar: {e}")

    async def _handle_stop(self) -> None:
        """Para sessão de fala."""
        await self._strategy.on_stop_talking()

    async def _handle_audio(self, chunk: bytes) -> None:
        """Envia áudio do cliente para o Gemini."""
        await self._strategy.send_audio(chunk)

    async def _process_responses(self) -> None:
        """Processa respostas do Gemini e envia para clientes."""
        self._audio_buffer = []

        try:
            async for msg in self._strategy.receive_responses():
                # Processa áudio
                if audio_data := self._extract_audio(msg):
                    await self.send_speaking(True)
                    await self.send_audio(audio_data)

                    if settings.debug_play_audio_locally:
                        self._audio_buffer.append(audio_data)

                # Processa texto
                if text := self._extract_text(msg):
                    await self.send_subtitle(text)

                # Fim de turno
                if self._is_turn_complete(msg):
                    await self.send_speaking(False)
                    await self.send_turn_complete()

                    if settings.debug_play_audio_locally and self._audio_buffer:
                        self._play_audio_locally()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[bridge] Erro no processamento: %s", e)
            await self.send_error(str(e))

    # --- Métodos de Envio (Broadcast) ---

    async def _broadcast_text(self, data: dict) -> None:
        if not self._connections:
            return
        msg = json.dumps(data)
        # Envia para todos (ignora erros de envio individuais)
        await asyncio.gather(
            *[ws.send_text(msg) for ws in self._connections], return_exceptions=True
        )

    async def _broadcast_bytes(self, data: bytes) -> None:
        if not self._connections:
            return
        await asyncio.gather(
            *[ws.send_bytes(data) for ws in self._connections], return_exceptions=True
        )

    async def send_ready(self) -> None:
        await self._broadcast_text({"type": "ready"})

    async def send_speaking(self, is_speaking: bool) -> None:
        await self._broadcast_text({"type": "speaking", "value": is_speaking})

    async def send_subtitle(self, text: str) -> None:
        await self._broadcast_text({"type": "subtitle", "text": text})

    async def send_audio(self, pcm_data: bytes) -> None:
        await self._broadcast_bytes(pcm_data)

    async def send_turn_complete(self) -> None:
        await self._broadcast_text({"type": "turn_complete"})

    async def send_error(self, message: str) -> None:
        await self._broadcast_text({"type": "error", "message": message})

    # --- Helpers ---

    def _play_audio_locally(self) -> None:
        """[DEBUG] Reproduz áudio acumulado localmente."""
        if not self._audio_buffer or sd is None:
            return

        all_audio = b"".join(self._audio_buffer)
        audio_int16 = np.frombuffer(all_audio, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        logger.info("[bridge] [DEBUG] Reproduzindo áudio local...")
        sd.play(audio_float32, samplerate=_AUDIO_SAMPLE_RATE)
        sd.wait()
        self._audio_buffer = []

    def _extract_audio(self, msg: dict) -> bytes | None:
        try:
            parts = msg.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
            for part in parts:
                if inline := part.get("inlineData"):
                    if "audio" in inline.get("mimeType", ""):
                        data = inline["data"]
                        return (
                            data if isinstance(data, bytes) else base64.b64decode(data)
                        )
        except Exception:
            pass
        return None

    def _extract_text(self, msg: dict) -> str | None:
        try:
            parts = msg.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
            for part in parts:
                if text := part.get("text"):
                    return text
        except Exception:
            pass
        return None

    def _is_turn_complete(self, msg: dict) -> bool:
        return msg.get("serverContent", {}).get("turnComplete", False)

    async def shutdown(self) -> None:
        """Encerra conexões e estratégia."""
        logger.info("[bridge] Encerrando Bridge...")
        if self._response_task:
            self._response_task.cancel()

        await self._strategy.shutdown()

        # Fecha conexões WebSocket
        for ws in list(self._connections):
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()
        logger.info("[bridge] Encerrado.")
