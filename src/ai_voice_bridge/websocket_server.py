"""Servidor WebSocket para comunicação com clientes (Unreal Engine)."""

import asyncio
import json
import logging
from typing import Callable, Awaitable

from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosed

from ai_voice_bridge.config import settings

logger = logging.getLogger(__name__)


class WebSocketServer:
    """Servidor WebSocket para comunicação bidirecional com clientes."""

    def __init__(self) -> None:
        self._connections: set[ServerConnection] = set()
        self._server = None
        self._on_start_talking: Callable[[], Awaitable[None]] | None = None
        self._on_stop_talking: Callable[[], Awaitable[None]] | None = None
        self._on_audio_chunk: Callable[[bytes], Awaitable[None]] | None = None

    async def start(
        self,
        on_start_talking: Callable[[], Awaitable[None]],
        on_stop_talking: Callable[[], Awaitable[None]],
        on_audio_chunk: Callable[[bytes], Awaitable[None]],
    ) -> None:
        """Inicia o servidor WebSocket."""
        self._on_start_talking = on_start_talking
        self._on_stop_talking = on_stop_talking
        self._on_audio_chunk = on_audio_chunk

        self._server = await serve(
            self._handle_connection,
            settings.ws_host,
            settings.ws_port,
        )
        logger.info(
            "[ws-server] Escutando em ws://%s:%s",
            settings.ws_host,
            settings.ws_port,
        )

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        """Handler para cada conexão WebSocket."""
        self._connections.add(websocket)
        client_addr = websocket.remote_address
        logger.info("[ws-server] Cliente conectado: %s", client_addr)

        try:
            # Envia connected e ready imediatamente para o novo cliente
            await websocket.send(json.dumps({"type": "connected"}))
            await websocket.send(json.dumps({"type": "ready"}))

            async for message in websocket:
                await self._process_message(message)

        except ConnectionClosed as e:
            logger.info(
                "[ws-server] Conexão fechada: %s (code=%s)", client_addr, e.code
            )
        except Exception as e:
            logger.warning("[ws-server] Erro na conexão %s: %s", client_addr, e)
        finally:
            self._connections.discard(websocket)

    async def _process_message(self, message: str | bytes) -> None:
        """Processa mensagem recebida (JSON ou binário)."""
        # Áudio binário
        if isinstance(message, bytes):
            if self._on_audio_chunk:
                await self._on_audio_chunk(message)
            return

        # Controle JSON
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "start_talking":
                logger.debug("[ws-server] start_talking recebido")
                if self._on_start_talking:
                    await self._on_start_talking()

            elif msg_type == "stop_talking":
                logger.debug("[ws-server] stop_talking recebido")
                if self._on_stop_talking:
                    await self._on_stop_talking()

        except json.JSONDecodeError:
            logger.warning("[ws-server] Mensagem JSON inválida")

    async def _broadcast_json(self, message: dict) -> None:
        """Envia JSON para todos os clientes conectados."""
        if not self._connections:
            return
        msg_str = json.dumps(message)
        await asyncio.gather(
            *[ws.send(msg_str) for ws in self._connections],
            return_exceptions=True,
        )

    async def _broadcast_binary(self, data: bytes) -> None:
        """Envia dados binários para todos os clientes."""
        if not self._connections:
            return
        await asyncio.gather(
            *[ws.send(data) for ws in self._connections],
            return_exceptions=True,
        )

    async def send_ready(self) -> None:
        """Notifica que o gateway está pronto."""
        await self._broadcast_json({"type": "ready"})

    async def send_speaking(self, is_speaking: bool) -> None:
        """Notifica mudança no estado de fala do AI."""
        await self._broadcast_json({"type": "speaking", "value": is_speaking})

    async def send_subtitle(self, text: str) -> None:
        """Envia texto (legenda) para os clientes."""
        await self._broadcast_json({"type": "subtitle", "text": text})

    async def send_audio(self, pcm_data: bytes) -> None:
        """Envia áudio PCM como frame binário."""
        await self._broadcast_binary(pcm_data)

    async def send_turn_complete(self) -> None:
        """Notifica que o AI terminou de falar."""
        await self._broadcast_json({"type": "turn_complete"})

    async def send_error(self, message: str) -> None:
        """Envia mensagem de erro."""
        await self._broadcast_json({"type": "error", "message": message})

    async def stop(self) -> None:
        """Encerra o servidor."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[ws-server] Servidor encerrado")
