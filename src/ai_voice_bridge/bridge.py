"""Coordenador principal do AI Voice Bridge."""

import asyncio
import base64
import logging

import numpy as np

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
from ai_voice_bridge.websocket_server import WebSocketServer

# Sample rate do áudio de saída do Gemini
_AUDIO_SAMPLE_RATE = 24000


class VoiceBridge:
    """Coordena WebSocket server, estratégia e cliente Gemini."""

    def __init__(self) -> None:
        self._gemini = GeminiClient()
        self._ws = WebSocketServer()
        self._strategy = self._create_strategy()
        self._response_task: asyncio.Task | None = None
        self._audio_buffer: list[bytes] = []  # Buffer para debug de áudio local

    def _create_strategy(self) -> SessionStrategy:
        """Cria estratégia baseada na configuração."""
        mode = settings.connection_mode.upper()
        if mode == "ALWAYS_ON":
            logger.info("[bridge] Usando estratégia Always-On")
            return AlwaysOnStrategy(self._gemini)
        else:
            logger.info("[bridge] Usando estratégia On-Demand")
            return OnDemandStrategy(self._gemini)

    async def run(self) -> None:
        """Inicia o bridge."""
        logger.info("[bridge] Iniciando AI Voice Bridge...")

        # Inicia WebSocket server
        await self._ws.start(
            on_start_talking=self._handle_start,
            on_stop_talking=self._handle_stop,
            on_audio_chunk=self._handle_audio,
        )

        # Inicializa estratégia
        await self._strategy.initialize()
        await self._ws.send_ready()

        logger.info("[bridge] AI Voice Bridge pronto!")

    async def _handle_start(self) -> None:
        """Handler para start_talking."""
        logger.debug("[bridge] start_talking recebido")
        try:
            await self._strategy.on_start_talking()

            # Inicia task de processamento de respostas para esta sessão
            if self._response_task:
                self._response_task.cancel()
            self._response_task = asyncio.create_task(self._process_responses())

        except Exception as e:
            logger.error("[bridge] Erro ao iniciar: %s", e)
            await self._ws.send_error(f"Falha ao conectar: {e}")

    async def _handle_stop(self) -> None:
        """Handler para stop_talking."""
        logger.debug("[bridge] stop_talking recebido")
        await self._strategy.on_stop_talking()

    async def _handle_audio(self, chunk: bytes) -> None:
        """Handler para áudio recebido do cliente."""
        await self._strategy.send_audio(chunk)

    async def _process_responses(self) -> None:
        """Processa respostas do Gemini e envia para clientes."""
        self._audio_buffer = []  # Limpa buffer no início de cada turno

        try:
            async for msg in self._strategy.receive_responses():
                # Processa áudio
                if audio_data := self._extract_audio(msg):
                    logger.info("[bridge] Enviando chunk: %d bytes", len(audio_data))
                    await self._ws.send_speaking(True)
                    await self._ws.send_audio(audio_data)

                    # [DEBUG] Acumula áudio para reprodução local
                    if settings.debug_play_audio_locally:
                        self._audio_buffer.append(audio_data)

                # Processa texto (legendas)
                if text := self._extract_text(msg):
                    await self._ws.send_subtitle(text)

                # Detecta fim de turno
                if self._is_turn_complete(msg):
                    await self._ws.send_speaking(False)
                    await self._ws.send_turn_complete()

                    # [DEBUG] Reproduz áudio localmente
                    if settings.debug_play_audio_locally and self._audio_buffer:
                        self._play_audio_locally()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[bridge] Erro no processamento: %s", e)
            await self._ws.send_error(str(e))

    def _play_audio_locally(self) -> None:
        """[DEBUG] Reproduz áudio acumulado no dispositivo local."""
        if not self._audio_buffer:
            return

        if sd is None:
            logger.warning(
                "[bridge] sounddevice não disponível. Ignorando playback local."
            )
            self._audio_buffer = []
            return

        # Concatena todos os chunks
        all_audio = b"".join(self._audio_buffer)
        logger.info(
            "[bridge] Reproduzindo áudio localmente: %d bytes, %d chunks",
            len(all_audio),
            len(self._audio_buffer),
        )

        # Converte PCM 16-bit signed para float32 normalizado
        audio_int16 = np.frombuffer(all_audio, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        logger.info(
            "[bridge] Samples: %d, Duração: %.2fs",
            len(audio_float32),
            len(audio_float32) / _AUDIO_SAMPLE_RATE,
        )

        # Reproduz (bloqueante, mas é para debug)
        sd.play(audio_float32, samplerate=_AUDIO_SAMPLE_RATE)
        sd.wait()

        logger.info("[bridge] Reprodução local concluída")
        self._audio_buffer = []

    def _extract_audio(self, msg: dict) -> bytes | None:
        """Extrai áudio PCM da resposta Gemini."""
        try:
            parts = msg.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
            for part in parts:
                if inline := part.get("inlineData"):
                    mime = inline.get("mimeType", "")
                    if "audio" in mime:
                        data = inline["data"]
                        # SDK retorna bytes direto, WebSocket raw retornava base64
                        if isinstance(data, bytes):
                            return data
                        else:
                            return base64.b64decode(data)
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
        """Verifica se a resposta marca fim de turno."""
        return msg.get("serverContent", {}).get("turnComplete", False)

    async def shutdown(self) -> None:
        """Encerra o bridge graciosamente."""
        logger.info("[bridge] Encerrando...")

        if self._response_task:
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass

        await self._strategy.shutdown()
        await self._ws.stop()
        logger.info("[bridge] Encerrado.")
